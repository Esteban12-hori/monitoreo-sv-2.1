from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime


class MemorySchema(BaseModel):
    total: float
    used: float
    free: float
    cache: float


class CpuSchema(BaseModel):
    total: float
    per_core: List[float]


class DiskSchema(BaseModel):
    total: float
    used: float
    free: float
    percent: float


class NetworkSchema(BaseModel):
    bytes_sent: float
    bytes_recv: float
    packets_sent: float
    packets_recv: float
    sent_rate: Optional[float] = 0.0
    recv_rate: Optional[float] = 0.0


class DockerContainerSchema(BaseModel):
    name: str
    cpu: Optional[float] = None
    mem: Optional[float] = None


class DockerSchema(BaseModel):
    running_containers: int
    containers: List[DockerContainerSchema] = []

class ServiceSchema(BaseModel):
    port: int
    name: str
    proto: str
    ip: Optional[str] = None

class ProcessSchema(BaseModel):
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str

class MetricsIngestSchema(BaseModel):
    server_id: str
    memory: MemorySchema
    cpu: CpuSchema
    disk: DiskSchema
    network: Optional[NetworkSchema] = None
    uptime: Optional[float] = None
    docker: DockerSchema
    services: Optional[List[ServiceSchema]] = []
    processes: Optional[List[ProcessSchema]] = []
    timestamp: Optional[str] = None



class RegisterServerSchema(BaseModel):
    server_id: str = Field(..., min_length=1)
    token: str = Field(..., min_length=8)


class AlertConfigSchema(BaseModel):
    cpu_total_percent: float
    memory_used_percent: float
    disk_used_percent: float

class LoginSchema(BaseModel):
    email: str
    password: str

class UserCreateSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: Optional[str] = None
    is_admin: bool = False
    receive_alerts: bool = False
    must_change_password: bool = True
    is_blocked: bool = False

class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    is_admin: Optional[bool] = None
    receive_alerts: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)
    is_blocked: Optional[bool] = None

class UserResponseSchema(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_admin: bool
    receive_alerts: bool
    must_change_password: bool
    is_blocked: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ServerAssignmentItem(BaseModel):
    server_id: str
    receive_alerts: bool = True

class ServerAssignmentSchema(BaseModel):
    assignments: List[ServerAssignmentItem]

class UserServerAssignmentResponse(BaseModel):
    server_id: str
    receive_alerts: bool

class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)

class SMTPConfigSchema(BaseModel):
    host: str
    port: int
    username: str
    password: Optional[str] = None # Plain text in request, encrypted in DB
    use_ssl: bool = False
    use_tls: bool = True
    sender_email: EmailStr

class SMTPConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    use_ssl: bool
    use_tls: bool
    sender_email: str
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ServerConfigUpdateSchema(BaseModel):
    report_interval: int = Field(..., ge=0, le=86400) # 0s to 24h


class AlertRecipientSchema(BaseModel):
    id: int
    email: str
    name: Optional[str]
    recipient_type: Optional[str] = "OTROS"
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class AlertRecipientCreateSchema(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    recipient_type: Optional[str] = "OTROS"


class AlertRuleBase(BaseModel):
    alert_type: str
    server_scope: str = Field(..., pattern="^(global|server|group)$")
    target_id: Optional[str] = None
    emails: List[EmailStr]

    # Advanced
    condition_field: Optional[str] = None
    condition_op: Optional[str] = None # gt, lt, eq
    condition_value: Optional[float] = None
    duration_seconds: Optional[int] = 0
    severity: Optional[str] = "warning"

class AlertRuleCreate(AlertRuleBase):
    pass

class AlertRuleResponse(AlertRuleBase):
    id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ServerUpdateGroupSchema(BaseModel):
    group_name: Optional[str]


class ServerThresholdBase(BaseModel):
    cpu_threshold: Optional[float] = Field(None, ge=0.1, le=100.0)
    memory_threshold: Optional[float] = Field(None, ge=0.1, le=100.0)
    disk_threshold: Optional[float] = Field(None, ge=0.1, le=100.0)

class ServerThresholdUpdate(ServerThresholdBase):
    pass

class ServerThresholdImport(ServerThresholdBase):
    server_id: str

class ServerThresholdResponse(ServerThresholdBase):
    server_id: str
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    action: str
    target_type: str
    target_id: Optional[str]
    changes: Optional[str]
    user_email: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class RemoteActionCreate(BaseModel):
    port: int
    proto: str
    ip: Optional[str] = None
    service: Optional[str] = None


class RemoteActionResponse(BaseModel):
    id: int
    server_id: str
    action_type: str
    payload: str
    status: str
    created_at: Optional[datetime]
    executed_at: Optional[datetime]
    requested_by: str

    class Config:
        from_attributes = True
