
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, backref
from sqlalchemy.sql import func

Base = declarative_base()

# Tabla de asociación para User <-> Server (Modelo explícito para campos extra)
class UserServerLink(Base):
    __tablename__ = 'user_server_link'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    server_id = Column(Integer, ForeignKey('servers.id'), primary_key=True)
    receive_alerts = Column(Boolean, default=True) # Controla si recibe alertas de este servidor específico

    # Relationships
    user = relationship("User", back_populates="server_links")
    server = relationship("Server", back_populates="user_links")


class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True)
    server_id = Column(String(255), unique=True, index=True, nullable=False)
    token = Column(String(255), nullable=False)
    report_interval = Column(Integer, default=2400) # Segundos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group_name = Column(String(255), nullable=True, index=True) # Nuevo campo
    webhook_enabled = Column(Boolean, default=False) # Habilita recepción de DataMonitoring

    # Relación a través de UserServerLink
    user_links = relationship("UserServerLink", back_populates="server", cascade="all, delete-orphan")
    # Helper para obtener usuarios directamente (read-only recomendado para evitar conflictos)
    assigned_users = relationship("User", secondary="user_server_link", viewonly=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False) # 'cpu', 'memory', 'disk', 'offline'
    server_scope = Column(String(20), nullable=False) # 'global', 'server', 'group'
    target_id = Column(String(255), nullable=True) # server_id o group_name
    emails = Column(Text, nullable=False) # Lista de emails en JSON (e.g. ["a@b.com", "c@d.com"])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Advanced Rules
    condition_field = Column(String(100), nullable=True) # e.g. 'cpu.total'
    condition_op = Column(String(10), nullable=True) # 'gt', 'lt', 'eq'
    condition_value = Column(Float, nullable=True)
    duration_seconds = Column(Integer, default=0)
    severity = Column(String(20), default="warning")


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    server_id = Column(String(255), index=True, nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    mem_total = Column(Float)
    mem_used = Column(Float)
    mem_free = Column(Float)
    mem_cache = Column(Float)

    cpu_total = Column(Float)
    cpu_per_core = Column(Text)  # JSON serializado

    disk_total = Column(Float)
    disk_used = Column(Float)
    disk_free = Column(Float)
    disk_percent = Column(Float)

    net_bytes_sent = Column(Float, default=0.0)
    net_bytes_recv = Column(Float, default=0.0)
    net_sent_rate = Column(Float, default=0.0)
    net_recv_rate = Column(Float, default=0.0)
    uptime_seconds = Column(Float, default=0.0)

    docker_running = Column(Integer)
    docker_containers = Column(Text)  # JSON serializado
    
    services = Column(Text) # JSON serializado (Auto-discovery)
    processes = Column(Text) # JSON serializado (Top processes)


class AlertConfig(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    cpu_total_percent = Column(Float)
    memory_used_percent = Column(Float)
    disk_used_percent = Column(Float)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertRecipient(Base):
    __tablename__ = "alert_recipients"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    recipient_type = Column(String(50), default="OTROS") # VS, SV, OTROS
    phone_number = Column(String(50), nullable=True) # WhatsApp/SMS
    webhook_url = Column(String(500), nullable=True) # Custom Integration
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserServerThreshold(Base):
    __tablename__ = "user_server_thresholds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    server_id = Column(String(255), nullable=False) # Not ForeignKey to allow detached configs
    
    cpu_limit = Column(Float, nullable=True)
    mem_limit = Column(Float, nullable=True)
    disk_limit = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# --- User Management Extensions (Groups & Rules) ---

user_group_association = Table('user_group_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('group_id', Integer, ForeignKey('user_groups.id'))
)

class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    users = relationship("User", secondary=user_group_association, back_populates="groups")


class NotificationRule(Base):
    __tablename__ = 'notification_rules'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    group_id = Column(Integer, ForeignKey('user_groups.id'), nullable=True)
    server_id = Column(String(255), nullable=True) # If Null -> Global/All Servers
    action = Column(String(20), nullable=False, default='ALLOW') # ALLOW / BLOCK
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="notification_rules")
    group = relationship("UserGroup", backref="notification_rules")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    receive_alerts = Column(Boolean, default=False) # Master switch
    must_change_password = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    phone_number = Column(String(50), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación Many-to-Many con Server
    server_links = relationship("UserServerLink", back_populates="user", cascade="all, delete-orphan")
    servers = relationship("Server", secondary="user_server_link", viewonly=True)
    
    # Groups
    groups = relationship("UserGroup", secondary=user_group_association, back_populates="users")


class SMTPConfig(Base):
    __tablename__ = "smtp_config"
    id = Column(Integer, primary_key=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    password_encrypted = Column(String(255), nullable=False)
    use_ssl = Column(Boolean, default=False)
    use_tls = Column(Boolean, default=True)
    sender_email = Column(String(255), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class UserSession(Base):
    __tablename__ = "sessions"
    token = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")


class ServerThreshold(Base):
    __tablename__ = "server_thresholds"
    id = Column(Integer, primary_key=True)
    server_id = Column(String(255), ForeignKey('servers.server_id'), unique=True, nullable=False)
    
    cpu_threshold = Column(Float, nullable=True)     # %
    memory_threshold = Column(Float, nullable=True)  # %
    disk_threshold = Column(Float, nullable=True)    # %


class RemoteAction(Base):
    __tablename__ = "remote_actions"
    id = Column(Integer, primary_key=True)
    server_id = Column(String(255), ForeignKey('servers.server_id'), index=True, nullable=False)
    action_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
    requested_by = Column(String(255), nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to Server
    server = relationship("Server", backref=backref("threshold", uselist=False, cascade="all, delete-orphan"))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String(255), nullable=False)
    target_type = Column(String(50), nullable=False) # e.g. 'threshold', 'user'
    target_id = Column(String(255), nullable=True)
    changes = Column(Text, nullable=True) # JSON details
    user_email = Column(String(255), nullable=True) # Who did it
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class DataMonitoring(Base):
    __tablename__ = "data_monitoring"
    id = Column(Integer, primary_key=True)
    server_id = Column(String(255), index=True, nullable=False) # No ForeignKey to allow fast inserts, validated in logic
    
    app = Column(String(100), nullable=False)
    cash_register_number = Column(Integer, nullable=True)
    user_name = Column(String(255), nullable=True)
    flow = Column(String(255), nullable=True)
    patent = Column(String(50), nullable=True)
    vehicle_type = Column(String(100), nullable=True)
    product = Column(String(255), nullable=True)
    entity_id = Column(String(255), nullable=True)
    working_day = Column(String(255), nullable=True)
    
    # Este es el 'createdAt' del payload (cuando ocurrió el evento en el cliente)
    client_created_at = Column(DateTime(timezone=True), nullable=True)
    
    # Este es el 'createdAt' de inserción en DB
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Gestión Proxmox (SSH + WireGuard) ---

class ProxmoxNode(Base):
    """Nodo Proxmox gestionado vía SSH (sin API HTTP)."""
    __tablename__ = "proxmox_nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    hostname = Column(String(255), nullable=False)        # IP o FQDN para SSH
    ssh_port = Column(Integer, default=22, nullable=False)
    ssh_user = Column(String(255), default="root", nullable=False)
    auth_type = Column(String(20), default="password", nullable=False)  # 'password' | 'key'
    secret_encrypted = Column(Text, nullable=False)       # contraseña o clave privada (cifrada Fernet)
    host_key_fingerprint = Column(String(255), nullable=True)  # TOFU: huella de la host key
    use_sudo = Column(Boolean, default=False)             # anteponer 'sudo' a los comandos
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guests = relationship("ProxmoxGuest", back_populates="node", cascade="all, delete-orphan")


class ProxmoxGuest(Base):
    """Inventario cacheado de VMs (qemu) y contenedores (lxc) de un nodo."""
    __tablename__ = "proxmox_guests"
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("proxmox_nodes.id"), nullable=False, index=True)
    vmid = Column(Integer, nullable=False)
    guest_type = Column(String(10), nullable=False)        # 'qemu' | 'lxc'
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    is_db = Column(Boolean, default=False)                 # marcado por autodetección de BD
    linked_server_id = Column(String(255), nullable=True)  # server_id monitoreado asociado
    last_synced = Column(DateTime(timezone=True), nullable=True)

    node = relationship("ProxmoxNode", back_populates="guests")


class BackupSchedule(Base):
    """Programación de backups (vzdump) gestionada por APScheduler."""
    __tablename__ = "backup_schedules"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    node_id = Column(Integer, ForeignKey("proxmox_nodes.id"), nullable=True)  # None = todos los nodos
    cron_expr = Column(String(100), nullable=False)        # ej. "0 3 * * *"
    storage = Column(String(64), nullable=False)
    mode = Column(String(20), default="snapshot")          # 'snapshot' | 'suspend' | 'stop'
    keep_last = Column(Integer, default=3)
    only_db = Column(Boolean, default=True)                # solo guests detectados como BD
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BackupJob(Base):
    """Historial de ejecuciones de backup."""
    __tablename__ = "backup_jobs"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("backup_schedules.id"), nullable=True)
    node_id = Column(Integer, nullable=True)
    vmid = Column(Integer, nullable=True)
    storage = Column(String(64), nullable=True)
    status = Column(String(20), default="running")         # 'running' | 'ok' | 'error'
    output_log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class NodeLink(Base):
    """Túnel WireGuard cifrado entre dos nodos para migración segura."""
    __tablename__ = "node_links"
    id = Column(Integer, primary_key=True)
    source_node_id = Column(Integer, ForeignKey("proxmox_nodes.id"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("proxmox_nodes.id"), nullable=False)
    status = Column(String(20), default="down")            # 'down' | 'up' | 'error'
    wg_interface = Column(String(32), default="wg-mig0")
    listen_port = Column(Integer, default=51830)
    source_wg_pubkey = Column(String(255), nullable=True)
    target_wg_pubkey = Column(String(255), nullable=True)
    source_wg_privkey_encrypted = Column(Text, nullable=True)
    target_wg_privkey_encrypted = Column(Text, nullable=True)
    source_tunnel_ip = Column(String(64), nullable=True)   # ej. 10.99.99.1
    target_tunnel_ip = Column(String(64), nullable=True)   # ej. 10.99.99.2
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SnapshotRecord(Base):
    """Auditoría de snapshots creados desde la aplicación."""
    __tablename__ = "snapshot_records"
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, nullable=False)
    vmid = Column(Integer, nullable=False)
    name = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

