from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreateSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: Optional[str] = None
    is_admin: bool = False
    receive_alerts: bool = False
    must_change_password: bool = True
    is_blocked: bool = False
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None

class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    is_admin: Optional[bool] = None
    receive_alerts: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)
    is_blocked: Optional[bool] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None

class UserResponseSchema(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_admin: bool
    receive_alerts: bool
    must_change_password: bool
    is_blocked: bool
    phone_number: Optional[str]
    webhook_url: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class DataMonitoringSchema(BaseModel):
    app: str
    cashRegisterNumber: Optional[int] = None
    userName: str
    flow: str
    patent: Optional[str] = None
    vehicleType: Optional[str] = None
    product: Optional[str] = None
    createdAt: str # String ISO from client
    entityId: str
    workingDay: str

class DataMonitoringResponse(BaseModel):
    id: int
    server_id: str
    app: str
    cash_register_number: Optional[int]
    user_name: Optional[str]
    flow: Optional[str]
    patent: Optional[str]
    vehicle_type: Optional[str]
    product: Optional[str]
    entity_id: Optional[str]
    working_day: Optional[str]
    client_created_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ServerWebhookConfigUpdate(BaseModel):
    webhook_enabled: bool


# --- Missing Schemas Added ---

class RegisterServerSchema(BaseModel):
    server_id: str
    token: str

class AlertConfigSchema(BaseModel):
    cpu_total_percent: float = Field(..., ge=0.0, le=100.0)
    memory_used_percent: float = Field(..., ge=0.0, le=100.0)
    disk_used_percent: float = Field(..., ge=0.0, le=100.0)

class LoginSchema(BaseModel):
    email: str
    password: str

class ChangePasswordSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class ServerConfigUpdateSchema(BaseModel):
    report_interval: int = Field(..., ge=0)

class AlertRecipientCreateSchema(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    recipient_type: Optional[str] = "OTROS"
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None

class AlertRecipientSchema(BaseModel):
    id: int
    email: str
    name: Optional[str]
    recipient_type: str
    phone_number: Optional[str]
    webhook_url: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Metrics Schemas ---

class MetricsCPU(BaseModel):
    total: float
    per_core: List[float]

class MetricsMemory(BaseModel):
    total: float
    used: float
    free: float
    cache: float

class MetricsDisk(BaseModel):
    total: float
    used: float
    free: float
    percent: float

class MetricsNetwork(BaseModel):
    bytes_sent: float
    bytes_recv: float
    packets_sent: Optional[float] = None
    packets_recv: Optional[float] = None
    sent_rate: Optional[float] = None
    recv_rate: Optional[float] = None

    class Config:
        extra = "allow"

class MetricsContainer(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    image: Optional[str] = None
    status: Optional[str] = None
    created: Optional[str] = None
    ports: Optional[str] = None
    state: Optional[str] = None
    
    class Config:
        extra = "allow"

class MetricsDocker(BaseModel):
    running_containers: int
    containers: List[MetricsContainer] = []

class MetricsService(BaseModel):
    name: str
    status: Optional[str] = "active"
    
    class Config:
        extra = "allow"

class MetricsProcess(BaseModel):
    pid: int
    name: str
    username: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    
    class Config:
        extra = "allow"

class MetricsIngestSchema(BaseModel):
    server_id: str
    cpu: MetricsCPU
    memory: MetricsMemory
    disk: MetricsDisk
    network: Optional[MetricsNetwork] = None
    uptime: Optional[float] = None
    docker: MetricsDocker
    services: Optional[List[MetricsService]] = None
    processes: Optional[List[MetricsProcess]] = None

class ServerAssignmentItem(BaseModel):
    server_id: str
    receive_alerts: bool = True

class ServerAssignmentSchema(BaseModel):
    assignments: List[ServerAssignmentItem]

class UserServerAssignmentResponse(BaseModel):
    server_id: str
    receive_alerts: bool
    
    class Config:
        from_attributes = True



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

class ServerThresholdResponse(ServerThresholdBase):
    id: int
    server_id: str
    
    class Config:
        from_attributes = True

class ServerThresholdUpdate(ServerThresholdBase):
    pass


class UserServerThresholdBase(BaseModel):
    server_id: str
    cpu_limit: Optional[float] = Field(None, ge=0.1, le=100.0)
    mem_limit: Optional[float] = Field(None, ge=0.1, le=100.0)
    disk_limit: Optional[float] = Field(None, ge=0.1, le=100.0)

class UserServerThresholdUpdate(UserServerThresholdBase):
    pass

class ServerSubscriptionUpdate(BaseModel):
    receive_alerts: bool

class UserServerThresholdResponse(UserServerThresholdBase):
    id: int
    user_id: int
    receive_alerts: bool = True # Added field
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ServerThresholdImport(ServerThresholdBase):
    server_id: str

class UserGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class UserGroupCreate(UserGroupBase):
    user_ids: List[int] = []

class UserGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_ids: Optional[List[int]] = None

class UserGroupResponse(UserGroupBase):
    id: int
    created_at: Optional[datetime]
    user_count: int = 0
    user_ids: List[int] = []

    class Config:
        from_attributes = True

class NotificationRuleBase(BaseModel):
    user_id: Optional[int] = None
    group_id: Optional[int] = None
    server_id: Optional[str] = None # None means Global
    action: str = Field(..., pattern="^(ALLOW|BLOCK)$")

class NotificationRuleCreate(NotificationRuleBase):
    pass

# --- Alert Preview Schemas ---

class AlertPreviewRequest(BaseModel):
    user_id: int
    server_id: str

class AlertPreviewResponse(BaseModel):
    decision: bool
    reason: str
    trace: List[str]

class NotificationRuleResponse(NotificationRuleBase):
    id: int
    created_at: Optional[datetime]

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

class SMTPConfigSchema(BaseModel):
    host: str
    port: int
    username: str
    password: Optional[str] = None
    use_ssl: bool
    use_tls: bool
    sender_email: str

class SMTPConfigResponse(SMTPConfigSchema):
    id: int
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
