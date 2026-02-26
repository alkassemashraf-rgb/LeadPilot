from datetime import datetime
from typing import List, Optional, Union, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, JSON
from sqlalchemy import Column, UniqueConstraint, Index

# --- Enums ---

class WorkspaceRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"

class FlowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class ExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    WAITING = "waiting"

class WebhookStatus(str, Enum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSED = "processed"
    FAILED = "failed"

class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"

class EmailStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"

class EmailOutboxStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"

class ConversationStatus(str, Enum):
    BOT_ACTIVE = "bot_active"
    HUMAN_TAKEOVER = "human_takeover"
    CLOSED = "closed"

class AgencyStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"

class AgencyRole(str, Enum):
    AGENCY_OWNER = "agency_owner"
    AGENCY_ADMIN = "agency_admin"
    AGENCY_OPERATOR = "agency_operator"
    AGENCY_VIEWER = "agency_viewer"

class OwnerType(str, Enum):
    USER = "user"
    AGENCY = "agency"

# --- Base Models ---

class BaseIDModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceScopedModel(BaseIDModel):
    workspace_id: UUID = Field(index=True, foreign_key="workspace.id")

class OptionalWorkspaceScopedModel(BaseIDModel):
    workspace_id: Optional[UUID] = Field(default=None, index=True, foreign_key="workspace.id")

# --- Identity & Workspaces ---

class WorkspaceMember(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspace.id", primary_key=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER)

class Workspace(BaseIDModel, table=True):
    name: str = Field(index=True)
    subscription_tier: str = Field(default="free")
    
    # Relationships
    members: List["User"] = Relationship(back_populates="workspaces", link_model=WorkspaceMember)

class User(BaseIDModel, table=True):
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = Field(default=None)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    
    # OAuth
    auth_provider: Optional[str] = Field(default="email")
    provider_subject: Optional[str] = Field(default=None, index=True)
    
    # Email Verification (Mission 10.20)
    email_verified_at: Optional[datetime] = Field(default=None)
    email_verification_expires_at: Optional[datetime] = Field(default=None)
    email_verification_sent_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    workspaces: List[Workspace] = Relationship(back_populates="members", link_model=WorkspaceMember)

class Invite(BaseIDModel, table=True):
    workspace_id: UUID = Field(foreign_key="workspace.id")
    email: str
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    accepted_at: Optional[datetime] = None

# --- Email Verification (Mission 10.20) ---

class EmailVerificationToken(BaseIDModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)

# --- Automations ---

class Flow(WorkspaceScopedModel, table=True):
    name: str = Field(index=True)
    description: Optional[str] = None
    status: FlowStatus = Field(default=FlowStatus.DRAFT)
    
    # Relationships
    nodes: List["FlowNode"] = Relationship(back_populates="flow")
    edges: List["FlowEdge"] = Relationship(back_populates="flow")
    versions: List["FlowVersion"] = Relationship(back_populates="flow")

class FlowNode(BaseIDModel, table=True):
    flow_id: UUID = Field(foreign_key="flow.id")
    type: str
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    position_x: float
    position_y: float
    
    flow: "Flow" = Relationship(back_populates="nodes")

class FlowEdge(BaseIDModel, table=True):
    flow_id: UUID = Field(foreign_key="flow.id")
    source_node_id: UUID = Field(foreign_key="flownode.id")
    target_node_id: UUID = Field(foreign_key="flownode.id")
    source_handle: Optional[str] = None
    
    flow: "Flow" = Relationship(back_populates="edges")

class FlowVersion(BaseIDModel, table=True):
    flow_id: UUID = Field(foreign_key="flow.id")
    version_number: int
    definition_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    is_published: bool = Field(default=False)
    
    flow: "Flow" = Relationship(back_populates="versions")

# --- Execution ---

class ExecutionInstance(WorkspaceScopedModel, table=True):
    flow_version_id: UUID = Field(foreign_key="flowversion.id")
    status: ExecutionStatus = Field(default=ExecutionStatus.RUNNING)
    current_node_id: Optional[UUID] = None
    next_run_at: Optional[datetime] = None
    
    # Metadata for execution context
    # Metadata for execution context
    contact_id: Optional[UUID] = Field(default=None, foreign_key="contact.id")
    
    # Mission 7.1: Abort Semantics
    abort_reason: Optional[str] = None
    aborted_at: Optional[datetime] = None

    __table_args__ = (
        Index("idx_exec_stats", "workspace_id", "created_at", "status"),
    )

class ExecutionStepLog(BaseIDModel, table=True):
    execution_instance_id: UUID = Field(foreign_key="executioninstance.id")
    node_id: UUID = Field(foreign_key="flownode.id")
    input_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    output_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

# --- Logs ---

class WebhookEventLog(OptionalWorkspaceScopedModel, table=True):
    __table_args__ = (UniqueConstraint("provider", "provider_event_id"),)
    
    provider: str
    provider_event_id: str
    status: WebhookStatus = Field(default=WebhookStatus.RECEIVED)
    correlation_id: UUID = Field(default_factory=uuid4)
    attempts: int = Field(default=0)
    last_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    payload: Dict[str, Any] = Field(sa_column=Column(JSON))

# --- Prompt Studio ---

class PromptConfig(WorkspaceScopedModel, table=True):
    name: str = Field(default="Default Config", index=True)
    current_version_id: Optional[UUID] = None # Points to the active version
    
    # Relationships
    versions: List["PromptVersion"] = Relationship(back_populates="prompt_config")

class PromptVersion(BaseIDModel, table=True):
    prompt_config_id: UUID = Field(foreign_key="promptconfig.id")
    version_number: int
    
    business_profile_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    system_prompt_text: str
    guardrails_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # New Form-Based Fields (Mission 5.2)
    structured_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    compiled_system_instruction: Optional[str] = None
    
    model: str # e.g., gpt-4-turbo
    temperature: float = Field(default=0.7)
    max_tokens_per_execution: int = Field(default=1000)
    
    prompt_config: PromptConfig = Relationship(back_populates="versions")

# --- CRM ---

class ZohoLeadMapping(WorkspaceScopedModel, table=True):
    module_name: str = Field(default="Leads")
    dedupe_strategy: str = Field(default="EMAIL_OR_PHONE")
    field_mappings: Dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))

    __table_args__ = (UniqueConstraint("workspace_id"),)

