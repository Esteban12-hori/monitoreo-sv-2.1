import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import os
import uuid
import unicodedata

from fastapi import FastAPI, HTTPException, Header, Depends, status, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import create_engine, select, delete, text
from sqlalchemy.orm import Session, defer
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import DB_PATH, DEFAULT_ALERTS, ALLOWED_ORIGINS, DASHBOARD_TOKEN, CACHE_MAX_ITEMS, BASE_DIR
from .models import Base, Server, Metric, AlertConfig, User, UserSession, AlertRecipient, AlertRule, ServerThreshold, AuditLog, UserServerLink, SMTPConfig, RemoteAction, UserGroup, NotificationRule, UserServerThreshold
from .schemas import (
    MetricsIngestSchema, RegisterServerSchema, AlertConfigSchema, LoginSchema,
    UserCreateSchema, UserResponseSchema, ChangePasswordSchema,
    ServerConfigUpdateSchema, AlertRecipientSchema, AlertRecipientCreateSchema,
    ServerAssignmentSchema, AlertRuleCreate, AlertRuleResponse, ServerUpdateGroupSchema,
    ServerThresholdResponse, ServerThresholdUpdate, AuditLogResponse, ServerThresholdImport,
    UserUpdateSchema, UserServerAssignmentResponse, SMTPConfigSchema, SMTPConfigResponse,
    UserGroupCreate, UserGroupResponse, UserGroupUpdate, NotificationRuleCreate, NotificationRuleResponse,
    AlertPreviewRequest, AlertPreviewResponse, UserServerThresholdResponse, UserServerThresholdUpdate,
    ServerSubscriptionUpdate
)
from .email_utils import send_alert_email
from .alert_logic import get_alert_recipients, check_advanced_rules, explain_alert_decision
from .security import encrypt_password, decrypt_password
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
    allowed_hosts=["localhost", "127.0.0.1", "::1", "*"]
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
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
            
            # Update cache immediately
            _threshold_cache[item.server_id] = {
                "cpu": t.cpu_threshold,
                "memory": t.memory_threshold,
                "disk": t.disk_threshold
            }
            count += 1
        
        log_audit(sess, "import", "threshold", "bulk", {"count": count}, user["email"])
        sess.commit()
        return {"status": "imported", "count": count}

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
            UserServerThreshold.user_id == user["id"],
            UserServerThreshold.server_id == server_id
        )).scalar_one_or_none()
        
        if not ut:
            # Return empty/default structure if not found, with dummy id
            return UserServerThresholdResponse(id=0, user_id=user["id"], server_id=server_id)
        return ut

@app.post("/api/user/thresholds", response_model=UserServerThresholdResponse)
def set_user_server_threshold(payload: UserServerThresholdUpdate, user: dict = Depends(get_current_user_from_token)):
    with Session(engine) as sess:
        ut = sess.execute(select(UserServerThreshold).where(
            UserServerThreshold.user_id == user["id"],
            UserServerThreshold.server_id == payload.server_id
        )).scalar_one_or_none()
        
        if not ut:
            ut = UserServerThreshold(
                user_id=user["id"],
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
