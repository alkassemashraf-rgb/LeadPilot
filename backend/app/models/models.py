from datetime import datetime
from typing import List, Optional, Dict, Any
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
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

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
    # Points to the active published FlowVersion; FK constraint added by Alembic migration
    published_version_id: Optional[UUID] = Field(default=None, index=True)
    # Template source tracking (Mission 32) — not FK to avoid cascade issues
    source_template_id: Optional[UUID] = Field(default=None, index=True)
    source_template_version_id: Optional[UUID] = Field(default=None, index=True)

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
    node_id: Optional[UUID] = Field(default=None, foreign_key="flownode.id")
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

    # Mission M-B: Multi-agent qualification
    qualification_status: Optional[str] = Field(default=None)
    # values: None | "in_progress" | "qualified" | "disqualified"
    intent: Optional[str] = Field(default=None)
    # values: None | "qualification" | "support" | "purchase" | "complaint"

    __table_args__ = (
        Index("idx_contact_workspace_zoho", "workspace_id", "zoho_lead_id"),
        Index("idx_contact_zoho_stats", "workspace_id", "zoho_last_synced_at"),
        Index("idx_contact_workspace_created", "workspace_id", "created_at"),
    )

class ChannelIdentity(BaseIDModel, table=True):
    contact_id: UUID = Field(foreign_key="contact.id")
    provider: str # whatsapp, meta, etc
    provider_user_id: str # phone number or fb id
    channel: Optional[str] = Field(default=None) # instagram, messenger (sub-channel of meta)
    
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
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    last_error: Optional[str] = None
    failure_code: Optional[str] = None

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
    sha256_hash: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="READY")  # READY | FAILED


class KnowledgeChunk(SQLModel, table=True):
    """Individual text chunk from a knowledge file for retrieval."""
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workspace_id: UUID = Field(index=True, foreign_key="workspace.id")
    knowledge_file_id: UUID = Field(index=True, foreign_key="workspaceknowledgefile.id")
    chunk_index: int = Field(default=0)
    content_text: str

    __table_args__ = (
        Index("idx_kc_ws_file", "workspace_id", "knowledge_file_id"),
    )


class QualificationConfig(WorkspaceScopedModel, table=True):
    """Workspace-scoped lead qualification configuration."""
    version: int = Field(default=1)
    qualification_questions: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    qualification_statuses: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )


class QualificationCriterion(WorkspaceScopedModel, table=True):
    """Dynamic lead qualification criterion — stored as rows, not JSON."""
    code: str = Field(index=True)
    label: str
    description: Optional[str] = None
    criterion_type: str = Field(default="boolean")  # boolean | enum | text | score
    enum_values: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    weight: Optional[int] = None
    sort_order: int = Field(default=0)
    is_enabled: bool = Field(default=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_qualcriterion_ws_code"),
    )


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
    actor_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    correlation_id: Optional[UUID] = None
    # Mission 17 — Enterprise Audit fields
    actor_type: Optional[str] = Field(default=None, index=True)
    agency_id: Optional[UUID] = Field(default=None, index=True)
    outcome: Optional[str] = Field(default=None, index=True)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    request_path: Optional[str] = Field(default=None)
    request_method: Optional[str] = Field(default=None)
    error_code: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    __table_args__ = (
        Index("idx_audit_actor_created", "actor_user_id", "created_at"),
        Index("idx_audit_entity_created", "entity_type", "entity_id", "created_at"),
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_agency_created", "agency_id", "created_at"),
        Index("idx_audit_outcome", "outcome", "created_at"),
        Index("idx_audit_actor_type", "actor_type", "created_at"),
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

# --- Runtime Event Trail (Mission 18) ---

class RuntimeEventLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: Optional[UUID] = Field(default=None, index=True)
    event_type: str = Field(index=True)
    source: str = Field(index=True)
    correlation_id: Optional[str] = Field(default=None, index=True)
    related_ids: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    actor_user_id: Optional[UUID] = Field(default=None)
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    outcome: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_rte_ws_created", "workspace_id", "created_at"),
        Index("idx_rte_correlation", "correlation_id"),
        Index("idx_rte_type_created", "event_type", "created_at"),
        Index("idx_rte_source_created", "source", "created_at"),
    )

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

