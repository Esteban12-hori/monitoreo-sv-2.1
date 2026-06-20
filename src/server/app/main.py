import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import os
import uuid
import unicodedata

from fastapi import FastAPI, HTTPException, Header, Depends, status, Request, Response, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import create_engine, select, delete, text, func
from sqlalchemy.orm import Session, defer
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import DB_PATH, DEFAULT_ALERTS, ALLOWED_ORIGINS, ALLOWED_HOSTS, DASHBOARD_TOKEN, CACHE_MAX_ITEMS, BASE_DIR
from .models import Base, Server, Metric, AlertConfig, User, UserSession, AlertRecipient, AlertRule, ServerThreshold, AuditLog, UserServerLink, SMTPConfig, RemoteAction, UserGroup, NotificationRule, UserServerThreshold, DataMonitoring
from .schemas import (
    MetricsIngestSchema, RegisterServerSchema, AlertConfigSchema, LoginSchema,
    UserCreateSchema, UserResponseSchema, ChangePasswordSchema,
    ServerConfigUpdateSchema, AlertRecipientSchema, AlertRecipientCreateSchema,
    ServerAssignmentSchema, AlertRuleCreate, AlertRuleResponse, ServerUpdateGroupSchema,
    ServerThresholdResponse, ServerThresholdUpdate, AuditLogResponse, ServerThresholdImport,
    UserUpdateSchema, UserServerAssignmentResponse, SMTPConfigSchema, SMTPConfigResponse,
    UserGroupCreate, UserGroupResponse, UserGroupUpdate, NotificationRuleCreate, NotificationRuleResponse,
    AlertPreviewRequest, AlertPreviewResponse, UserServerThresholdResponse, UserServerThresholdUpdate,
    ServerSubscriptionUpdate, DataMonitoringSchema, DataMonitoringResponse, ServerWebhookConfigUpdate
)
from .email_utils import send_alert_email
from .alert_logic import get_alert_recipients, check_advanced_rules, explain_alert_decision
from .security import encrypt_password, decrypt_password
from .models import ProxmoxNode, ProxmoxGuest, BackupSchedule, BackupJob, NodeLink, SnapshotRecord
from .models import MonitoringCheck, MonitoringCheckResult, NotificationChannel
from .schemas import (
    ProxmoxNodeCreate, ProxmoxNodeResponse, ProxmoxGuestResponse, GuestLinkUpdate,
    GuestResourceUpdate, SnapshotCreate, SnapshotResponse, BackupScheduleCreate,
    BackupScheduleUpdate, BackupScheduleResponse, BackupRunRequest, BackupJobResponse,
    NodeLinkCreate, NodeLinkResponse, MigrateRequest, GuestPowerRequest
)
from .proxmox import service as pmx_service, wireguard as pmx_wg, scheduler as pmx_scheduler, dbdetect as pmx_dbdetect
from .proxmox.ssh_executor import get_host_fingerprint, SSHCommandError
from .schemas import (
    MonitoringCheckCreate, MonitoringCheckUpdate, MonitoringCheckResponse,
    MonitoringCheckResultResponse, NotificationChannelCreate, NotificationChannelUpdate,
    NotificationChannelResponse, DiscoveryScanRequest, DiscoveryScanResponse, InventoryItem
)
from .monitoring import checks as mon_checks
from .monitoring import validators as mon_validators
from .monitoring import discovery as mon_discovery
from .notifications import channels as notif_channels
from . import maintenance
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import logging

# Configuración de Passlib para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Logging Configuration ---
LOG_FILE = BASE_DIR / "server.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

from .database import engine

Base.metadata.create_all(engine)

app = FastAPI(title="UpKeep")

# --- Rate Limiting Setup ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Security Middlewares ---
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )
    return response

# Si se permite cualquier origen ("*"), no se pueden habilitar credenciales:
# el navegador rechaza la combinación wildcard + credentials. Como la
# autenticación viaja en la cabecera X-Dashboard-Token (no en cookies),
# deshabilitar credentials en ese caso es seguro y evita una config inválida.
_allow_credentials = "*" not in ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/agent/install", tags=["Agent"])
def get_agent_install_script(request: Request):
    """
    Retorna el script de instalación del agente (install.py).
    Permite instalación rápida con: curl -sSL https://domain/api/agent/install | python3 -
    Inyecta la URL del servidor automáticamente.
    """
    script_path = BASE_DIR / "agent" / "python" / "install.py"
    if not script_path.exists():
        # Fallback si no encuentra la ruta (ej. en docker container con estructura diferente)
        potential_paths = [
            Path("agent/python/install.py"),
            Path("../agent/python/install.py"),
            Path("/app/agent/python/install.py")
        ]
        for p in potential_paths:
            if p.exists():
                script_path = p
                break
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Install script not found")
    
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Inject Server URL if placeholder exists, or prepend it
        server_url = str(request.base_url).rstrip("/")
        if '__SERVER_URL__ = ""' in content:
            content = content.replace('__SERVER_URL__ = ""', f'__SERVER_URL__ = "{server_url}"')
        else:
             content = f'__SERVER_URL__ = "{server_url}"\n' + content

        return Response(content=content, media_type="text/x-python")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading script: {str(e)}")

@app.get("/api/agent/download", tags=["Agent"])
def get_agent_py():
    """
    Retorna el código fuente del agente (agent.py).
    """
    script_path = BASE_DIR / "agent" / "python" / "agent.py"
    if not script_path.exists():
         potential_paths = [
            Path("agent/python/agent.py"),
            Path("../agent/python/agent.py"),
            Path("/app/agent/python/agent.py")
        ]
         for p in potential_paths:
            if p.exists():
                script_path = p
                break
    
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Agent script not found")
        
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="text/x-python")
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error reading agent: {str(e)}")

def ensure_default_alerts(sess: Session):
    # Usamos scalars().first() para evitar error si hay múltiples (aunque no debería)
    cfg = sess.execute(select(AlertConfig)).scalars().first()
    if not cfg:
        cfg = AlertConfig(
            cpu_total_percent=DEFAULT_ALERTS["cpu_total_percent"],
            memory_used_percent=DEFAULT_ALERTS["memory_used_percent"],
            disk_used_percent=DEFAULT_ALERTS["disk_used_percent"],
        )
        sess.add(cfg)
        sess.commit()

def ensure_recipient_type_column():
    """Migración manual para agregar recipient_type a AlertRecipient si no existe."""
    with Session(engine) as sess:
        try:
            # Intenta seleccionar la columna
            sess.execute(select(AlertRecipient.recipient_type).limit(1))
        except Exception:
            # Si falla, probablemente no existe la columna
            print("Agregando columna recipient_type a alert_recipients...")
            try:
                sess.execute(text("ALTER TABLE alert_recipients ADD COLUMN recipient_type VARCHAR(50) DEFAULT 'OTROS'"))
                sess.commit()
            except Exception as e:
                print(f"Error migrando recipient_type: {e}")
                sess.rollback()

def ensure_link_column():
    """Migración manual para agregar receive_alerts a user_server_link si no existe."""
    with Session(engine) as sess:
        try:
            sess.execute(select(UserServerLink.receive_alerts).limit(1))
        except Exception:
            print("Agregando columna receive_alerts a user_server_link...")
            try:
                sess.execute(text("ALTER TABLE user_server_link ADD COLUMN receive_alerts BOOLEAN DEFAULT 1"))
                sess.commit()
            except Exception as e:
                print(f"Error migrando user_server_link: {e}")
                sess.rollback()

def ensure_user_blocked_column():
    with Session(engine) as sess:
        try:
            sess.execute(select(User.is_blocked).limit(1))
        except Exception:
            try:
                sess.execute(text("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0"))
                sess.commit()
            except Exception as e:
                print(f"Error migrando users.is_blocked: {e}")
                sess.rollback()

def ensure_user_notification_columns():
    with Session(engine) as sess:
        try:
            sess.execute(select(User.phone_number).limit(1))
        except Exception:
            try:
                sess.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(50)"))
                sess.execute(text("ALTER TABLE users ADD COLUMN webhook_url VARCHAR(500)"))
                sess.commit()
            except Exception as e:
                print(f"Error migrando users.phone_number/webhook_url: {e}")
                sess.rollback()

@app.on_event("startup")
def startup():
    # Usar un lock o simplemente un try-except robusto
    try:
        ensure_recipient_type_column()
        ensure_link_column()
        ensure_user_blocked_column()
        ensure_user_notification_columns()
        with Session(engine) as sess:
            ensure_default_alerts(sess)
    except Exception as e:
        print(f"Advertencia en startup: {e}")

    # Iniciar el scheduler de backups Proxmox (no bloquea si APScheduler falta)
    try:
        pmx_scheduler.init_scheduler()
    except Exception as e:
        print(f"Advertencia iniciando scheduler de backups: {e}")


@app.on_event("shutdown")
def shutdown():
    try:
        pmx_scheduler.shutdown_scheduler()
    except Exception:
        pass

# Caché en memoria de métricas recientes por servidor
_cache: dict[str, list[dict]] = {}
_cache_order: dict[str, int] = {}

# Caché de umbrales: server_id -> {cpu_threshold, memory_threshold, disk_threshold}
_threshold_cache: dict[str, dict] = {}

# Estado de alertas enviadas: {(server_id, alert_type): timestamp}
_alert_state: dict[tuple[str, str], float] = {}
# Estado de alertas avanzadas: {key: {"start": ts, "last_sent": ts}}
_advanced_alert_state: dict[str, dict] = {}
ALERT_COOLDOWN = 3600  # 1 hora

# Tiempo de vida de las sesiones (horas). Configurable vía env.
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "168"))  # 7 días por defecto

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    try:
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
    except Exception:
        pass
    return s

