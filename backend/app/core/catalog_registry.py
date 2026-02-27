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
    },
    {
        "key": "SEND_MESSAGE",
        "label": "Send Message",
        "description": "Send a message via the connected platform.",
        "icon_hint": "send",
    },
    {
        "key": "HUMAN_HANDOVER",
        "label": "Human Handover",
        "description": "Transfer conversation to a human agent.",
        "icon_hint": "user",
    },
    {
        "key": "TAG_CONTACT",
        "label": "Tag Contact",
        "description": "Apply a tag to the contact for segmentation.",
        "icon_hint": "tag",
    },
]

VALID_NODE_TYPES = {n["key"] for n in AUTOMATION_NODE_TYPES}


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
    {"key": "failed", "label": "Failed", "description": "Message delivery failed."},
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