class PlanOverride(BaseIDModel, table=True):
    """Time-bound plan override for a workspace (Mission 34). Supersedes WorkspacePlan during active window."""
    __table_args__ = (
        Index("idx_plan_override_ws_status", "workspace_id", "status"),
        Index("idx_plan_override_ends_at", "ends_at"),
    )

    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    plan_id: UUID = Field(foreign_key="plan.id", index=True)
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    ends_at: datetime
    reason: Optional[str] = None
    status: str = Field(default="active")  # "active" | "revoked" | "expired"
    revoked_at: Optional[datetime] = None
    revoked_by_admin_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    created_by_admin_id: UUID = Field(foreign_key="user.id")

class WorkspaceEntitlementOverride(BaseIDModel, table=True):
    __table_args__ = (UniqueConstraint("workspace_id", "module_key"),)

    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    module_key: str = Field(index=True)
    hard_limit: Optional[int] = Field(default=None)
    enabled: Optional[bool] = Field(default=None)

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


# --- Builder v2: Draft Storage (Mission 27) ---

class FlowDraft(BaseIDModel, table=True):
    """Editable builder graph for a flow. One draft per flow. Not used by runtime."""
    workspace_id: UUID = Field(index=True)
    flow_id: UUID = Field(foreign_key="flow.id")
    builder_graph_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    updated_by_user_id: Optional[UUID] = Field(default=None)
    last_validation_errors: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    __table_args__ = (
        UniqueConstraint("flow_id", name="uq_flowdraft_flow_id"),
        Index("idx_flowdraft_ws_updated", "workspace_id", "updated_at"),
    )


# --- Template Catalog (Mission 27) ---

class AutomationTemplate(BaseIDModel, table=True):
    """Global, admin-managed automation template. Workspace users can browse and clone."""
    slug: str = Field(unique=True, index=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    category: str = Field(default="general", index=True)
    industry_tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    platforms: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    required_integrations: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_featured: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    created_by_admin_id: Optional[UUID] = Field(default=None)

    __table_args__ = (
        Index("idx_template_active_featured", "is_active", "is_featured"),
    )


class AutomationTemplateVersion(BaseIDModel, table=True):
    """Immutable snapshot of a template version. Published versions are cloneable."""
    template_id: UUID = Field(foreign_key="automationtemplate.id", index=True)
    version_number: int
    builder_graph_json: Dict[str, Any] = Field(sa_column=Column(JSON))
    translated_definition_json: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    changelog: Optional[str] = None
    created_by_admin_id: Optional[UUID] = Field(default=None)
    is_published: bool = Field(default=False, index=True)
    published_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        Index("idx_atv_template_ver", "template_id", "version_number"),
        Index("idx_atv_template_published", "template_id", "is_published"),
    )


# --- Template Variables + Analytics (Mission 32) ---

class TemplateVariable(BaseIDModel, table=True):
    """Variable placeholder defined per template version. Used during clone."""
    template_version_id: UUID = Field(foreign_key="automationtemplateversion.id", index=True)
    key: str
    label: str
    description: Optional[str] = None
    var_type: str = Field(default="text")  # text | textarea | number | phone | url
    required: bool = Field(default=True)
    default_value: Optional[str] = None
    sort_order: int = Field(default=0)

    __table_args__ = (
        UniqueConstraint("template_version_id", "key", name="uq_tmplvar_version_key"),
        Index("idx_tmplvar_version", "template_version_id", "sort_order"),
    )


class FlowTemplateVariableValue(BaseIDModel, table=True):
    """Stores the variable values supplied when a flow was cloned from a template."""
    flow_id: UUID = Field(foreign_key="flow.id", index=True)
    template_variable_id: UUID = Field(foreign_key="templatevariable.id", index=True)
    value: Optional[str] = None

    __table_args__ = (
        UniqueConstraint("flow_id", "template_variable_id", name="uq_ftvv_flow_var"),
    )