def get_current_user_from_token(x_dashboard_token: Optional[str] = Header(None)):
    if not x_dashboard_token:
        raise HTTPException(status_code=401, detail="Unauthorized dashboard token")
    
    with Session(engine) as sess:
        session_record = sess.execute(
            select(UserSession).where(UserSession.token == x_dashboard_token)
        ).scalar_one_or_none()
        
        if not session_record:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Validar expiración de la sesión (TTL)
        created = session_record.created_at
        if created is not None:
            try:
                # Normalizar a naive UTC para comparar de forma segura
                if created.tzinfo is not None:
                    created = created.astimezone(timezone.utc).replace(tzinfo=None)
                age = datetime.utcnow() - created
                if age > timedelta(hours=SESSION_TTL_HOURS):
                    sess.delete(session_record)
                    sess.commit()
                    raise HTTPException(status_code=401, detail="Session expired")
            except HTTPException:
                raise
            except Exception:
                # Si la comparación falla por algún motivo, no bloqueamos el acceso
                pass

        # Cargar usuario relacionado
        user = sess.get(User, session_record.user_id)
        if not user:
            # Sesión huérfana
            sess.delete(session_record)
            sess.commit()
            raise HTTPException(status_code=401, detail="User not found")
            
        data = {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin
        }
        return data

