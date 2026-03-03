"""
Startup seed utilities: Ensures all canonical modules, default plans, and seed users exist.
Runs once on app startup; idempotent (uses INSERT or IGNORE logic via get-or-create).
"""
import logging
from datetime import datetime
from app.core.db import SessionLocal as AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.models import (
    SystemModuleConfig, Plan, PlanEntitlement, SystemSettings,
    User, Workspace, WorkspaceMember, WorkspaceRole,
    AutomationTemplate, AutomationTemplateVersion,
    TemplateVariable, TemplateUsageStat,
)
from app.core.modules import ALL_MODULES
from app.domain.builder_translator import translate
from sqlmodel import select

logger = logging.getLogger(__name__)

# --- Default plan definitions ---
# Each entry: (name, display_name, sort_order, description, entitlements_dict)
# entitlements_dict: {module_key: hard_limit} where None = unlimited
DEFAULT_PLANS = [
    (
        "free", "Free", 0, "Basic access with limited usage",
        {
            "prompt_studio": 1,
            "runtime_engine": 50,
            "integrations_connect": 1,
            "automations": 2,
            "dispatch_engine": 200,
            "knowledge_files": 5,
            "analytics": None,
            "inbox": None,
            "max_workspaces": 1,
        }
    ),
    (
        "growth", "Growth", 1, "Expanded limits for growing teams",
        {
            "prompt_studio": 10,
            "runtime_engine": 500,
            "integrations_connect": 5,
            "automations": 20,
            "dispatch_engine": 2000,
            "knowledge_files": 50,
            "analytics": None,
            "inbox": None,
            "webhooks_ingestion": None,
            "zoho_sync": 500,
            "max_workspaces": 5,
        }
    ),
    (
        "enterprise", "Enterprise", 2, "Unlimited access to all modules",
        {
            "prompt_studio": None,
            "runtime_engine": None,
            "integrations_connect": None,
            "automations": None,
            "dispatch_engine": None,
            "knowledge_files": None,
            "analytics": None,
            "inbox": None,
            "webhooks_ingestion": None,
            "zoho_sync": None,
            "diagnostics": None,
            "email_engine": None,
            "email_verification": None,
            "integrations_hub": None,
            "admin_portal": None,
            "auth": None,
            "max_workspaces": None,
        }
    ),
]


async def seed_modules():
    """
    Ensures every module in ALL_MODULES has a row in systemmoduleconfig.
    - All modules default to is_enabled=True.
    - admin_portal is also enabled by default (and is locked against being disabled via API).
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SystemModuleConfig.module_name))
            existing = {row[0] for row in result.all()}

            new_count = 0
            for module_name in ALL_MODULES:
                if module_name not in existing:
                    mod = SystemModuleConfig(
                        module_name=module_name,
                        is_enabled=True,  # All modules start enabled
                    )
                    db.add(mod)
                    new_count += 1

            if new_count > 0:
                await db.commit()
                logger.info(f"[seed_modules] Seeded {new_count} module(s) into SystemModuleConfig.")
            else:
                logger.info("[seed_modules] All modules already seeded; no action taken.")
    except Exception as e:
        logger.error(f"[seed_modules] Failed to seed modules: {e}", exc_info=True)


async def seed_plans():
    """
    Ensures the default plans (Free, Growth, Enterprise) exist with their entitlements.
    Idempotent:
    - Creates plans that don't exist yet (with all entitlements).
    - For plans that already exist, adds any entitlements that are missing.
    - Never removes or modifies existing entitlements.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Plan.name, Plan.id))
            existing_plans = {row[0]: row[1] for row in result.all()}

            new_plan_count = 0
            new_ent_count = 0

            for name, display_name, sort_order, description, entitlements in DEFAULT_PLANS:
                if name not in existing_plans:
                    plan = Plan(
                        name=name,
                        display_name=display_name,
                        sort_order=sort_order,
                        description=description,
                        is_active=True,
                    )
                    db.add(plan)
                    await db.flush()  # get plan.id

                    for module_key, hard_limit in entitlements.items():
                        db.add(PlanEntitlement(
                            plan_id=plan.id,
                            module_key=module_key,
                            hard_limit=hard_limit,
                        ))

                    new_plan_count += 1

                else:
                    # Plan exists — add any entitlements that are missing
                    plan_id = existing_plans[name]
                    ent_result = await db.execute(
                        select(PlanEntitlement.module_key).where(
                            PlanEntitlement.plan_id == plan_id
                        )
                    )
                    existing_keys = {row[0] for row in ent_result.all()}

                    for module_key, hard_limit in entitlements.items():
                        if module_key not in existing_keys:
                            db.add(PlanEntitlement(
                                plan_id=plan_id,
                                module_key=module_key,
                                hard_limit=hard_limit,
                            ))
                            new_ent_count += 1
                            logger.info(
                                f"[seed_plans] Added missing entitlement '{module_key}' to plan '{name}'."
                            )

            if new_plan_count > 0 or new_ent_count > 0:
                await db.commit()
                logger.info(
                    f"[seed_plans] Seeded {new_plan_count} plan(s) and {new_ent_count} missing entitlement(s)."
                )
            else:
                logger.info("[seed_plans] All default plans and entitlements already seeded; no action taken.")
    except Exception as e:
        logger.error(f"[seed_plans] Failed to seed plans: {e}", exc_info=True)