class TemplateUsageStat(BaseIDModel, table=True):
    """Aggregate usage statistics for a template. One row per template."""
    template_id: UUID = Field(foreign_key="automationtemplate.id", unique=True, index=True)
    clone_count: int = Field(default=0)
    publish_count: int = Field(default=0)
    active_flows_count: int = Field(default=0)


# --- OAuth Framework (Mission 37) ---

class OAuthConnectionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"


class OAuthProvider(BaseIDModel, table=True):
    """Registry of supported OAuth providers. Seeded at startup."""
    __table_args__ = (
        Index("idx_oauth_provider_code", "provider_code"),
    )

    provider_code: str = Field(unique=True, index=True)  # facebook, tiktok, hubspot, salesforce
    display_name: str
    auth_url: str
    token_url: str
    scopes_json: Optional[str] = Field(default=None)  # JSON array string
    is_active: bool = Field(default=True)
    supports_refresh_token: bool = Field(default=False)


class OAuthConnection(BaseIDModel, table=True):
    """Workspace-scoped (or user-scoped) OAuth token storage. Tokens encrypted at rest."""
    __table_args__ = (
        Index("idx_oauth_conn_workspace_provider", "workspace_id", "provider_code"),
        Index("idx_oauth_conn_user_provider", "user_id", "provider_code"),
    )

    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id", index=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    provider_code: str = Field(index=True)
    external_account_id: Optional[str] = Field(default=None)
    external_account_name: Optional[str] = Field(default=None)
    access_token_encrypted: str  # Fernet-encrypted, NEVER expose plaintext
    refresh_token_encrypted: Optional[str] = Field(default=None)  # Fernet-encrypted
    expires_at: Optional[datetime] = Field(default=None)
    token_type: Optional[str] = Field(default=None)
    scopes_json: Optional[str] = Field(default=None)
    metadata_json: Optional[str] = Field(default=None)
    status: OAuthConnectionStatus = Field(default=OAuthConnectionStatus.ACTIVE)


class OAuthState(SQLModel, table=True):
    """Temporary CSRF-safe state storage for OAuth flows. Expires in 10 minutes."""
    __table_args__ = (
        Index("idx_oauth_state_token", "state_token"),
        Index("idx_oauth_state_expires", "expires_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    provider_code: str = Field(index=True)
    state_token: str = Field(unique=True, index=True)
    workspace_id: Optional[UUID] = Field(default=None)
    user_id: Optional[UUID] = Field(default=None)
    redirect_after: Optional[str] = Field(default=None)
    purpose: Optional[str] = Field(default="integration")  # "integration" | "social_auth"
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserIdentity(BaseIDModel, table=True):
    """Stores social login identities (Facebook, TikTok, etc.) linked to a User.
    Supports multiple providers per user. Created when a user signs in via social OAuth."""
    __tablename__ = "user_identity"
    __table_args__ = (
        UniqueConstraint("provider_code", "provider_user_id", name="uq_user_identity_provider"),
        Index("idx_user_identity_user_id", "user_id"),
        Index("idx_user_identity_provider", "provider_code", "provider_user_id"),
    )

    user_id: UUID = Field(foreign_key="user.id", index=True)
    provider_code: str = Field(index=True)          # "facebook", "tiktok"
    provider_user_id: str                            # Unique ID from the provider
    provider_email: Optional[str] = Field(default=None)
    provider_name: Optional[str] = Field(default=None)
    provider_avatar_url: Optional[str] = Field(default=None)
    metadata_json: Optional[str] = Field(default=None)  # e.g. {"social_email_missing": true}


class AgentSession(SQLModel, table=True):
    """
    Persistent ADK session storage. One row per Conversation.
    session_id == str(conversation.id) — they share the same UUID.
    """
    __tablename__ = "agent_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(index=True, foreign_key="conversation.id")
    app_name: str = Field(default="leadpilot")
    user_id: str  # str(contact.id)

    # ADK session state — qualification progress, intent, CRM sync status, etc.
    state: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Compressed ADK event history (last 50 events)
    events: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    is_archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