def require_admin(user: dict = Depends(get_current_user_from_token)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Requiere privilegios de administrador")
    return user

@app.post("/api/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginSchema):
    identifier = _norm(payload.email or "")
    password = (payload.password or "").strip()
    
    with Session(engine) as sess:
        # Buscar usuario por email
        # Primero intentamos coincidencia exacta
        user = sess.execute(select(User).where(User.email == identifier)).scalar_one_or_none()
        
        # Si no, buscar si el identificador coincide con la parte local del correo
        if not user:
             # Esto es menos eficiente pero permite login corto. 
             # Idealmente el cliente debería enviar el email completo.
             all_users = sess.execute(select(User)).scalars().all()
             for u in all_users:
                 if _norm(u.email) == identifier or _norm(u.email.split('@')[0]) == identifier:
                     user = u
                     break
        
        if not user or user.is_blocked or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        token = uuid.uuid4().hex
        
        # Guardar sesión en DB
        new_session = UserSession(token=token, user_id=user.id)
        sess.add(new_session)
        sess.commit()
        
        return {
            "token": token, 
            "email": user.email, 
            "name": user.name, 
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password,
            "is_blocked": user.is_blocked
        }

@app.post("/api/logout")
def logout(x_dashboard_token: Optional[str] = Header(None)):
    if not x_dashboard_token:
        raise HTTPException(status_code=401, detail="Missing token")
        
    with Session(engine) as sess:
        sess.execute(delete(UserSession).where(UserSession.token == x_dashboard_token))
        sess.commit()
    
    return {"status": "logged_out"}

@app.post("/api/users/change-password")
def change_password(payload: ChangePasswordSchema, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        u = sess.get(User, user["user_id"])
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        if not verify_password(payload.current_password, u.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
            
        u.password_hash = get_password_hash(payload.new_password)
        u.must_change_password = False
        sess.commit()
        
        return {"status": "password_changed"}


# --- Gestión de Usuarios (Admin) ---

@app.get("/api/admin/users", response_model=List[UserResponseSchema])
def list_users(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        users = sess.execute(select(User)).scalars().all()
        return users

@app.post("/api/admin/users", response_model=UserResponseSchema)
def create_user(payload: UserCreateSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        existing = sess.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        
        new_user = User(
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            name=payload.name,
            is_admin=payload.is_admin,
            receive_alerts=payload.receive_alerts,
            must_change_password=payload.must_change_password,
            is_blocked=payload.is_blocked
        )
        sess.add(new_user)
        sess.commit()
        sess.refresh(new_user)
        return new_user

@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_admin)):
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
        
    with Session(engine) as sess:
        u = sess.get(User, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        sess.delete(u)
        sess.commit()
        return {"status": "deleted"}

@app.put("/api/admin/users/{user_id}", response_model=UserResponseSchema)
def update_user(user_id: int, payload: UserUpdateSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        u = sess.get(User, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if payload.name is not None:
            u.name = payload.name
        if payload.is_admin is not None:
            # Evitar quitarse admin a sí mismo
            if user_id == user["user_id"] and payload.is_admin is False:
                raise HTTPException(status_code=400, detail="No puedes quitarte privilegios de administrador a ti mismo")
            u.is_admin = payload.is_admin
        if payload.receive_alerts is not None:
            u.receive_alerts = payload.receive_alerts
        if payload.password is not None:
            u.password_hash = get_password_hash(payload.password)
        if payload.is_blocked is not None:
            if user_id == user["user_id"] and payload.is_blocked:
                raise HTTPException(status_code=400, detail="No puedes bloquear tu propia cuenta")
            u.is_blocked = payload.is_blocked
            
        sess.commit()
        sess.refresh(u)
        return u

@app.post("/api/admin/users/{user_id}/servers")
def assign_servers_to_user(user_id: int, payload: ServerAssignmentSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        target_user = sess.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Usuario destino no encontrado")
        
        # 1. Eliminar asignaciones existentes
        sess.execute(delete(UserServerLink).where(UserServerLink.user_id == user_id))
        
        # 2. Crear nuevas asignaciones
        if payload.assignments:
            # Obtener IDs internos de los servidores
            server_ids_str = [a.server_id for a in payload.assignments]
            servers_map = {
                s.server_id: s.id 
                for s in sess.execute(select(Server).where(Server.server_id.in_(server_ids_str))).scalars().all()
            }
            
            for item in payload.assignments:
                s_int_id = servers_map.get(item.server_id)
                if s_int_id:
                    link = UserServerLink(
                        user_id=user_id,
                        server_id=s_int_id,
                        receive_alerts=item.receive_alerts
                    )
                    sess.add(link)
        
        sess.commit()
        return {"status": "assigned", "count": len(payload.assignments)}

@app.get("/api/admin/users/{user_id}/servers", response_model=List[UserServerAssignmentResponse])
def get_user_servers(user_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        target_user = sess.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Usuario destino no encontrado")
        
        res = []
        for link in target_user.server_links:
            # Asegurarse de que link.server esté cargado
            res.append({
                "server_id": link.server.server_id,
                "receive_alerts": link.receive_alerts
            })
        return res

# --- Servidores y Métricas ---

@app.post("/api/register")
def register_server(payload: RegisterServerSchema):
    with Session(engine) as sess:
        existing = sess.execute(select(Server).where(Server.server_id == payload.server_id)).scalar_one_or_none()
        if existing:
            existing.token = payload.token
            sess.commit()
            return {"status": "updated", "server_id": existing.server_id}
        srv = Server(server_id=payload.server_id, token=payload.token)
        sess.add(srv)
        sess.commit()
        return {"status": "registered", "server_id": payload.server_id}


@app.get("/api/data-monitoring/stats")
def get_data_monitoring_stats(user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        # Construir query base
        stmt_app = select(DataMonitoring.app, func.count(DataMonitoring.id)).group_by(DataMonitoring.app)
        stmt_server = select(DataMonitoring.server_id, func.count(DataMonitoring.id)).group_by(DataMonitoring.server_id)

        if not user["is_admin"]:
             u = sess.get(User, user["user_id"])
             if not u:
                 return {"by_app": [], "by_server": []}
             server_ids = [s.server_id for s in u.servers]
             stmt_app = stmt_app.where(DataMonitoring.server_id.in_(server_ids))
             stmt_server = stmt_server.where(DataMonitoring.server_id.in_(server_ids))
        
        by_app = sess.execute(stmt_app).all()
        by_server = sess.execute(stmt_server).all()
        
        return {
            "by_app": [{"label": r[0], "count": r[1]} for r in by_app],
            "by_server": [{"label": r[0], "count": r[1]} for r in by_server]
        }

@app.get("/api/servers")
def list_servers(user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        if user["is_admin"]:
            servers = sess.execute(select(Server)).scalars().all()
        else:
            # Filtrar solo servidores asignados al usuario
            u = sess.get(User, user["user_id"])
            servers = u.servers if u else []
            
        return [
            {
                "server_id": s.server_id, 
                "created_at": str(s.created_at), 
                "group_name": s.group_name,
                "report_interval": s.report_interval
            } 
            for s in servers
        ]


@app.delete("/api/admin/servers/{server_id}")
def delete_server(server_id: str, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Servidor no encontrado")
        sess.delete(srv)
        sess.commit()
        
        # Limpiar caché si existe
        if server_id in _cache:
            del _cache[server_id]
            
        return {"status": "deleted", "server_id": server_id}


@app.put("/api/admin/servers/{server_id}/config")
def update_server_config(server_id: str, payload: ServerConfigUpdateSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Servidor no encontrado")
        
        srv.report_interval = payload.report_interval
        sess.commit()
        return {"status": "updated", "server_id": server_id, "report_interval": srv.report_interval}


# --- Destinatarios de Alertas (Alert Recipients) ---

@app.get("/api/admin/recipients", response_model=List[AlertRecipientSchema])
def list_alert_recipients(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        recipients = sess.execute(select(AlertRecipient)).scalars().all()
    return recipients

@app.post("/api/admin/recipients", response_model=AlertRecipientSchema)
def create_alert_recipient(payload: AlertRecipientCreateSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        existing = sess.execute(select(AlertRecipient).where(AlertRecipient.email == payload.email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        
        new_recipient = AlertRecipient(
            email=payload.email, 
            name=payload.name,
            recipient_type=payload.recipient_type
        )
        sess.add(new_recipient)
        sess.commit()
        sess.refresh(new_recipient)
        return new_recipient

@app.delete("/api/admin/recipients/{recipient_id}")
def delete_alert_recipient(recipient_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        r = sess.get(AlertRecipient, recipient_id)
        if not r:
            raise HTTPException(status_code=404, detail="Destinatario no encontrado")
        sess.delete(r)
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/admin/test-email")
def test_email(payload: AlertRecipientCreateSchema, user: dict = Depends(require_admin)):
    """
    Endpoint para probar la configuración de correo.
    Envía un correo de prueba al destinatario especificado.
    """
    try:
        # Usamos send_alert_email con datos simulados
        send_alert_email(
            server_id="TEST-SERVER",
            alert_type="PRUEBA DE CORREO",
            current_value=100.0,
            threshold=50.0,
            extra_recipients=[payload.email],
            full_metrics={}
        )
        return {"status": "sent", "message": f"Correo de prueba enviado a {payload.email}"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error enviando correo: {str(e)}")


# --- Reglas de Alerta y Grupos ---

@app.get("/api/admin/alert-rules", response_model=List[AlertRuleResponse])
def list_alert_rules(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        rules = sess.execute(select(AlertRule)).scalars().all()
        res = []
        for r in rules:
            try:
                emails_list = json.loads(r.emails) if r.emails else []
            except:
                emails_list = []
            res.append(AlertRuleResponse(
                id=r.id,
                alert_type=r.alert_type,
                server_scope=r.server_scope,
                target_id=r.target_id,
                emails=emails_list,
                created_at=r.created_at,
                condition_field=r.condition_field,
                condition_op=r.condition_op,
                condition_value=r.condition_value,
                duration_seconds=r.duration_seconds,
                severity=r.severity
            ))
        return res

@app.post("/api/admin/alert-rules", response_model=AlertRuleResponse)
def create_alert_rule(payload: AlertRuleCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        new_rule = AlertRule(
            alert_type=payload.alert_type,
            server_scope=payload.server_scope,
            target_id=payload.target_id,
            emails=json.dumps(payload.emails),
            condition_field=payload.condition_field,
            condition_op=payload.condition_op,
            condition_value=payload.condition_value,
            duration_seconds=payload.duration_seconds,
            severity=payload.severity
        )
        sess.add(new_rule)
        sess.commit()
        sess.refresh(new_rule)
        
        return AlertRuleResponse(
            id=new_rule.id,
            alert_type=new_rule.alert_type,
            server_scope=new_rule.server_scope,
            target_id=new_rule.target_id,
            emails=payload.emails,
            created_at=new_rule.created_at,
            condition_field=new_rule.condition_field,
            condition_op=new_rule.condition_op,
            condition_value=new_rule.condition_value,
            duration_seconds=new_rule.duration_seconds,
            severity=new_rule.severity
        )

@app.delete("/api/admin/alert-rules/{rule_id}")
def delete_alert_rule(rule_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        r = sess.get(AlertRule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Regla no encontrada")
        sess.delete(r)
        sess.commit()
        return {"status": "deleted"}

@app.put("/api/admin/servers/{server_id}/group")
def update_server_group(server_id: str, payload: ServerUpdateGroupSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Servidor no encontrado")
        srv.group_name = payload.group_name
        sess.commit()
        return {"status": "updated", "group_name": srv.group_name}


def log_audit(sess: Session, action: str, target_type: str, target_id: str, changes: dict, user_email: str):
    log_entry = AuditLog(
        action=action,
        target_type=target_type,
        target_id=target_id,
        changes=json.dumps(changes) if changes else None,
        user_email=user_email
    )
    sess.add(log_entry)


# --- Gestión de Umbrales (Thresholds) ---

@app.get("/api/umbrales", response_model=List[ServerThresholdResponse])
def list_thresholds(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        thresholds = sess.execute(select(ServerThreshold)).scalars().all()
        return thresholds

@app.get("/api/umbrales/{server_id}", response_model=ServerThresholdResponse)
def get_threshold(server_id: str, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        t = sess.execute(select(ServerThreshold).where(ServerThreshold.server_id == server_id)).scalar_one_or_none()
        if not t:
            # Si no existe, devolver uno vacío con el server_id
            return ServerThresholdResponse(server_id=server_id, cpu_threshold=None, memory_threshold=None, disk_threshold=None, updated_at=None)
        return t

@app.put("/api/umbrales/{server_id}", response_model=ServerThresholdResponse)
def update_threshold(server_id: str, payload: ServerThresholdUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        # Check if server exists
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
             raise HTTPException(status_code=404, detail="Servidor no encontrado")
             
        t = sess.execute(select(ServerThreshold).where(ServerThreshold.server_id == server_id)).scalar_one_or_none()
        
        changes = {}
        if not t:
            t = ServerThreshold(server_id=server_id)
            sess.add(t)
            changes["created"] = True
            
        if payload.cpu_threshold is not None:
            changes["cpu_threshold"] = {"old": t.cpu_threshold, "new": payload.cpu_threshold}
            t.cpu_threshold = payload.cpu_threshold
            
        if payload.memory_threshold is not None:
            changes["memory_threshold"] = {"old": t.memory_threshold, "new": payload.memory_threshold}
            t.memory_threshold = payload.memory_threshold
            
        if payload.disk_threshold is not None:
            changes["disk_threshold"] = {"old": t.disk_threshold, "new": payload.disk_threshold}
            t.disk_threshold = payload.disk_threshold
            
        # Log Audit
        log_audit(sess, "update", "threshold", server_id, changes, user["email"])
        
        sess.commit()
        sess.refresh(t)
        
        # Update Cache
        _threshold_cache[server_id] = {
            "cpu": t.cpu_threshold,
            "memory": t.memory_threshold,
            "disk": t.disk_threshold
        }
        
        return t

@app.get("/api/umbrales/export", response_model=List[ServerThresholdResponse])
def export_thresholds(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        thresholds = sess.execute(select(ServerThreshold)).scalars().all()
        return thresholds

@app.post("/api/umbrales/import")
def import_thresholds(payload: List[ServerThresholdImport], user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        count = 0
        for item in payload:
            # Validate server exists
            srv = sess.execute(select(Server).where(Server.server_id == item.server_id)).scalar_one_or_none()
            if not srv:
                continue 
            
            t = sess.execute(select(ServerThreshold).where(ServerThreshold.server_id == item.server_id)).scalar_one_or_none()
            if not t:
                t = ServerThreshold(server_id=item.server_id)
                sess.add(t)
            
            t.cpu_threshold = item.cpu_threshold
            t.memory_threshold = item.memory_threshold
            t.disk_threshold = item.disk_threshold
            
            count += 1
        
        sess.commit()
        
        # Clear cache to force reload
        _threshold_cache.clear()
        
        return {"status": "imported", "count": count}

# --- Webhook Endpoint ---

@app.get("/api/webhook")
def verify_webhook(token: str = Query(...)):
    """
    Verifica que el webhook esté activo y el token sea recibido correctamente.
    """
    masked = (token[:4] + "***") if token else ""
    logger.info(f"Webhook verification request received (token={masked})")
    return {"status": "active", "message": "Webhook endpoint is ready"}

@app.post("/api/webhook")
async def receive_webhook(request: Request, token: str = Query(...)):
    """
    Recibe datos vía Webhook para auditoría (IDataMonitoring).
    Valida que el token corresponda a un servidor registrado y que tenga habilitado el webhook.
    """
    with Session(engine) as sess:
        # 1. Validar token del servidor
        server = sess.execute(select(Server).where(Server.token == token)).scalar_one_or_none()
        if not server:
            raise HTTPException(status_code=403, detail="Invalid token")
            
        # 2. Validar si tiene habilitado el monitoreo
        if not server.webhook_enabled:
             raise HTTPException(status_code=403, detail="Webhook data collection is disabled for this server")

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        # 3. Validar payload (opcionalmente con Pydantic, aquí lo hacemos manual/flexible o usamos DataMonitoringSchema)
        # Intentamos parsear con Pydantic para validación
        try:
            data = DataMonitoringSchema(**body)
        except Exception as e:
            # Si el payload no coincide con IDataMonitoring, lo rechazamos o lo guardamos como 'raw' (pero el requerimiento es específico)
            logger.warning(f"Webhook payload validation failed: {e}")
            raise HTTPException(status_code=422, detail=f"Invalid payload structure: {str(e)}")
            
        # 4. Guardar en DB
        new_record = DataMonitoring(
            server_id=server.server_id,
            app=data.app,
            cash_register_number=data.cashRegisterNumber,
            user_name=data.userName,
            flow=data.flow,
            patent=data.patent,
            vehicle_type=data.vehicleType,
            product=data.product,
            entity_id=data.entityId,
            working_day=data.workingDay,
            client_created_at=datetime.fromisoformat(data.createdAt.replace('Z', '+00:00')) if data.createdAt else None
        )
        sess.add(new_record)
        sess.commit()
        
        logger.info(f"DataMonitoring stored for server {server.server_id}")
    
    return {"status": "received", "server_id": server.server_id}

# --- Data Monitoring Endpoints ---

@app.get("/api/servers/{server_id}/data-monitoring", response_model=List[DataMonitoringResponse])
def get_server_monitoring_data(
    server_id: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user_from_token)
):
    """
    Obtiene los datos de monitoreo para un servidor (para gráficos).
    """
    with Session(engine) as sess:
        # Verificar acceso
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Server not found")
            
        if not user["is_admin"]:
            # Verificar asignación
            link = sess.execute(
                select(UserServerLink)
                .where(UserServerLink.user_id == user["user_id"])
                .where(UserServerLink.server_id == srv.id)
            ).scalar_one_or_none()
            if not link:
                raise HTTPException(status_code=403, detail="Access denied")

        query = select(DataMonitoring).where(DataMonitoring.server_id == server_id)
        
        if start_date:
            try:
                dt_start = datetime.fromisoformat(start_date)
                query = query.where(DataMonitoring.created_at >= dt_start)
            except: pass
            
        if end_date:
            try:
                dt_end = datetime.fromisoformat(end_date)
                query = query.where(DataMonitoring.created_at <= dt_end)
            except: pass
            
        query = query.order_by(DataMonitoring.created_at.desc()).limit(limit)
        
        results = sess.execute(query).scalars().all()
        return results

@app.put("/api/servers/{server_id}/webhook-config")
def update_server_webhook_config(
    server_id: str, 
    payload: ServerWebhookConfigUpdate, 
    user: dict = Depends(require_admin)
):
    """
    Activa o desactiva la recepción de datos vía webhook para un servidor.
    """
    with Session(engine) as sess:
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Server not found")
            
        srv.webhook_enabled = payload.webhook_enabled
        sess.commit()
        
        status_msg = "enabled" if srv.webhook_enabled else "disabled"
        log_audit(sess, "update_webhook_config", "server", server_id, {"enabled": srv.webhook_enabled}, user["email"])
        
        return {"status": "updated", "server_id": server_id, "webhook_enabled": srv.webhook_enabled}


# --- User Personal Thresholds ---

@app.get("/api/servers/{server_id}/thresholds/me", response_model=UserServerThresholdResponse)
def get_my_server_threshold(server_id: str, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        # Get Server PK for Link check
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        
        # Get Subscription Status
        receive_alerts = True
        if srv:
            link = sess.execute(
                select(UserServerLink)
                .where(UserServerLink.user_id == user["user_id"])
                .where(UserServerLink.server_id == srv.id)
            ).scalar_one_or_none()
            if link:
                receive_alerts = link.receive_alerts

        # Get Thresholds
        t = sess.execute(
            select(UserServerThreshold)
            .where(UserServerThreshold.server_id == server_id)
            .where(UserServerThreshold.user_id == user["user_id"])
        ).scalar_one_or_none()
        
        if not t:
            return UserServerThresholdResponse(
                server_id=server_id,
                user_id=user["user_id"],
                cpu_limit=None,
                mem_limit=None,
                disk_limit=None,
                created_at=None,
                updated_at=None,
                id=0,
                receive_alerts=receive_alerts
            )
            
        return UserServerThresholdResponse(
            id=t.id,
            user_id=t.user_id,
            server_id=t.server_id,
            cpu_limit=t.cpu_limit,
            mem_limit=t.mem_limit,
            disk_limit=t.disk_limit,
            created_at=t.created_at,
            updated_at=t.updated_at,
            receive_alerts=receive_alerts
        )

@app.put("/api/servers/{server_id}/thresholds/me", response_model=UserServerThresholdResponse)
def update_my_server_threshold(server_id: str, payload: UserServerThresholdUpdate, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        # Verify server exists
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Server not found")

        # Get Subscription Status (read-only here, updated via separate endpoint)
        receive_alerts = True
        link = sess.execute(
            select(UserServerLink)
            .where(UserServerLink.user_id == user["user_id"])
            .where(UserServerLink.server_id == srv.id)
        ).scalar_one_or_none()
        if link:
            receive_alerts = link.receive_alerts

        if not user["is_admin"]:
             if not link:
                 # Implicit permission check: if no link and not admin, technically they shouldn't be editing?
                 # But we allow creating thresholds.
                 pass

        t = sess.execute(
            select(UserServerThreshold)
            .where(UserServerThreshold.server_id == server_id)
            .where(UserServerThreshold.user_id == user["user_id"])
        ).scalar_one_or_none()
        
        if not t:
            t = UserServerThreshold(
                server_id=server_id,
                user_id=user["user_id"]
            )
            sess.add(t)
        
        # Use exclude_unset to distinguish between missing (ignore) and None (clear)
        update_data = payload.dict(exclude_unset=True)
        
        if "cpu_limit" in update_data:
            t.cpu_limit = update_data["cpu_limit"]
        if "mem_limit" in update_data:
            t.mem_limit = update_data["mem_limit"]
        if "disk_limit" in update_data:
            t.disk_limit = update_data["disk_limit"]
            
        t.updated_at = datetime.now(timezone.utc)
        
        sess.commit()
        sess.refresh(t)
        
        return UserServerThresholdResponse(
            id=t.id,
            user_id=t.user_id,
            server_id=t.server_id,
            cpu_limit=t.cpu_limit,
            mem_limit=t.mem_limit,
            disk_limit=t.disk_limit,
            created_at=t.created_at,
            updated_at=t.updated_at,
            receive_alerts=receive_alerts
        )

@app.put("/api/servers/{server_id}/subscription")
def update_server_subscription(server_id: str, payload: ServerSubscriptionUpdate, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        # Verify server exists
        srv = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
        if not srv:
            raise HTTPException(status_code=404, detail="Server not found")
            
        # Check/Create Link
        link = sess.execute(
            select(UserServerLink)
            .where(UserServerLink.user_id == user["user_id"])
            .where(UserServerLink.server_id == srv.id)
        ).scalar_one_or_none()
        
        if not link:
            # If link doesn't exist, create it? 
            # If users are strictly managed, maybe not. 
            # But for "Personalization", allowing them to subscribe if they have access (which we assume if they know the ID or we should check visibility)
            # For now, let's assume if they can call this, they want to track it.
            # However, list_servers logic restricts what they see.
            # If they are admin, they see all. If not, they see assigned.
            # If not assigned, they shouldn't be able to subscribe?
            if not user["is_admin"]:
                 raise HTTPException(status_code=403, detail="Server not assigned to user")
            else:
                # Admin can create a link for themselves
                link = UserServerLink(user_id=user["user_id"], server_id=srv.id, receive_alerts=payload.receive_alerts)
                sess.add(link)
        else:
            link.receive_alerts = payload.receive_alerts
            
        sess.commit()
        return {"status": "updated", "server_id": server_id, "receive_alerts": payload.receive_alerts}

@app.get("/api/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        logs = sess.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)).scalars().all()
        return logs


@app.post("/api/metrics")
def ingest_metrics(payload: MetricsIngestSchema, x_auth_token: Optional[str] = Header(None)):
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    with Session(engine) as sess:
        srv = sess.execute(select(Server).where(Server.server_id == payload.server_id)).scalar_one_or_none()
        if not srv or srv.token != x_auth_token:
            raise HTTPException(status_code=403, detail="Unauthorized server or bad token")

        # Validaciones de rango
        if not (0 <= payload.cpu.total <= 100):
            raise HTTPException(status_code=422, detail="cpu.total fuera de rango")
        if any(c < 0 or c > 100 for c in payload.cpu.per_core):
            raise HTTPException(status_code=422, detail="cpu.per_core fuera de rango")
        if payload.memory.used > payload.memory.total or payload.memory.total <= 0:
            raise HTTPException(status_code=422, detail="memoria inválida")
        if not (0 <= payload.disk.percent <= 100):
            raise HTTPException(status_code=422, detail="disk.percent fuera de rango")

        if srv.report_interval > 0:
            m = Metric(
                server_id=payload.server_id,
                mem_total=payload.memory.total,
                mem_used=payload.memory.used,
                mem_free=payload.memory.free,
                mem_cache=payload.memory.cache,
                cpu_total=payload.cpu.total,
                cpu_per_core=json.dumps(payload.cpu.per_core),
                disk_total=payload.disk.total,
                disk_used=payload.disk.used,
                disk_free=payload.disk.free,
                disk_percent=payload.disk.percent,
                net_bytes_sent=payload.network.bytes_sent if payload.network else 0,
                net_bytes_recv=payload.network.bytes_recv if payload.network else 0,
                net_sent_rate=payload.network.sent_rate if payload.network and payload.network.sent_rate is not None else 0.0,
                net_recv_rate=payload.network.recv_rate if payload.network and payload.network.recv_rate is not None else 0.0,
                uptime_seconds=payload.uptime if payload.uptime else 0,
                docker_running=payload.docker.running_containers,
                docker_containers=json.dumps([c.model_dump() for c in payload.docker.containers]),
                services=json.dumps([s.model_dump() for s in payload.services]) if payload.services else "[]",
                processes=json.dumps([p.model_dump() for p in payload.processes]) if payload.processes else "[]",
            )
            sess.add(m)
            sess.commit()
        else:
             # Si el intervalo es 0, no guardamos métricas (modo desactivado/heartbeat)
             pass

        try:
            logging.info(
                "Metrics update for server_id=%s at %s (report_interval=%s)",
                payload.server_id,
                datetime.utcnow().isoformat() + "Z",
                srv.report_interval,
            )
        except Exception:
            pass

        # Verificar Alertas
        try:
            # Cargar configuración de alertas global
            alert_cfg = sess.execute(select(AlertConfig)).scalar_one_or_none()
            
            # Cargar umbrales específicos (con caché)
            thresholds = _threshold_cache.get(payload.server_id)
            if thresholds is None:
                # Si no está en caché, buscar en DB
                t_db = sess.execute(select(ServerThreshold).where(ServerThreshold.server_id == payload.server_id)).scalar_one_or_none()
                if t_db:
                    thresholds = {
                        "cpu": t_db.cpu_threshold,
                        "memory": t_db.memory_threshold,
                        "disk": t_db.disk_threshold
                    }
                else:
                    thresholds = {}
                _threshold_cache[payload.server_id] = thresholds
            
            # --- Check Advanced Rules ---
            check_advanced_rules(sess, srv, payload, _advanced_alert_state)
            
            # Definir límites efectivos (Global vs Específico)
            # Prioridad: Específico > Global
            
            cpu_limit = thresholds.get("cpu")
            if cpu_limit is None and alert_cfg:
                cpu_limit = alert_cfg.cpu_total_percent
                
            mem_limit = thresholds.get("memory")
            if mem_limit is None and alert_cfg:
                mem_limit = alert_cfg.memory_used_percent
                
            disk_limit = thresholds.get("disk")
            if disk_limit is None and alert_cfg:
                disk_limit = alert_cfg.disk_used_percent

            # Datos completos para el correo
            full_metrics = payload.model_dump()
            current_time = time.time()
            
            # Check CPU
            if cpu_limit and cpu_limit > 0 and payload.cpu.total >= cpu_limit:
                key = (payload.server_id, "cpu")
                last_sent = _alert_state.get(key, 0)
                if current_time - last_sent > ALERT_COOLDOWN:
                    recipients, applied_rules = get_alert_recipients(sess, srv, "cpu")
                    print(f"[ALERT] Sending CPU alert for {srv.server_id}. Threshold: {cpu_limit}% (Global or Custom). Applied rules: {applied_rules}")
                    send_alert_email(payload.server_id, "CPU Alta", payload.cpu.total, cpu_limit, recipients, full_metrics)
                    _alert_state[key] = current_time
            
            # Check Memory
            mem_percent = (payload.memory.used / payload.memory.total) * 100 if payload.memory.total > 0 else 0
            if mem_limit and mem_limit > 0 and mem_percent >= mem_limit:
                key = (payload.server_id, "memory")
                last_sent = _alert_state.get(key, 0)
                if current_time - last_sent > ALERT_COOLDOWN:
                    recipients, applied_rules = get_alert_recipients(sess, srv, "memory")
                    print(f"[ALERT] Sending Memory alert for {srv.server_id}. Threshold: {mem_limit}% (Global or Custom). Applied rules: {applied_rules}")
                    send_alert_email(payload.server_id, "Memoria Alta", mem_percent, mem_limit, recipients, full_metrics)
                    _alert_state[key] = current_time

            # Check Disk
            if disk_limit and disk_limit > 0 and payload.disk.percent >= disk_limit:
                key = (payload.server_id, "disk")
                last_sent = _alert_state.get(key, 0)
                if current_time - last_sent > ALERT_COOLDOWN:
                    recipients, applied_rules = get_alert_recipients(sess, srv, "disk")
                    print(f"[ALERT] Sending Disk alert for {srv.server_id}. Threshold: {disk_limit}% (Global or Custom). Applied rules: {applied_rules}")
                    send_alert_email(payload.server_id, "Disco Lleno", payload.disk.percent, disk_limit, recipients, full_metrics)
                    _alert_state[key] = current_time

            # --- User Specific Thresholds ---
            user_thresholds = sess.execute(select(UserServerThreshold).where(UserServerThreshold.server_id == payload.server_id)).scalars().all()
            for ut in user_thresholds:
                # Check CPU
                if ut.cpu_limit and payload.cpu.total >= ut.cpu_limit:
                    key = (payload.server_id, ut.user_id, "cpu")
                    last_sent = _alert_state.get(key, 0)
                    if current_time - last_sent > ALERT_COOLDOWN:
                        user_obj = sess.get(User, ut.user_id)
                        if user_obj and user_obj.receive_alerts: # Check if user wants alerts globally
                             print(f"[ALERT] Sending User CPU alert for {srv.server_id} to {user_obj.email}")
                             send_alert_email(payload.server_id, "CPU Alta (Personal)", payload.cpu.total, ut.cpu_limit, [{"email": user_obj.email, "name": user_obj.name}], full_metrics)
                             _alert_state[key] = current_time
                
                # Check Memory
                mem_pct = (payload.memory.used / payload.memory.total) * 100 if payload.memory.total > 0 else 0
                if ut.mem_limit and mem_pct >= ut.mem_limit:
                    key = (payload.server_id, ut.user_id, "memory")
                    last_sent = _alert_state.get(key, 0)
                    if current_time - last_sent > ALERT_COOLDOWN:
                         user_obj = sess.get(User, ut.user_id)
                         if user_obj and user_obj.receive_alerts:
                             send_alert_email(payload.server_id, "Memoria Alta (Personal)", mem_pct, ut.mem_limit, [{"email": user_obj.email, "name": user_obj.name}], full_metrics)
                             _alert_state[key] = current_time
                             
                # Check Disk
                if ut.disk_limit and payload.disk.percent >= ut.disk_limit:
                    key = (payload.server_id, ut.user_id, "disk")
                    last_sent = _alert_state.get(key, 0)
                    if current_time - last_sent > ALERT_COOLDOWN:
                         user_obj = sess.get(User, ut.user_id)
                         if user_obj and user_obj.receive_alerts:
                             send_alert_email(payload.server_id, "Disco Lleno (Personal)", payload.disk.percent, ut.disk_limit, [{"email": user_obj.email, "name": user_obj.name}], full_metrics)
                             _alert_state[key] = current_time

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error checking alerts: {e}")

        # Actualizar caché en memoria
        try:
            entry = {
                "server_id": payload.server_id,
                "ts": str(m.ts),
                "memory": payload.memory.model_dump(),
                "cpu": payload.cpu.model_dump(),
                "disk": payload.disk.model_dump(),
                "network": {
                    "bytes_sent": m.net_bytes_sent,
                    "bytes_recv": m.net_bytes_recv,
                    "sent_rate": m.net_sent_rate,
                    "recv_rate": m.net_recv_rate,
                },
                "uptime": m.uptime_seconds,
                "docker": payload.docker.model_dump(),
                "services": [s.model_dump() for s in payload.services] if payload.services else [],
                "processes": [p.model_dump() for p in payload.processes] if payload.processes else [],
            }
            buf = _cache.get(payload.server_id)
            if not buf:
                buf = []
                _cache[payload.server_id] = buf
            buf.append(entry)
            if len(buf) > CACHE_MAX_ITEMS:
                # recortar dejado en el inicio
                del buf[: len(buf) - CACHE_MAX_ITEMS]
        except Exception:
            # No bloquear por errores de caché
            pass
        return {"status": "ok", "report_interval": srv.report_interval}


@app.get("/api/metrics/history")
def metrics_history(
    server_id: Optional[str] = None, 
    limit: int = 100, 
    hours: Optional[int] = None,
    user: dict = Depends(get_current_user_from_token)
):
    # Intentar servir desde caché si es posible (solo si no se pide historial específico)
    if server_id and server_id in _cache and not hours:
        buf = _cache[server_id]
        if len(buf) >= 1:
            return buf[-limit:]
            
    with Session(engine) as sess:
        try:
            q = select(Metric).order_by(Metric.id.desc())
            
            if server_id:
                q = q.where(Metric.server_id == server_id)
                
            if hours:
                # Filtrar por tiempo
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                q = q.where(Metric.ts >= cutoff)
            
            # Aplicar limite siempre por seguridad/paginación
            q = q.limit(limit)
            
            # Optimización: No cargar columnas pesadas (JSON) por defecto
            # Se cargarán automáticamente (lazy load) SOLO si se accede a ellas (para el último item)
            q = q.options(
                defer(Metric.cpu_per_core),
                defer(Metric.docker_containers),
                defer(Metric.services),
                defer(Metric.processes)
            )
            
            rows = sess.execute(q).scalars().all()
            rows = list(reversed(rows))
            
            def row_to_dict(r: Metric, include_details: bool = False):
                base = {
                    "ts": str(r.ts),
                    "memory": {"used": r.mem_used, "total": r.mem_total},
                    "cpu": {"total": r.cpu_total},
                    "disk": {"percent": r.disk_percent},
                }
                
                if include_details:
                    base.update({
                        "server_id": r.server_id,
                        "memory": {"total": r.mem_total, "used": r.mem_used, "free": r.mem_free, "cache": r.mem_cache},
                        "cpu": {"total": r.cpu_total, "per_core": json.loads(r.cpu_per_core or "[]")},
                        "disk": {"total": r.disk_total, "used": r.disk_used, "free": r.disk_free, "percent": r.disk_percent},
                        "network": {
                            "bytes_sent": r.net_bytes_sent, 
                            "bytes_recv": r.net_bytes_recv,
                            "sent_rate": getattr(r, "net_sent_rate", 0.0),
                            "recv_rate": getattr(r, "net_recv_rate", 0.0)
                        },
                        "uptime": r.uptime_seconds,
                        "docker": {"running_containers": r.docker_running, "containers": json.loads(r.docker_containers or "[]")},
                        "services": json.loads(r.services or "[]"),
                        "processes": json.loads(r.processes or "[]"),
                    })
                return base
            
            data = []
            for i, r in enumerate(rows):
                # Include details only for the last item (most recent)
                is_last = (i == len(rows) - 1)
                data.append(row_to_dict(r, include_details=is_last))
                
            if server_id:
                _cache[server_id] = data[-CACHE_MAX_ITEMS:]
            return data
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error consultando historial: {str(e)}")


@app.get("/api/alerts")
def get_alerts(user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        cfg = sess.execute(select(AlertConfig)).scalar_one()
        return {
            "cpu_total_percent": cfg.cpu_total_percent,
            "memory_used_percent": cfg.memory_used_percent,
            "disk_used_percent": cfg.disk_used_percent,
        }


@app.post("/api/alerts")
def set_alerts(payload: AlertConfigSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        cfg = sess.execute(select(AlertConfig)).scalar_one_or_none()
        if not cfg:
            cfg = AlertConfig(
                cpu_total_percent=payload.cpu_total_percent,
                memory_used_percent=payload.memory_used_percent,
                disk_used_percent=payload.disk_used_percent,
            )
            sess.add(cfg)
        else:
            cfg.cpu_total_percent = payload.cpu_total_percent
            cfg.memory_used_percent = payload.memory_used_percent
            cfg.disk_used_percent = payload.disk_used_percent
        sess.commit()
        return {"status": "updated"}

@app.get("/api/admin/logs")
def get_server_logs(lines: int = 100, user: dict = Depends(require_admin)):
    """
    Retorna las últimas N líneas del archivo de logs del servidor.
    """
    if not LOG_FILE.exists():
        return {"logs": ["Log file not found."]}
    
    try:
        # Leer las últimas líneas de manera eficiente (simple implementation)
        # Para archivos muy grandes, usar 'deque' o 'seek' sería mejor, pero esto basta por ahora.
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"logs": [f"Error reading logs: {str(e)}"]}



# --- SMTP Configuration ---

@app.get("/api/admin/smtp/config", response_model=SMTPConfigResponse)
def get_smtp_config_endpoint(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        config = sess.execute(select(SMTPConfig)).scalars().first()
        if not config:
            raise HTTPException(status_code=404, detail="SMTP Config not found")
        return config

@app.post("/api/admin/smtp/config")
def update_smtp_config_endpoint(payload: SMTPConfigSchema, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        config = sess.execute(select(SMTPConfig)).scalars().first()
        is_new = False
        if not config:
            config = SMTPConfig()
            sess.add(config)
            is_new = True
        
        config.host = payload.host
        config.port = payload.port
        config.username = payload.username
        config.use_ssl = payload.use_ssl
        config.use_tls = payload.use_tls
        config.sender_email = payload.sender_email
        
        if payload.password:
             config.password_encrypted = encrypt_password(payload.password)
        
        sess.commit()
        
        action = "CREATE" if is_new else "UPDATE"
        log_audit(sess, action, "SMTP_CONFIG", str(config.id), "Updated SMTP settings", user["email"])
        
        return {"status": "updated"}

@app.post("/api/admin/smtp/test")
def test_smtp_config_endpoint(payload: SMTPConfigSchema, user: dict = Depends(require_admin)):
    try:
        server = smtplib.SMTP(payload.host, payload.port)
        if payload.use_tls:
            server.starttls()
        
        password = payload.password
        if not password:
             with Session(engine) as sess:
                config = sess.execute(select(SMTPConfig)).scalars().first()
                if config and config.password_encrypted:
                     password = decrypt_password(config.password_encrypted)
        
        if payload.username and password:
            server.login(payload.username, password)
            
        msg = MIMEMultipart()
        msg["Subject"] = "Test SMTP Configuration"
        msg["From"] = payload.sender_email
        msg["To"] = user["email"]
        msg.attach(MIMEText("This is a test email to verify SMTP configuration.", "plain"))
        
        server.sendmail(payload.sender_email, [user["email"]], msg.as_string())
        server.quit()
        return {"status": "success", "message": f"Test email sent to {user['email']}"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
def health():
    try:
        with Session(engine) as sess:
            sess.execute(select(Server)).first()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/metrics/export")
def export_metrics(
    format: str = "csv", 
    server_id: Optional[str] = None, 
    hours: int = 24,
    user: dict = Depends(get_current_user_from_token)
):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Generator for CSV streaming
    def iter_csv():
        yield "server_id,timestamp,cpu_total,memory_used_percent,disk_percent\n"
        with Session(engine) as sess:
            q = select(Metric).where(Metric.ts >= cutoff).order_by(Metric.ts.desc())
            if server_id:
                q = q.where(Metric.server_id == server_id)
            
            # Use yield_per to stream results efficiently
            results = sess.execute(q.execution_options(yield_per=1000)).scalars()
            
            for m in results:
                mem_pct = (m.mem_used / m.mem_total * 100) if m.mem_total and m.mem_total > 0 else 0
                # Format timestamp
                ts_str = m.ts.isoformat() if m.ts else ""
                yield f"{m.server_id},{ts_str},{m.cpu_total},{mem_pct:.2f},{m.disk_percent}\n"

    if format.lower() == 'csv':
        filename = f"metrics_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter_csv(), 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
            
    elif format.lower() == 'json':
        with Session(engine) as sess:
            q = select(Metric).where(Metric.ts >= cutoff).order_by(Metric.ts.desc())
            if server_id:
                q = q.where(Metric.server_id == server_id)
            
            # Limit JSON to avoid massive memory usage since we're not streaming JSON here
            rows = sess.execute(q.limit(10000)).scalars().all()
            
            data = [
                {
                    "server_id": r.server_id,
                    "ts": str(r.ts),
                    "cpu": r.cpu_total,
                    "memory_pct": (r.mem_used / r.mem_total * 100) if r.mem_total and r.mem_total > 0 else 0,
                    "disk_pct": r.disk_percent
                }
                for r in rows
            ]
            return data
            
    raise HTTPException(status_code=400, detail="Invalid format. Use 'csv' or 'json'.")

# --- User Groups Management ---

@app.get("/api/admin/groups", response_model=List[UserGroupResponse])
def list_user_groups(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        groups = sess.execute(select(UserGroup)).scalars().all()
        res = []
        for g in groups:
            user_ids = [u.id for u in g.users]
            res.append(UserGroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                created_at=g.created_at,
                user_count=len(g.users),
                user_ids=user_ids
            ))
        return res

@app.post("/api/admin/groups", response_model=UserGroupResponse)
def create_user_group(payload: UserGroupCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        existing = sess.execute(select(UserGroup).where(UserGroup.name == payload.name)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Group name already exists")
        
        new_group = UserGroup(
            name=payload.name,
            description=payload.description
        )
        
        if payload.user_ids:
            users = sess.execute(select(User).where(User.id.in_(payload.user_ids))).scalars().all()
            new_group.users = users
            
        sess.add(new_group)
        sess.commit()
        sess.refresh(new_group)
        
        return UserGroupResponse(
            id=new_group.id,
            name=new_group.name,
            description=new_group.description,
            created_at=new_group.created_at,
            user_count=len(new_group.users),
            user_ids=[u.id for u in new_group.users]
        )

@app.put("/api/admin/groups/{group_id}", response_model=UserGroupResponse)
def update_user_group(group_id: int, payload: UserGroupUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        group = sess.get(UserGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
            
        if payload.name:
            if payload.name != group.name:
                 existing = sess.execute(select(UserGroup).where(UserGroup.name == payload.name)).scalar_one_or_none()
                 if existing:
                     raise HTTPException(status_code=400, detail="Group name already exists")
            group.name = payload.name
            
        if payload.description is not None:
            group.description = payload.description
            
        if payload.user_ids is not None:
            users = sess.execute(select(User).where(User.id.in_(payload.user_ids))).scalars().all()
            group.users = users
            
        sess.commit()
        sess.refresh(group)
        
        return UserGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            user_count=len(group.users),
            user_ids=[u.id for u in group.users]
        )

@app.delete("/api/admin/groups/{group_id}")
def delete_user_group(group_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        group = sess.get(UserGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        sess.delete(group)
        sess.commit()
        return {"status": "deleted"}


# --- Notification Rules Management ---

@app.get("/api/admin/notification-rules", response_model=List[NotificationRuleResponse])
def list_notification_rules(
    user_id: Optional[int] = None, 
    group_id: Optional[int] = None,
    user: dict = Depends(require_admin)
):
    with Session(engine) as sess:
        q = select(NotificationRule)
        if user_id:
            q = q.where(NotificationRule.user_id == user_id)
        if group_id:
            q = q.where(NotificationRule.group_id == group_id)
        
        rules = sess.execute(q).scalars().all()
        return rules

@app.post("/api/admin/notification-rules", response_model=NotificationRuleResponse)
def create_notification_rule(payload: NotificationRuleCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        q = select(NotificationRule).where(
            NotificationRule.action == payload.action,
            NotificationRule.server_id == payload.server_id
        )
        if payload.user_id:
            q = q.where(NotificationRule.user_id == payload.user_id)
        elif payload.group_id:
            q = q.where(NotificationRule.group_id == payload.group_id)
        else:
             raise HTTPException(status_code=400, detail="Must specify user_id or group_id")
             
        existing = sess.execute(q).scalar_one_or_none()
        if existing:
            return existing

        new_rule = NotificationRule(
            user_id=payload.user_id,
            group_id=payload.group_id,
            server_id=payload.server_id,
            action=payload.action
        )
        sess.add(new_rule)
        sess.commit()
        sess.refresh(new_rule)
        return new_rule

@app.delete("/api/admin/notification-rules/{rule_id}")
def delete_notification_rule(rule_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        rule = sess.get(NotificationRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        sess.delete(rule)
        sess.commit()
        return {"status": "deleted"}

@app.post("/api/admin/alert-preview", response_model=AlertPreviewResponse)
def preview_alert_decision(payload: AlertPreviewRequest, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        result = explain_alert_decision(sess, payload.user_id, payload.server_id)
        return AlertPreviewResponse(**result)


# --- User Server Thresholds ---

@app.get("/api/user/thresholds/{server_id}", response_model=UserServerThresholdResponse)
def get_user_server_threshold(server_id: str, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        ut = sess.execute(select(UserServerThreshold).where(
            UserServerThreshold.user_id == user["user_id"],
            UserServerThreshold.server_id == server_id
        )).scalar_one_or_none()

        if not ut:
            # Return empty/default structure if not found, with dummy id
            return UserServerThresholdResponse(id=0, user_id=user["user_id"], server_id=server_id)
        return ut

@app.post("/api/user/thresholds", response_model=UserServerThresholdResponse)
def set_user_server_threshold(payload: UserServerThresholdUpdate, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        ut = sess.execute(select(UserServerThreshold).where(
            UserServerThreshold.user_id == user["user_id"],
            UserServerThreshold.server_id == payload.server_id
        )).scalar_one_or_none()

        if not ut:
            ut = UserServerThreshold(
                user_id=user["user_id"],
                server_id=payload.server_id,
                cpu_limit=payload.cpu_limit,
                mem_limit=payload.mem_limit,
                disk_limit=payload.disk_limit
            )
            sess.add(ut)
        else:
            ut.cpu_limit = payload.cpu_limit
            ut.mem_limit = payload.mem_limit
            ut.disk_limit = payload.disk_limit
        
        sess.commit()
        sess.refresh(ut)
        return ut


# ============================================================
# --- Gestión Proxmox (SSH + WireGuard) ---
# Todos los endpoints requieren admin y registran auditoría.
# ============================================================

def _pmx_get_node(sess: Session, node_id: int) -> ProxmoxNode:
    node = sess.get(ProxmoxNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Nodo Proxmox no encontrado")
    return node


def _pmx_get_guest(sess: Session, guest_id: int) -> ProxmoxGuest:
    guest = sess.get(ProxmoxGuest, guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest no encontrado")
    return guest


# --- Nodos ---

@app.get("/api/proxmox/nodes", response_model=List[ProxmoxNodeResponse])
def pmx_list_nodes(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        return sess.execute(select(ProxmoxNode)).scalars().all()


@app.post("/api/proxmox/nodes", response_model=ProxmoxNodeResponse)
def pmx_create_node(payload: ProxmoxNodeCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        existing = sess.execute(select(ProxmoxNode).where(ProxmoxNode.name == payload.name)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un nodo con ese nombre")
        node = ProxmoxNode(
            name=payload.name,
            hostname=payload.hostname,
            ssh_port=payload.ssh_port,
            ssh_user=payload.ssh_user,
            auth_type=payload.auth_type,
            secret_encrypted=encrypt_password(payload.secret),
            use_sudo=payload.use_sudo,
        )
        sess.add(node)
        sess.commit()
        sess.refresh(node)
        # Best-effort: registrar la huella de host key (TOFU)
        try:
            node.host_key_fingerprint = get_host_fingerprint(node)
            sess.commit()
            sess.refresh(node)
        except Exception as e:
            logger.warning(f"No se pudo obtener la host key de {node.hostname}: {e}")
        log_audit(sess, "create", "proxmox_node", node.name, {"hostname": node.hostname}, user["email"])
        sess.commit()
        sess.refresh(node)
        return node


@app.delete("/api/proxmox/nodes/{node_id}")
def pmx_delete_node(node_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        node = _pmx_get_node(sess, node_id)
        name = node.name
        sess.delete(node)
        log_audit(sess, "delete", "proxmox_node", name, None, user["email"])
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/proxmox/nodes/{node_id}/test")
def pmx_test_node(node_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        node = _pmx_get_node(sess, node_id)
        try:
            version = pmx_service.test_connection(node)
        except SSHCommandError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"status": "ok", "version": version}


@app.post("/api/proxmox/nodes/{node_id}/sync")
def pmx_sync_node(node_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        node = _pmx_get_node(sess, node_id)
        try:
            guests = pmx_service.list_guests(node)
        except SSHCommandError as e:
            raise HTTPException(status_code=502, detail=str(e))

        # Conjunto de servidores monitoreados para auto-vinculación por nombre
        monitored = {s.server_id for s in sess.execute(select(Server)).scalars().all()}

        seen = set()
        for g in guests:
            seen.add((g["vmid"], g["guest_type"]))
            existing = sess.execute(
                select(ProxmoxGuest).where(
                    ProxmoxGuest.node_id == node.id,
                    ProxmoxGuest.vmid == g["vmid"],
                    ProxmoxGuest.guest_type == g["guest_type"],
                )
            ).scalar_one_or_none()
            if not existing:
                existing = ProxmoxGuest(node_id=node.id, vmid=g["vmid"], guest_type=g["guest_type"])
                sess.add(existing)
            existing.name = g.get("name")
            existing.status = g.get("status")
            existing.last_synced = datetime.utcnow()
            # Auto-vincular si el nombre coincide con un servidor monitoreado
            if existing.linked_server_id is None and g.get("name") in monitored:
                existing.linked_server_id = g.get("name")
        sess.commit()

        # Refrescar autodetección de BD
        try:
            pmx_dbdetect.detect_db_guests(sess)
        except Exception as e:
            logger.warning(f"Autodetección BD falló: {e}")

        log_audit(sess, "sync", "proxmox_node", node.name, {"guests": len(guests)}, user["email"])
        sess.commit()
        return {"status": "synced", "count": len(guests)}


# --- Guests: inventario, recursos, vinculación ---

@app.get("/api/proxmox/nodes/{node_id}/guests", response_model=List[ProxmoxGuestResponse])
def pmx_list_guests(node_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        _pmx_get_node(sess, node_id)
        return sess.execute(select(ProxmoxGuest).where(ProxmoxGuest.node_id == node_id)).scalars().all()


@app.put("/api/proxmox/guests/{guest_id}/resources")
def pmx_update_resources(guest_id: int, payload: GuestResourceUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        out = pmx_service.set_resources(
            node, guest.vmid, guest.guest_type,
            cores=payload.cores, memory=payload.memory,
            disk=payload.disk, disk_size=payload.disk_size,
        )
        log_audit(sess, "update_resources", "proxmox_guest", str(guest.vmid),
                  payload.dict(exclude_none=True), user["email"])
        sess.commit()
        return {"status": "ok", "output": out}


@app.post("/api/proxmox/guests/{guest_id}/power")
def pmx_power_action(guest_id: int, payload: GuestPowerRequest, user: dict = Depends(require_admin)):
    """Ciclo de vida de un guest: start/stop/shutdown/reboot/suspend/resume."""
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        out = pmx_service.power_action(node, guest.vmid, guest.guest_type, payload.action)
        log_audit(sess, f"power_{payload.action}", "proxmox_guest", str(guest.vmid),
                  {"action": payload.action}, user["email"])
        sess.commit()
        return {"status": "ok", "action": payload.action, "output": out}


@app.get("/api/proxmox/guests/{guest_id}/status")
def pmx_guest_status(guest_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        status = pmx_service.guest_status(node, guest.vmid, guest.guest_type)
        return {"vmid": guest.vmid, "guest_type": guest.guest_type, "status": status}


@app.put("/api/proxmox/guests/{guest_id}/link", response_model=ProxmoxGuestResponse)
def pmx_link_guest(guest_id: int, payload: GuestLinkUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        guest.linked_server_id = payload.linked_server_id
        # Reevaluar BD con el nuevo vínculo
        if payload.linked_server_id:
            guest.is_db = pmx_dbdetect.server_runs_db(sess, payload.linked_server_id)
        else:
            guest.is_db = False
        sess.commit()
        sess.refresh(guest)
        return guest


# --- Snapshots ---

@app.get("/api/proxmox/guests/{guest_id}/snapshots", response_model=List[SnapshotResponse])
def pmx_list_snapshots(guest_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        return pmx_service.list_snapshots(node, guest.vmid, guest.guest_type)


@app.post("/api/proxmox/guests/{guest_id}/snapshots")
def pmx_create_snapshot(guest_id: int, payload: SnapshotCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        out = pmx_service.create_snapshot(node, guest.vmid, guest.guest_type, payload.name, payload.description)
        sess.add(SnapshotRecord(node_id=node.id, vmid=guest.vmid, name=payload.name,
                                description=payload.description, created_by=user["email"]))
        log_audit(sess, "create_snapshot", "proxmox_guest", str(guest.vmid), {"name": payload.name}, user["email"])
        sess.commit()
        return {"status": "ok", "output": out}


@app.post("/api/proxmox/guests/{guest_id}/snapshots/{name}/rollback")
def pmx_rollback_snapshot(guest_id: int, name: str, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        out = pmx_service.rollback_snapshot(node, guest.vmid, guest.guest_type, name)
        log_audit(sess, "rollback_snapshot", "proxmox_guest", str(guest.vmid), {"name": name}, user["email"])
        sess.commit()
        return {"status": "ok", "output": out}


@app.delete("/api/proxmox/guests/{guest_id}/snapshots/{name}")
def pmx_delete_snapshot(guest_id: int, name: str, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        guest = _pmx_get_guest(sess, guest_id)
        node = _pmx_get_node(sess, guest.node_id)
        out = pmx_service.delete_snapshot(node, guest.vmid, guest.guest_type, name)
        log_audit(sess, "delete_snapshot", "proxmox_guest", str(guest.vmid), {"name": name}, user["email"])
        sess.commit()
        return {"status": "ok", "output": out}


# --- Backups programados ---

@app.get("/api/proxmox/backup-schedules", response_model=List[BackupScheduleResponse])
def pmx_list_schedules(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        return sess.execute(select(BackupSchedule)).scalars().all()


@app.post("/api/proxmox/backup-schedules", response_model=BackupScheduleResponse)
def pmx_create_schedule(payload: BackupScheduleCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        sched = BackupSchedule(
            name=payload.name, node_id=payload.node_id, cron_expr=payload.cron_expr,
            storage=payload.storage, mode=payload.mode, keep_last=payload.keep_last,
            only_db=payload.only_db, enabled=payload.enabled,
        )
        sess.add(sched)
        sess.commit()
        sess.refresh(sched)
        pmx_scheduler.add_schedule_job(sched)
        log_audit(sess, "create", "backup_schedule", sched.name, {"cron": sched.cron_expr}, user["email"])
        sess.commit()
        sess.refresh(sched)
        return sched


@app.put("/api/proxmox/backup-schedules/{schedule_id}", response_model=BackupScheduleResponse)
def pmx_update_schedule(schedule_id: int, payload: BackupScheduleUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        sched = sess.get(BackupSchedule, schedule_id)
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule no encontrado")
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(sched, field, value)
        sess.commit()
        sess.refresh(sched)
        # Re-registrar el job
        pmx_scheduler.remove_schedule_job(sched.id)
        if sched.enabled:
            pmx_scheduler.add_schedule_job(sched)
        log_audit(sess, "update", "backup_schedule", sched.name, payload.dict(exclude_unset=True), user["email"])
        sess.commit()
        sess.refresh(sched)
        return sched


@app.delete("/api/proxmox/backup-schedules/{schedule_id}")
def pmx_delete_schedule(schedule_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        sched = sess.get(BackupSchedule, schedule_id)
        if not sched:
            raise HTTPException(status_code=404, detail="Schedule no encontrado")
        name = sched.name
        sess.delete(sched)
        pmx_scheduler.remove_schedule_job(schedule_id)
        log_audit(sess, "delete", "backup_schedule", name, None, user["email"])
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/proxmox/backups/run", response_model=BackupJobResponse)
def pmx_run_backup(payload: BackupRunRequest, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        node = _pmx_get_node(sess, payload.node_id)
        job = BackupJob(node_id=node.id, vmid=payload.vmid, storage=payload.storage, status="running")
        sess.add(job)
        sess.commit()
        sess.refresh(job)
        try:
            rc, out, err = pmx_service.run_vzdump(node, payload.vmid, payload.storage, payload.mode)
            job.status = "ok" if rc == 0 else "error"
            job.output_log = (out or "") + (("\n" + err) if err else "")
        except HTTPException as e:
            job.status = "error"
            job.output_log = str(e.detail)
        except Exception as e:
            job.status = "error"
            job.output_log = str(e)
        job.finished_at = datetime.utcnow()
        log_audit(sess, "run_backup", "proxmox_guest", str(payload.vmid), {"storage": payload.storage}, user["email"])
        sess.commit()
        sess.refresh(job)
        return job


@app.get("/api/proxmox/backup-jobs", response_model=List[BackupJobResponse])
def pmx_list_backup_jobs(limit: int = 100, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        return sess.execute(
            select(BackupJob).order_by(BackupJob.id.desc()).limit(limit)
        ).scalars().all()


# --- Vinculación de nodos (túnel WireGuard) y migración ---

@app.get("/api/proxmox/links", response_model=List[NodeLinkResponse])
def pmx_list_links(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        return sess.execute(select(NodeLink)).scalars().all()


@app.post("/api/proxmox/links", response_model=NodeLinkResponse)
def pmx_create_link(payload: NodeLinkCreate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        if payload.source_node_id == payload.target_node_id:
            raise HTTPException(status_code=400, detail="El nodo origen y destino deben ser distintos")
        source = _pmx_get_node(sess, payload.source_node_id)
        target = _pmx_get_node(sess, payload.target_node_id)
        link = NodeLink(
            source_node_id=source.id, target_node_id=target.id,
            wg_interface=payload.wg_interface, listen_port=payload.listen_port,
        )
        sess.add(link)
        sess.commit()
        sess.refresh(link)
        try:
            pmx_wg.create_link(link, source, target)
        except HTTPException:
            link.status = "error"
            sess.commit()
            raise
        log_audit(sess, "create_link", "node_link", f"{source.name}->{target.name}",
                  {"interface": link.wg_interface}, user["email"])
        sess.commit()
        sess.refresh(link)
        return link


@app.delete("/api/proxmox/links/{link_id}")
def pmx_delete_link(link_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        link = sess.get(NodeLink, link_id)
        if not link:
            raise HTTPException(status_code=404, detail="Link no encontrado")
        source = sess.get(ProxmoxNode, link.source_node_id)
        target = sess.get(ProxmoxNode, link.target_node_id)
        try:
            if source and target:
                pmx_wg.teardown_link(link, source, target)
        except Exception as e:
            logger.warning(f"Error bajando túnel: {e}")
        sess.delete(link)
        log_audit(sess, "delete_link", "node_link", str(link_id), None, user["email"])
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/proxmox/migrate")
def pmx_migrate(payload: MigrateRequest, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        link = sess.get(NodeLink, payload.link_id)
        if not link:
            raise HTTPException(status_code=404, detail="Link no encontrado")
        source = _pmx_get_node(sess, link.source_node_id)
        target = _pmx_get_node(sess, link.target_node_id)
        out = pmx_wg.migrate_guest(
            link, source, target, payload.vmid, payload.guest_type,
            payload.storage, online=payload.online,
        )
        log_audit(sess, "migrate", "proxmox_guest", str(payload.vmid),
                  {"from": source.name, "to": target.name}, user["email"])
        sess.commit()
        return {"status": "migrated", "output": out}


# ============================================================
# --- Checks agentless (monitoreo server-side) ---
# ============================================================

@app.get("/api/monitoring/checks", response_model=List[MonitoringCheckResponse])
def list_monitoring_checks(user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        return sess.execute(select(MonitoringCheck)).scalars().all()


@app.post("/api/monitoring/checks", response_model=MonitoringCheckResponse)
def create_monitoring_check(payload: MonitoringCheckCreate, user: dict = Depends(require_admin)):
    mon_validators.validate_check_target(payload.check_type, payload.target, payload.port)
    with Session(engine) as sess:
        check = MonitoringCheck(
            name=payload.name, check_type=payload.check_type, target=payload.target,
            port=payload.port, interval_seconds=payload.interval_seconds,
            timeout_seconds=payload.timeout_seconds, expected_status=payload.expected_status,
            enabled=payload.enabled,
        )
        sess.add(check)
        log_audit(sess, "create", "monitoring_check", payload.name, {"type": payload.check_type}, user["email"])
        sess.commit()
        sess.refresh(check)
        return check


@app.put("/api/monitoring/checks/{check_id}", response_model=MonitoringCheckResponse)
def update_monitoring_check(check_id: int, payload: MonitoringCheckUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        check = sess.get(MonitoringCheck, check_id)
        if not check:
            raise HTTPException(status_code=404, detail="Check no encontrado")
        data = payload.dict(exclude_unset=True)
        # Si cambia el target o el puerto, revalidar contra el tipo actual del check.
        if "target" in data or "port" in data:
            new_target = data.get("target", check.target)
            new_port = data.get("port", check.port)
            mon_validators.validate_check_target(check.check_type, new_target, new_port)
        for field, value in data.items():
            setattr(check, field, value)
        sess.commit()
        sess.refresh(check)
        return check


@app.delete("/api/monitoring/checks/{check_id}")
def delete_monitoring_check(check_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        check = sess.get(MonitoringCheck, check_id)
        if not check:
            raise HTTPException(status_code=404, detail="Check no encontrado")
        sess.execute(delete(MonitoringCheckResult).where(MonitoringCheckResult.check_id == check_id))
        sess.delete(check)
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/monitoring/checks/{check_id}/run")
def run_monitoring_check(check_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        if not sess.get(MonitoringCheck, check_id):
            raise HTTPException(status_code=404, detail="Check no encontrado")
    result = mon_checks.execute_and_store(check_id)
    return {"status": "ok", "result": result}


@app.get("/api/monitoring/checks/{check_id}/results", response_model=List[MonitoringCheckResultResponse])
def list_check_results(check_id: int, limit: int = 100, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        return sess.execute(
            select(MonitoringCheckResult)
            .where(MonitoringCheckResult.check_id == check_id)
            .order_by(MonitoringCheckResult.id.desc()).limit(limit)
        ).scalars().all()


# ============================================================
# --- Auto-descubrimiento de red (estilo Zabbix) ---
# ============================================================

@app.post("/api/discovery/scan", response_model=DiscoveryScanResponse)
def discovery_scan(payload: DiscoveryScanRequest, user: dict = Depends(require_admin)):
    """Barre un CIDR y devuelve los hosts vivos; opcionalmente crea checks."""
    hosts = mon_discovery.discover_hosts(
        payload.cidr, ports=payload.ports, timeout=payload.timeout, use_icmp=payload.use_icmp
    )
    created = 0
    if payload.auto_create and hosts:
        with Session(engine) as sess:
            existing = {c.target for c in sess.execute(select(MonitoringCheck)).scalars().all()}
            for h in hosts:
                if h["open_ports"]:
                    ctype, target, port = "tcp", h["host"], h["open_ports"][0]
                else:
                    ctype, target, port = "icmp", h["host"], None
                if target in existing:
                    continue
                # Validación defensiva antes de persistir (reusa Fase 1).
                mon_validators.validate_check_target(ctype, target, port)
                sess.add(MonitoringCheck(
                    name=f"auto-{target}", check_type=ctype, target=target, port=port,
                    interval_seconds=60, timeout_seconds=10, enabled=True,
                ))
                existing.add(target)
                created += 1
            if created:
                log_audit(sess, "discovery_auto_create", "monitoring_check",
                          payload.cidr, {"created": created}, user["email"])
            sess.commit()
    return DiscoveryScanResponse(
        cidr=payload.cidr, scanned=0, found=len(hosts), hosts=hosts, created_checks=created
    )


# ============================================================
# --- Inventario unificado (CMDB) ---
# ============================================================

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(user: dict = Depends(get_current_user_from_token)):
    """
    Vista única de toda la infraestructura: servidores con agente, checks
    agentless y guests Proxmox. Es el punto donde convergen el lado "Zabbix"
    (monitoreo) y el lado "Proxmox" (virtualización).
    """
    items: List[dict] = []
    online_window = datetime.utcnow() - timedelta(minutes=10)
    with Session(engine) as sess:
        # 1. Servidores con agente: online si reportaron métricas hace <10 min.
        servers = sess.execute(select(Server)).scalars().all()
        for s in servers:
            last = sess.execute(
                select(Metric.ts).where(Metric.server_id == s.server_id)
                .order_by(Metric.ts.desc()).limit(1)
            ).scalar_one_or_none()
            online = False
            if last is not None:
                lt = last.replace(tzinfo=None) if last.tzinfo else last
                online = lt >= online_window
            items.append({
                "source": "agent", "name": s.server_id, "identifier": s.server_id,
                "kind": "server", "status": "online" if online else "offline",
                "detail": s.group_name, "node": None,
            })

        # 2. Checks agentless.
        for c in sess.execute(select(MonitoringCheck)).scalars().all():
            items.append({
                "source": "agentless", "name": c.name, "identifier": c.target,
                "kind": c.check_type, "status": c.last_status or "unknown",
                "detail": c.last_message, "node": None,
            })

        # 3. Guests Proxmox (VMs/contenedores).
        nodes = {n.id: n.name for n in sess.execute(select(ProxmoxNode)).scalars().all()}
        for g in sess.execute(select(ProxmoxGuest)).scalars().all():
            items.append({
                "source": "proxmox", "name": g.name or f"vmid-{g.vmid}",
                "identifier": str(g.vmid), "kind": g.guest_type, "status": g.status,
                "detail": "BD" if g.is_db else None, "node": nodes.get(g.node_id),
            })
    return items


# ============================================================
# --- Canales de notificación ---
# ============================================================

@app.get("/api/admin/notification-channels", response_model=List[NotificationChannelResponse])
def list_notification_channels(user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        return sess.execute(select(NotificationChannel)).scalars().all()


@app.post("/api/admin/notification-channels", response_model=NotificationChannelResponse)
def create_notification_channel(payload: NotificationChannelCreate, user: dict = Depends(require_admin)):
    notif_channels.validate_channel_target(payload.channel_type, payload.target)
    with Session(engine) as sess:
        channel = NotificationChannel(
            name=payload.name, channel_type=payload.channel_type,
            target_encrypted=encrypt_password(payload.target),
            extra=payload.extra, enabled=payload.enabled,
        )
        sess.add(channel)
        log_audit(sess, "create", "notification_channel", payload.name, {"type": payload.channel_type}, user["email"])
        sess.commit()
        sess.refresh(channel)
        return channel


@app.put("/api/admin/notification-channels/{channel_id}", response_model=NotificationChannelResponse)
def update_notification_channel(channel_id: int, payload: NotificationChannelUpdate, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        channel = sess.get(NotificationChannel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Canal no encontrado")
        data = payload.dict(exclude_unset=True)
        if "target" in data and data["target"]:
            notif_channels.validate_channel_target(channel.channel_type, data["target"])
            channel.target_encrypted = encrypt_password(data.pop("target"))
        else:
            data.pop("target", None)
        for field, value in data.items():
            setattr(channel, field, value)
        sess.commit()
        sess.refresh(channel)
        return channel


@app.delete("/api/admin/notification-channels/{channel_id}")
def delete_notification_channel(channel_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        channel = sess.get(NotificationChannel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Canal no encontrado")
        sess.delete(channel)
        sess.commit()
        return {"status": "deleted"}


@app.post("/api/admin/notification-channels/{channel_id}/test")
def test_notification_channel(channel_id: int, user: dict = Depends(require_admin)):
    with Session(engine) as sess:
        channel = sess.get(NotificationChannel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Canal no encontrado")
        ok, detail = notif_channels.send_to_channel(channel, "🔔 Mensaje de prueba desde UpKeep")
    if not ok:
        raise HTTPException(status_code=502, detail=f"Envío falló: {detail}")
    return {"status": "sent", "detail": detail}


# ============================================================
# --- Mantenimiento / retención ---
# ============================================================

@app.post("/api/admin/maintenance/purge")
def purge_retention(user: dict = Depends(require_admin)):
    deleted = maintenance.purge_old_data()
    with Session(engine) as sess:
        log_audit(sess, "purge", "maintenance", "retention", deleted, user["email"])
        sess.commit()
    return {"status": "ok", "deleted": deleted}


# --- Servir Frontend ---
frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
if not frontend_path.exists():
    # Fallback to local client build
    frontend_path = Path(__file__).resolve().parent.parent.parent / "client" / "dist"

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if not frontend_path.exists():
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        return HTMLResponse("Frontend not found. Please build it.", status_code=404)
    
    # Check if file exists in frontend_path (e.g. assets)
    file_path = frontend_path / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # If not API and not file, serve index.html (SPA)
    if full_path.startswith("api"):
         raise HTTPException(status_code=404, detail="Not Found")
         
    index_file = frontend_path / "index.html"
    if not index_file.exists():
        return HTMLResponse("index.html not found", status_code=404)
        
    return FileResponse(index_file)