async def seed_system_settings():
    """Ensure the single-row SystemSettings exists with defaults."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.singleton_key == "global")
            )
            if not result.scalars().first():
                import copy
                from app.services.settings_service import SYSTEM_SETTINGS_DEFAULT
                ss = SystemSettings(
                    singleton_key="global",
                    settings_json=copy.deepcopy(SYSTEM_SETTINGS_DEFAULT),
                    version=1,
                )
                db.add(ss)
                await db.commit()
                logger.info("[seed_system_settings] Seeded default system settings.")
            else:
                logger.info("[seed_system_settings] System settings already exist.")
    except Exception as e:
        logger.error(f"[seed_system_settings] Failed: {e}", exc_info=True)


# --- Default seed users ---
SEED_USERS = [
    {
        "email": "demo@leadpilot.com",
        "password": "demo123456",
        "full_name": "Demo User",
        "is_superuser": False,
        "workspace_name": "Demo Workspace",
    },
    {
        "email": "admin@leadpilot.com",
        "password": "admin123456",
        "full_name": "Admin",
        "is_superuser": True,
        "workspace_name": "Admin Workspace",
    },
]


async def seed_users():
    """
    Seed demo and admin users with workspaces. Idempotent: skips if email exists.
    Both users are created with email_verified_at set (no verification required).
    """
    try:
        async with AsyncSessionLocal() as db:
            new_count = 0
            for user_def in SEED_USERS:
                result = await db.execute(
                    select(User).where(User.email == user_def["email"])
                )
                if result.scalars().first():
                    logger.info(f"[seed_users] {user_def['email']} already exists; skipping.")
                    continue

                now = datetime.utcnow()
                user = User(
                    email=user_def["email"],
                    hashed_password=get_password_hash(user_def["password"]),
                    full_name=user_def["full_name"],
                    is_active=True,
                    is_superuser=user_def["is_superuser"],
                    email_verified_at=now,
                )
                db.add(user)
                await db.flush()

                workspace = Workspace(name=user_def["workspace_name"])
                db.add(workspace)
                await db.flush()

                membership = WorkspaceMember(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    role=WorkspaceRole.OWNER,
                )
                db.add(membership)
                new_count += 1
                logger.info(f"[seed_users] Created {user_def['email']} (superuser={user_def['is_superuser']}).")

            if new_count > 0:
                await db.commit()
                logger.info(f"[seed_users] Seeded {new_count} user(s).")
            else:
                logger.info("[seed_users] All seed users already exist; no action taken.")
    except Exception as e:
        logger.error(f"[seed_users] Failed: {e}", exc_info=True)


# --- Helper: build a valid builder graph ---

def _graph(trigger_type, platform, steps):
    """Build a valid builder_graph_json from a trigger and list of step tuples."""
    nodes = [
        {
            "id": "trigger-1",
            "type": "triggerNode",
            "position": {"x": 250, "y": 50},
            "data": {"nodeType": trigger_type, "platform": platform, "config": {}},
        }
    ]
    edges = []
    y = 220
    prev_id = "trigger-1"
    for i, (node_type, config) in enumerate(steps, start=1):
        nid = f"node-{i}"
        nodes.append({
            "id": nid,
            "type": "actionNode",
            "position": {"x": 250, "y": y},
            "data": {"nodeType": node_type, "config": config},
        })
        edges.append({"id": f"e{i}", "source": prev_id, "target": nid})
        prev_id = nid
        y += 180
    return {"nodes": nodes, "edges": edges}


# Common variables shared by all templates
_COMMON_VARS = [
    {"key": "business_name", "label": "Business Name", "description": "Your business or brand name", "required": True},
    {"key": "company_name", "label": "Company Name", "description": "Legal company name (can match business name)", "required": False, "default_value": ""},
]

_SALES_VARS = _COMMON_VARS + [
    {"key": "sales_phone", "label": "Sales Phone", "var_type": "phone", "description": "Phone number for sales inquiries", "required": False, "default_value": ""},
    {"key": "working_hours", "label": "Working Hours", "description": "e.g. Mon-Fri 9am-6pm", "required": False, "default_value": "Mon-Fri 9am-6pm"},
]


SEED_TEMPLATES = [
    # 1. WhatsApp Lead Qualifier Basic
    {
        "slug": "whatsapp-lead-qualifier-basic",
        "name": "WhatsApp Lead Qualifier",
        "description": "Automatically qualify inbound WhatsApp leads by collecting key information and tagging them for follow-up.",
        "category": "lead_generation",
        "platforms": ["whatsapp"],
        "industry_tags": ["real-estate", "services", "saas"],
        "required_integrations": ["whatsapp"],
        "is_featured": True,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "Welcome the visitor to {{business_name}}. Ask qualifying questions: What are they looking for? What is their budget range? What is their timeline? Collect their name and email if possible.",
                "tasks": ["Greet warmly", "Ask about needs", "Ask budget and timeline", "Collect name and email"],
            }),
            ("TAG_CONTACT", {"tag": "new-lead"}),
            ("HUMAN_HANDOVER", {"announcement": "A qualified lead from {{business_name}} is ready for follow-up."}),
        ]),
    },
    # 2. WhatsApp Appointment Booking
    {
        "slug": "whatsapp-appointment-booking",
        "name": "WhatsApp Appointment Scheduler",
        "description": "Let customers book appointments through WhatsApp with AI-guided scheduling and confirmation.",
        "category": "sales",
        "platforms": ["whatsapp"],
        "industry_tags": ["healthcare", "beauty", "consulting"],
        "required_integrations": ["whatsapp"],
        "is_featured": False,
        "variables": _SALES_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "Help the customer schedule an appointment with {{business_name}}. Ask for their preferred date and time. Our working hours are {{working_hours}}. Collect their name and contact details.",
                "tasks": ["Ask preferred date/time", "Confirm availability", "Collect name and phone"],
            }),
            ("SEND_MESSAGE", {"content": "Your appointment request has been received! A team member from {{business_name}} will confirm shortly. For urgent inquiries, call {{sales_phone}}."}),
            ("HUMAN_HANDOVER", {"announcement": "Appointment request ready for confirmation."}),
        ]),
    },
    # 3. WhatsApp FAQ Responder
    {
        "slug": "whatsapp-faq-responder",
        "name": "WhatsApp FAQ Auto-Responder",
        "description": "Answer common customer questions automatically using AI, with seamless handover for complex queries.",
        "category": "customer_support",
        "platforms": ["whatsapp"],
        "industry_tags": ["e-commerce", "saas", "services"],
        "required_integrations": ["whatsapp"],
        "is_featured": False,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "Answer the customer's question about {{business_name}} using your knowledge base. Be helpful, concise, and professional. If the question is too complex or requires human judgment, let the customer know a team member will help.",
                "tasks": ["Identify the question topic", "Provide accurate answer", "Offer to connect with a human if needed"],
            }),
            ("HUMAN_HANDOVER", {"announcement": "Customer needs human assistance for a question the AI couldn't fully resolve."}),
        ]),
    },
    # 4. WhatsApp Pricing Gatekeeper
    {
        "slug": "whatsapp-pricing-gatekeeper",
        "name": "WhatsApp Pricing Gatekeeper",
        "description": "Qualify leads asking about pricing by understanding their needs before connecting them with sales.",
        "category": "sales",
        "platforms": ["whatsapp"],
        "industry_tags": ["saas", "services", "consulting"],
        "required_integrations": ["whatsapp"],
        "is_featured": False,
        "variables": _SALES_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "The customer is asking about {{business_name}} pricing. Before sharing pricing, qualify them: What specific product or service are they interested in? What is their company size? What is their budget range? What is their decision timeline?",
                "tasks": ["Understand their interest", "Ask company size", "Qualify budget range", "Ask decision timeline"],
            }),
            ("TAG_CONTACT", {"tag": "high-value"}),
            ("HUMAN_HANDOVER", {"announcement": "Qualified pricing inquiry ready for sales team. Contact: {{sales_phone}}"}),
        ]),
    },
    # 5. WhatsApp Reactivation Campaign
    {
        "slug": "whatsapp-reactivation-campaign",
        "name": "WhatsApp Re-engagement Bot",
        "description": "Re-engage dormant leads with a friendly follow-up message and AI-powered conversation to reignite interest.",
        "category": "lead_generation",
        "platforms": ["whatsapp"],
        "industry_tags": ["e-commerce", "saas", "real-estate"],
        "required_integrations": ["whatsapp"],
        "is_featured": False,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("SEND_MESSAGE", {"content": "Hi! It's been a while since we last chatted. {{business_name}} has some exciting updates we think you'd love to hear about. Would you like to know more?"}),
            ("AI_REPLY", {
                "goal": "Follow up on the re-engagement message for {{business_name}}. If the customer shows interest, share what's new and try to schedule a follow-up or demo. If not interested, thank them gracefully.",
                "tasks": ["Gauge interest level", "Share relevant updates", "Try to schedule follow-up"],
            }),
            ("TAG_CONTACT", {"tag": "reactivated"}),
        ]),
    },
    # 6. WhatsApp Sales Concierge
    {
        "slug": "whatsapp-sales-concierge",
        "name": "WhatsApp Sales Concierge",
        "description": "Full-service AI sales assistant that qualifies leads, captures details, syncs to CRM, and hands over to your sales team.",
        "category": "sales",
        "platforms": ["whatsapp"],
        "industry_tags": ["saas", "real-estate", "consulting", "services"],
        "required_integrations": ["whatsapp", "zoho"],
        "is_featured": True,
        "variables": _SALES_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "Act as a professional sales concierge for {{business_name}}. Have a natural conversation to understand the customer's needs, budget, and timeline. Collect their full name, email, phone number, and company name for CRM entry.",
                "tasks": ["Introduce yourself as the AI assistant", "Understand needs and pain points", "Qualify budget and timeline", "Collect full name, email, phone, company"],
            }),
            ("TAG_CONTACT", {"tag": "qualified"}),
            ("ZOHO_UPSERT_LEAD", {}),
            ("HUMAN_HANDOVER", {"announcement": "Qualified lead synced to CRM. Ready for sales follow-up at {{sales_phone}}."}),
        ]),
    },
    # 7. Instagram DM Keyword Responder
    {
        "slug": "instagram-dm-keyword-responder",
        "name": "Instagram DM Auto-Responder",
        "description": "Automatically respond to Instagram DMs with a welcome message and AI follow-up to capture leads.",
        "category": "lead_generation",
        "platforms": ["meta"],
        "industry_tags": ["e-commerce", "fashion", "beauty"],
        "required_integrations": ["meta"],
        "is_featured": False,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "meta", [
            ("SEND_MESSAGE", {"content": "Hey! Thanks for reaching out to {{business_name}} on Instagram! How can we help you today?"}),
            ("AI_REPLY", {
                "goal": "Follow up on the Instagram DM for {{business_name}}. Understand what the customer is looking for, answer their questions, and try to collect their email or phone for follow-up.",
                "tasks": ["Understand their interest", "Answer questions about products/services", "Collect contact details"],
            }),
            ("TAG_CONTACT", {"tag": "ig-lead"}),
        ]),
    },
    # 8. Messenger Support Intake
    {
        "slug": "messenger-support-intake",
        "name": "Messenger Support Intake",
        "description": "Collect support issues through Facebook Messenger with AI triage and human handover.",
        "category": "customer_support",
        "platforms": ["meta"],
        "industry_tags": ["e-commerce", "saas", "services"],
        "required_integrations": ["meta"],
        "is_featured": False,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "meta", [
            ("AI_REPLY", {
                "goal": "You are the support intake bot for {{business_name}}. Collect the customer's issue details: What problem are they experiencing? When did it start? What have they already tried? Categorize the issue and prepare a summary for the support team.",
                "tasks": ["Identify the issue", "Collect details and steps to reproduce", "Categorize severity", "Summarize for support team"],
            }),
            ("TAG_CONTACT", {"tag": "support"}),
            ("HUMAN_HANDOVER", {"announcement": "Support ticket created via Messenger. Issue details collected by AI."}),
        ]),
    },
    # 9. Meta Lead Ads Intake
    {
        "slug": "meta-lead-ads-intake",
        "name": "Meta Lead Ads Qualifier",
        "description": "Automatically engage Meta Lead Ad submissions with AI qualification and CRM sync.",
        "category": "lead_generation",
        "platforms": ["meta"],
        "industry_tags": ["real-estate", "automotive", "education"],
        "required_integrations": ["meta", "zoho"],
        "is_featured": True,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("LEAD_AD_SUBMIT", "meta", [
            ("AI_REPLY", {
                "goal": "Welcome this lead who submitted a form for {{business_name}}. Thank them for their interest, confirm the details they provided, and ask any additional qualifying questions: What is their budget? When are they looking to make a decision?",
                "tasks": ["Thank for form submission", "Confirm lead details", "Ask qualifying questions", "Collect additional info"],
            }),
            ("TAG_CONTACT", {"tag": "lead-ad"}),
            ("ZOHO_UPSERT_LEAD", {}),
        ]),
    },
    # 10. Instagram Appointment Booking
    {
        "slug": "instagram-appointment-booking",
        "name": "Instagram Appointment Scheduler",
        "description": "Let Instagram followers book appointments through DMs with AI-guided scheduling.",
        "category": "sales",
        "platforms": ["meta"],
        "industry_tags": ["beauty", "healthcare", "fitness"],
        "required_integrations": ["meta"],
        "is_featured": False,
        "variables": _SALES_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "meta", [
            ("AI_REPLY", {
                "goal": "Help the customer book an appointment with {{business_name}} via Instagram DM. Ask for their preferred service, date, and time. Our hours are {{working_hours}}. Collect their name and phone number.",
                "tasks": ["Ask what service they need", "Ask preferred date/time", "Collect name and phone"],
            }),
            ("SEND_MESSAGE", {"content": "Thanks for booking with {{business_name}}! We'll confirm your appointment shortly. Questions? Call us at {{sales_phone}}."}),
            ("TAG_CONTACT", {"tag": "booked"}),
        ]),
    },
    # 11. Omnichannel Lead Qualifier
    {
        "slug": "omnichannel-lead-qualifier",
        "name": "Omnichannel Lead Qualifier",
        "description": "Unified AI lead qualification that works across WhatsApp and Meta channels with CRM integration.",
        "category": "lead_generation",
        "platforms": ["whatsapp", "meta"],
        "industry_tags": ["saas", "services", "real-estate"],
        "required_integrations": ["whatsapp", "meta", "zoho"],
        "is_featured": True,
        "variables": _COMMON_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "Qualify this inbound lead for {{business_name}}. Regardless of which channel they came from, collect: their name, email, what they're looking for, their budget range, and decision timeline. Be professional and conversational.",
                "tasks": ["Greet and introduce {{business_name}}", "Collect name and email", "Understand needs", "Qualify budget and timeline"],
            }),
            ("TAG_CONTACT", {"tag": "qualified"}),
            ("ZOHO_UPSERT_LEAD", {}),
        ]),
    },
    # 12. Inbound to CRM Pipeline
    {
        "slug": "inbound-to-crm-pipeline",
        "name": "Inbound to CRM Pipeline",
        "description": "Capture every inbound conversation, extract structured lead data with AI, sync to your CRM, and hand over to sales.",
        "category": "sales",
        "platforms": ["whatsapp", "meta"],
        "industry_tags": ["saas", "services", "consulting", "real-estate"],
        "required_integrations": ["whatsapp", "meta", "zoho"],
        "is_featured": True,
        "variables": _SALES_VARS,
        "builder_graph_json": _graph("MESSAGE_INBOUND", "whatsapp", [
            ("AI_REPLY", {
                "goal": "You are the intake assistant for {{business_name}}. Collect structured information from the customer: full name, email, phone number, company name, role/title, what they need, budget range, and decision timeline. Be conversational but thorough.",
                "tasks": ["Collect full name", "Collect email and phone", "Ask company and role", "Understand needs", "Qualify budget and timeline"],
                "output_schema": [
                    {"key": "full_name", "label": "Full Name"},
                    {"key": "email", "label": "Email"},
                    {"key": "phone", "label": "Phone"},
                    {"key": "company", "label": "Company"},
                    {"key": "needs", "label": "What they need"},
                    {"key": "budget", "label": "Budget range"},
                ],
            }),
            ("TAG_CONTACT", {"tag": "pipeline"}),
            ("ZOHO_UPSERT_LEAD", {}),
            ("HUMAN_HANDOVER", {"announcement": "New pipeline lead synced to CRM for {{business_name}}. Contact {{sales_phone}} for immediate follow-up."}),
        ]),
    },
]


async def seed_templates():
    """Seed 12 production automation templates. Idempotent by slug."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AutomationTemplate.slug))
            existing_slugs = {row[0] for row in result.all()}

            new_count = 0
            for tmpl_def in SEED_TEMPLATES:
                if tmpl_def["slug"] in existing_slugs:
                    continue

                now = datetime.utcnow()
                template = AutomationTemplate(
                    slug=tmpl_def["slug"],
                    name=tmpl_def["name"],
                    description=tmpl_def["description"],
                    category=tmpl_def["category"],
                    platforms=tmpl_def["platforms"],
                    industry_tags=tmpl_def.get("industry_tags", []),
                    required_integrations=tmpl_def.get("required_integrations", []),
                    is_featured=tmpl_def.get("is_featured", False),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(template)
                await db.flush()

                # Create published version
                builder_json = tmpl_def["builder_graph_json"]
                translated = translate(builder_json)
                version = AutomationTemplateVersion(
                    template_id=template.id,
                    version_number=1,
                    builder_graph_json=builder_json,
                    translated_definition_json=translated,
                    changelog="Initial seed version",
                    is_published=True,
                    published_at=now,
                    created_at=now,
                    updated_at=now,
                )
                db.add(version)
                await db.flush()

                # Create variables
                for i, var_def in enumerate(tmpl_def.get("variables", [])):
                    var = TemplateVariable(
                        template_version_id=version.id,
                        key=var_def["key"],
                        label=var_def["label"],
                        description=var_def.get("description"),
                        var_type=var_def.get("var_type", "text"),
                        required=var_def.get("required", True),
                        default_value=var_def.get("default_value"),
                        sort_order=i,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(var)

                # Create usage stat row
                stat = TemplateUsageStat(
                    template_id=template.id,
                    clone_count=0,
                    publish_count=0,
                    active_flows_count=0,
                    created_at=now,
                    updated_at=now,
                )
                db.add(stat)
                new_count += 1

            if new_count > 0:
                await db.commit()
                logger.info(f"[seed_templates] Seeded {new_count} template(s).")
            else:
                logger.info("[seed_templates] All templates already seeded; no action taken.")
    except Exception as e:
        logger.error(f"[seed_templates] Failed: {e}", exc_info=True)
