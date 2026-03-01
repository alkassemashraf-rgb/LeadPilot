"""
Catalog Registry — Mission 19
Single source of truth for all enumerated catalogs.
The catalog router reads from here (for enums/constants)
and from DB tables (for plans/modules).
Backend validation logic also imports from here.
"""
from typing import Any, Dict, List


# ── Integration Providers ────────────────────────────────────────────

INTEGRATION_PROVIDERS: List[Dict[str, Any]] = [
    {
        "key": "zoho",
        "label": "Zoho CRM",
        "description": "Sync leads and contacts directly into your Zoho CRM pipeline.",
        "icon_hint": "zoho",
        "fields": [
            {"name": "org_id", "label": "Organization ID", "type": "text"},
            {"name": "access_token", "label": "Access Token", "type": "password"},
        ],
    },
    {
        "key": "whatsapp",
        "label": "WhatsApp Cloud API",
        "description": "Official API for professional messaging and automation.",
        "icon_hint": "whatsapp",
        "fields": [
            {"name": "phone_number_id", "label": "Phone Number ID", "type": "text"},
            {"name": "access_token", "label": "Access Token", "type": "password"},
        ],
    },
    {
        "key": "meta",
        "label": "Meta (Instagram/Messenger)",
        "description": "Automate responses for Instagram DM and Facebook Messenger.",
        "icon_hint": "meta",
        "fields": [
            {"name": "page_id", "label": "Page ID", "type": "text"},
            {"name": "access_token", "label": "Access Token", "type": "password"},
        ],
    },
]

VALID_PROVIDERS = {p["key"] for p in INTEGRATION_PROVIDERS}


# ── Automation Node Types ────────────────────────────────────────────

AUTOMATION_NODE_TYPES: List[Dict[str, Any]] = [
    {
        "key": "AI_REPLY",
        "label": "AI Reply",
        "description": "Generate AI-powered response using workspace prompt config.",
        "icon_hint": "bot",
        "runtime_supported": True,
    },
    {
        "key": "SEND_MESSAGE",
        "label": "Send Message",
        "description": "Send a message via the connected platform.",
        "icon_hint": "send",
        "runtime_supported": True,
    },
    {
        "key": "HUMAN_HANDOVER",
        "label": "Human Handover",
        "description": "Transfer conversation to a human agent.",
        "icon_hint": "user",
        "runtime_supported": True,
    },
    {
        "key": "TAG_CONTACT",
        "label": "Tag Contact",
        "description": "Apply a tag to the contact for segmentation.",
        "icon_hint": "tag",
        "runtime_supported": True,
    },
    {
        "key": "ZOHO_UPSERT_LEAD",
        "label": "Zoho: Upsert Lead",
        "description": "Sync contact as a lead in Zoho CRM.",
        "icon_hint": "database",
        "runtime_supported": True,
        "required_module": "zoho_sync",
    },
    {
        "key": "CONDITION",
        "label": "Condition (Branch)",
        "description": "Branch the flow based on a condition. (Coming soon — cannot publish yet)",
        "icon_hint": "git-branch",
        "runtime_supported": False,
    },
    {
        "key": "WAIT_DELAY",
        "label": "Wait / Delay",
        "description": "Pause the flow for a set duration. (Coming soon — cannot publish yet)",
        "icon_hint": "clock",
        "runtime_supported": False,
    },
]

# Node types supported by the runtime engine (subset of builder palette)
VALID_NODE_TYPES = {n["key"] for n in AUTOMATION_NODE_TYPES if n.get("runtime_supported", True)}


# ── Automation Trigger Types ─────────────────────────────────────────

AUTOMATION_TRIGGER_TYPES: List[Dict[str, Any]] = [
    {
        "key": "MESSAGE_INBOUND",
        "label": "Inbound Message",
        "description": "Triggered when a new message is received.",
        "icon_hint": "message",
    },
    {
        "key": "LEAD_AD_SUBMIT",
        "label": "Lead Ad Submission",
        "description": "Triggered when a Meta Lead Ad form is submitted.",
        "icon_hint": "zap",
    },
]