class Contact(WorkspaceScopedModel, table=True):
    external_id: Optional[str] = Field(default=None, index=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Mission 8: Zoho Sync
    zoho_lead_id: Optional[str] = Field(default=None, index=True)
    zoho_last_synced_at: Optional[datetime] = None

    __table_args__ = (
        Index("idx_contact_workspace_zoho", "workspace_id", "zoho_lead_id"),
        Index("idx_contact_zoho_stats", "workspace_id", "zoho_last_synced_at"),
        Index("idx_contact_workspace_created", "workspace_id", "created_at"),
    )

class ChannelIdentity(BaseIDModel, table=True):
    contact_id: UUID = Field(foreign_key="contact.id")
    provider: str # whatsapp, meta, etc
    provider_user_id: str # phone number or fb id
    
class Conversation(WorkspaceScopedModel, table=True):
    __table_args__ = (
        Index("idx_conv_workspace_updated", "workspace_id", "updated_at"),
        Index("idx_conv_workspace_contact", "workspace_id", "contact_id"),
    )
    contact_id: UUID = Field(foreign_key="contact.id")
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    status: ConversationStatus = Field(default=ConversationStatus.BOT_ACTIVE, index=True)

class Message(WorkspaceScopedModel, table=True):
    __table_args__ = (
        UniqueConstraint("provider_message_id", name="uq_message_provider_id"),
        Index("idx_msg_poll", "workspace_id", "delivery_status", "created_at"),
        Index("idx_msg_retry", "delivery_status", "last_attempt_at"),
        Index("idx_msg_conv_created", "conversation_id", "created_at"),
        Index("idx_msg_stats", "workspace_id", "created_at", "direction", "delivery_status"),
    )
    conversation_id: UUID = Field(foreign_key="conversation.id")
    direction: str = Field(index=True) # inbound, outbound
    content: str
    platform: str = Field(index=True)
    delivery_status: DeliveryStatus = Field(default=DeliveryStatus.PENDING, index=True)
    
    provider_message_id: Optional[str] = Field(default=None, index=True)
    attempt_count: int = Field(default=0)
    last_attempt_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Mission 6.2: Hardening
    is_outbound_intent: bool = Field(default=True)
    idempotency_hash: Optional[str] = Field(default=None, index=True)
    
    additional_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

# --- Integrations ---

class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class Integration(WorkspaceScopedModel, table=True):
    __table_args__ = (UniqueConstraint("provider", "provider_workspace_id"),)
    
    provider: str = Field(index=True) # zoho, whatsapp, meta
    status: IntegrationStatus = Field(default=IntegrationStatus.DISCONNECTED)
    
    # Encrypted JSON string of tokens, IDs, etc.
    encrypted_config: Optional[str] = None
    
    connected_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Unique identifiers for resolution
    # Standard: 
    # - WhatsApp: phone_number_id
    # - Meta: page_id
    # - Zoho: org_id
    provider_workspace_id: Optional[str] = Field(default=None, index=True)

# --- Knowledge Base ---

class WorkspaceKnowledgeFile(WorkspaceScopedModel, table=True):
    filename: str = Field(index=True)
    mime_type: str
    size_bytes: int
    storage_path: str
    extracted_text: Optional[str] = Field(default=None)
    notes: Optional[str] = None

class PasswordResetToken(BaseIDModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(index=True)
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)

# --- Observability & Admin ---

class SystemModuleConfig(BaseIDModel, table=True):
    module_name: str = Field(unique=True, index=True)
    is_enabled: bool = Field(default=True)
    config_json: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    updated_by_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")

class AdminAuditLog(BaseIDModel, table=True):
    actor_user_id: UUID = Field(foreign_key="user.id", index=True)
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    correlation_id: Optional[UUID] = None

    __table_args__ = (
        Index("idx_audit_actor_created", "actor_user_id", "created_at"),
        Index("idx_audit_entity_created", "entity_type", "entity_id", "created_at"),
        Index("idx_audit_created", "created_at"),
    )

class EmailLog(OptionalWorkspaceScopedModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    email_type: str = Field(index=True)
    recipient: str = Field(index=True)
    subject: str
    status: EmailStatus = Field(default=EmailStatus.PENDING, index=True)
    attempt_count: int = Field(default=0)
    error_message: Optional[str] = None
    provider_message_id: Optional[str] = None
    
    idempotency_key: Optional[str] = Field(default=None, unique=True, index=True)
    sent_at: Optional[datetime] = None
    
    __table_args__ = (
        Index("idx_emaillog_w_created", "workspace_id", "created_at"),
        Index("idx_emaillog_st_created", "status", "created_at"),
    )

class EmailOutbox(BaseIDModel, table=True):
    email_log_id: UUID = Field(foreign_key="emaillog.id", unique=True, index=True)
    email_type: str = Field(index=True)
    payload_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    status: EmailOutboxStatus = Field(default=EmailOutboxStatus.PENDING, index=True)
    attempt_count: int = Field(default=0)
    next_attempt_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    locked_at: Optional[datetime] = None
    last_error: Optional[str] = None

# --- Plans & Entitlements (Mission 14) ---

class Plan(BaseIDModel, table=True):
    name: str = Field(unique=True, index=True)
    display_name: str
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    description: Optional[str] = None

    entitlements: List["PlanEntitlement"] = Relationship(back_populates="plan")

class PlanEntitlement(BaseIDModel, table=True):
    __table_args__ = (UniqueConstraint("plan_id", "module_key"),)

    plan_id: UUID = Field(foreign_key="plan.id", index=True)
    module_key: str = Field(index=True)
    hard_limit: Optional[int] = Field(default=None)

    plan: Plan = Relationship(back_populates="entitlements")

class WorkspacePlan(BaseIDModel, table=True):
    workspace_id: UUID = Field(foreign_key="workspace.id", unique=True, index=True)
    plan_id: UUID = Field(foreign_key="plan.id", index=True)
    assigned_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceEntitlementOverride(BaseIDModel, table=True):
    __table_args__ = (UniqueConstraint("workspace_id", "module_key"),)

    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    module_key: str = Field(index=True)
    hard_limit: Optional[int] = Field(default=None)

class UsageMeter(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("workspace_id", "module_key", "period"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    module_key: str = Field(index=True)
    period: str = Field(index=True)
    counter: int = Field(default=0)

# --- Agency Model (Mission 15) ---

class AgencyAccount(BaseIDModel, table=True):
    name: str = Field(index=True)
    owner_user_id: UUID = Field(foreign_key="user.id", index=True)
    status: AgencyStatus = Field(default=AgencyStatus.ACTIVE)
    plan_id: Optional[UUID] = Field(default=None, foreign_key="plan.id")

class AgencyMember(BaseIDModel, table=True):
    __table_args__ = (UniqueConstraint("agency_id", "user_id"),)

    agency_id: UUID = Field(foreign_key="agencyaccount.id", index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role: AgencyRole = Field(default=AgencyRole.AGENCY_OPERATOR)

class WorkspaceOwnership(BaseIDModel, table=True):
    workspace_id: UUID = Field(foreign_key="workspace.id", unique=True, index=True)
    owner_type: OwnerType = Field(default=OwnerType.USER)
    owner_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    owner_agency_id: Optional[UUID] = Field(default=None, foreign_key="agencyaccount.id", index=True)

# --- Settings Models (Mission 16) ---

class WorkspaceSettings(BaseIDModel, table=True):
    workspace_id: UUID = Field(foreign_key="workspace.id", unique=True, index=True)
    settings_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    version: int = Field(default=1)
    updated_by_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")

class AgencySettings(BaseIDModel, table=True):
    agency_id: UUID = Field(foreign_key="agencyaccount.id", unique=True, index=True)
    settings_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    version: int = Field(default=1)
    updated_by_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")

class SystemSettings(BaseIDModel, table=True):
    singleton_key: str = Field(default="global", unique=True, index=True)
    settings_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    version: int = Field(default=1)
    updated_by_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