VALID_TRIGGER_TYPES = {t["key"] for t in AUTOMATION_TRIGGER_TYPES}


# ── Conversation Statuses ────────────────────────────────────────────

CONVERSATION_STATUSES: List[Dict[str, str]] = [
    {
        "key": "bot_active",
        "label": "AI Active",
        "description": "AI bot is handling this conversation.",
    },
    {
        "key": "human_takeover",
        "label": "Human Control",
        "description": "A human agent has taken over.",
    },
    {
        "key": "closed",
        "label": "Closed",
        "description": "Conversation is closed.",
    },
]


# ── Message Delivery Statuses ────────────────────────────────────────

MESSAGE_DELIVERY_STATUSES: List[Dict[str, str]] = [
    {"key": "pending", "label": "Pending", "description": "Message queued for delivery."},
    {"key": "sending", "label": "Sending", "description": "Message is being sent."},
    {"key": "sent", "label": "Sent", "description": "Message delivered successfully."},
    {"key": "delivered", "label": "Delivered", "description": "Message confirmed delivered to recipient."},
    {"key": "read", "label": "Read", "description": "Message read by recipient."},
    {"key": "failed", "label": "Failed", "description": "Message delivery failed."},
    {"key": "dead_letter", "label": "Dead Letter", "description": "Message permanently failed after max retries."},
]


# ── Workspace Roles ──────────────────────────────────────────────────

WORKSPACE_ROLES: List[Dict[str, str]] = [
    {"key": "owner", "label": "Owner", "description": "Full control of the workspace."},
    {"key": "member", "label": "Member", "description": "Can view and edit workspace data."},
    {"key": "viewer", "label": "Viewer", "description": "Read-only access to workspace data."},
]


# ── Agency Roles (admin-roles catalog) ───────────────────────────────

AGENCY_ROLES: List[Dict[str, str]] = [
    {
        "key": "agency_owner",
        "label": "Agency Owner",
        "description": "Full control of the agency and all client workspaces.",
    },
    {
        "key": "agency_admin",
        "label": "Agency Admin",
        "description": "Manage agency settings and client workspaces.",
    },
    {
        "key": "agency_operator",
        "label": "Agency Operator",
        "description": "Operate client workspaces day-to-day.",
    },
    {
        "key": "agency_viewer",
        "label": "Agency Viewer",
        "description": "Read-only access to agency data.",
    },
]


# ── Module Labels ────────────────────────────────────────────────────

MODULE_LABELS: Dict[str, str] = {
    "auth": "Authentication",
    "email_engine": "Email Engine",
    "email_verification": "Email Verification",
    "prompt_studio": "Prompt Studio",
    "knowledge_files": "Knowledge Files",
    "integrations_hub": "Integrations Hub",
    "integrations_connect": "Integration Connect",
    "webhooks_ingestion": "Webhook Ingestion",
    "runtime_engine": "Runtime Engine",
    "dispatch_engine": "Dispatch Engine",
    "inbox": "Inbox",
    "zoho_sync": "Zoho Sync",
    "analytics": "Analytics",
    "automations": "Automations",
    "diagnostics": "Diagnostics",
    "admin_portal": "Admin Portal",
}


# ── Timezones ───────────────────────────────────────────────────────

TIMEZONES: List[Dict[str, str]] = [
    {"key": "UTC", "label": "UTC (Coordinated Universal Time)"},
    {"key": "US/Eastern", "label": "US/Eastern (EST/EDT)"},
    {"key": "US/Central", "label": "US/Central (CST/CDT)"},
    {"key": "US/Pacific", "label": "US/Pacific (PST/PDT)"},
    {"key": "Europe/London", "label": "Europe/London (GMT/BST)"},
    {"key": "Europe/Paris", "label": "Europe/Paris (CET/CEST)"},
    {"key": "Asia/Dubai", "label": "Asia/Dubai (GST)"},
    {"key": "Asia/Tokyo", "label": "Asia/Tokyo (JST)"},
    {"key": "Asia/Shanghai", "label": "Asia/Shanghai (CST)"},
    {"key": "Australia/Sydney", "label": "Australia/Sydney (AEST)"},
]


# ── Languages ───────────────────────────────────────────────────────

LANGUAGES: List[Dict[str, str]] = [
    {"key": "en", "label": "English"},
    {"key": "ar", "label": "Arabic"},
    {"key": "es", "label": "Spanish"},
    {"key": "fr", "label": "French"},
    {"key": "de", "label": "German"},
    {"key": "zh", "label": "Chinese"},
    {"key": "pt", "label": "Portuguese"},
    {"key": "ja", "label": "Japanese"},
]


# ── AI Models ───────────────────────────────────────────────────────

AI_MODELS: List[Dict[str, str]] = [
    {"key": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
    {"key": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
    {"key": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
]


# ── Dedupe Strategies ──────────────────────────────────────────────

DEDUPE_STRATEGIES: List[Dict[str, str]] = [
    {"key": "EMAIL", "label": "Email Address Only"},
    {"key": "PHONE", "label": "Phone Number Only"},
    {"key": "EMAIL_OR_PHONE", "label": "Email OR Phone (Recommended)"},
]


# ── Event Sources ──────────────────────────────────────────────────

EVENT_SOURCES: List[Dict[str, str]] = [
    {"key": "webhook", "label": "Webhook"},
    {"key": "runtime", "label": "Runtime"},
    {"key": "dispatch", "label": "Dispatch"},
    {"key": "email", "label": "Email"},
    {"key": "zoho", "label": "Zoho"},
    {"key": "inbox", "label": "Inbox"},
]


# ── Event Outcomes ─────────────────────────────────────────────────

EVENT_OUTCOMES: List[Dict[str, str]] = [
    {"key": "success", "label": "Success"},
    {"key": "failure", "label": "Failure"},
    {"key": "skipped", "label": "Skipped"},
]


# ── Audit Actions ──────────────────────────────────────────────────

AUDIT_ACTIONS: List[Dict[str, str]] = [
    {"key": "user_login", "label": "User Login"},
    {"key": "user_signup", "label": "User Signup"},
    {"key": "update_profile", "label": "Profile Update"},
    {"key": "workspace_create", "label": "Workspace Create"},
    {"key": "workspace_invite", "label": "Workspace Invite"},
    {"key": "workspace_member_remove", "label": "Member Remove"},
    {"key": "workspace_role_change", "label": "Role Change"},
    {"key": "automation_create", "label": "Automation Create"},
    {"key": "automation_publish", "label": "Automation Publish"},
    {"key": "integration_connect", "label": "Integration Connect"},
    {"key": "integration_disconnect", "label": "Integration Disconnect"},
    {"key": "dispatch_trigger", "label": "Dispatch Trigger"},
    {"key": "inbox_reply", "label": "Inbox Reply"},
    {"key": "inbox_status_change", "label": "Inbox Status Change"},
    {"key": "update_workspace_settings", "label": "Settings Update"},
]


# ── Contact Fields ─────────────────────────────────────────────────

CONTACT_FIELDS: List[Dict[str, Any]] = [
    {"key": "first_name", "label": "First Name", "required": True},
    {"key": "last_name", "label": "Last Name", "required": True},
    {"key": "email", "label": "Email", "required": False},
    {"key": "phone", "label": "Phone", "required": False},
    {"key": "company", "label": "Company", "required": False},
    {"key": "description", "label": "Description / Notes", "required": False},
]


# ── Template Categories ──────────────────────────────────────────────

TEMPLATE_CATEGORIES: List[Dict[str, str]] = [
    {"key": "lead_generation", "label": "Lead Generation"},
    {"key": "customer_support", "label": "Customer Support"},
    {"key": "sales", "label": "Sales"},
    {"key": "onboarding", "label": "Onboarding"},
    {"key": "general", "label": "General"},
]


# ── Template Platforms ───────────────────────────────────────────────

TEMPLATE_PLATFORMS: List[Dict[str, str]] = [
    {"key": "whatsapp", "label": "WhatsApp"},
    {"key": "meta", "label": "Meta"},
]
