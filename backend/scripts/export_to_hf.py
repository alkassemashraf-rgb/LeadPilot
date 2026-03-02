"""
export_to_hf.py — LeadPilot V2

Exports static seed data and all user-generated data to the
HuggingFace dataset repo: ashrafkassem/leadpilot-data

Usage:
    cd backend/
    python scripts/export_to_hf.py [--mode all|static|dynamic] [--dry-run]
    python scripts/export_to_hf.py --mode static --hf-token hf_xxx
    python scripts/export_to_hf.py --dry-run

Env vars (can also be passed as CLI flags):
    DATABASE_URL        — SQLite/Postgres URL (from app config)
    HF_TOKEN            — HuggingFace write token (required for live export)
    HF_DATASET_REPO     — Dataset repo ID (default: ashrafkassem/leadpilot-data)
"""
import sys
import os
import asyncio
import argparse
import hashlib
import json
import io
import logging
from datetime import datetime, timezone

# ── path bootstrap (same pattern as create_test_user.py) ─────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.models import (
    Workspace, Contact, Conversation, Message,
    Flow, ExecutionInstance, AdminAuditLog,
)
from app.core.seed import SEED_TEMPLATES, DEFAULT_PLANS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── PII pseudonymization helpers ─────────────────────────────────────────────

def _hash(value: str, length: int = 16) -> str:
    """Deterministic, non-reversible SHA-256 truncated to `length` hex chars."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _redact_contact(row: dict) -> dict:
    """Replace PII fields in a contact dict with deterministic hashes."""
    for field in ("first_name", "last_name", "display_name"):
        if row.get(field):
            row[field] = _hash(row[field], 8)
    if row.get("external_id"):
        row["external_id"] = _hash(row["external_id"], 12)
    if row.get("zoho_lead_id"):
        row["zoho_lead_id"] = _hash(row["zoho_lead_id"], 12)
    # additional_metadata may contain raw lead form data (emails, phones)
    row["additional_metadata"] = {}
    return row


def _redact_message(row: dict) -> dict:
    """Replace message content with [REDACTED], keep content_length as proxy metric."""
    content = row.get("content") or ""
    row["content_length"] = len(content)
    row["content"] = "[REDACTED]"
    # additional_metadata may contain media URLs or phone numbers
    row["additional_metadata"] = {}
    return row


def _redact_audit_log(row: dict) -> dict:
    """Strip IP, user agent, and hash actor/entity IDs."""
    row["ip_address"] = None
    row["user_agent"] = None
    row["error_message"] = None
    if row.get("actor_user_id"):
        row["actor_user_id"] = _hash(row["actor_user_id"], 12)
    if row.get("entity_id"):
        row["entity_id"] = _hash(row["entity_id"], 12)
    return row


# ── Static builders (no DB required) ─────────────────────────────────────────

def build_templates_jsonl() -> str:
    """Build JSONL for automation templates directly from SEED_TEMPLATES constant."""
    lines = []
    for t in SEED_TEMPLATES:
        row = {
            "slug": t["slug"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "platforms": t["platforms"],
            "industry_tags": t.get("industry_tags", []),
            "required_integrations": t.get("required_integrations", []),
            "is_featured": t.get("is_featured", False),
            "variables": [
                {
                    "key": v["key"],
                    "label": v["label"],
                    "var_type": v.get("var_type", "text"),
                    "required": v.get("required", True),
                    "description": v.get("description"),
                    "default_value": v.get("default_value"),
                }
                for v in t.get("variables", [])
            ],
            "builder_graph_json": t["builder_graph_json"],
        }
        lines.append(json.dumps(row, default=str))
    return "\n".join(lines)


def build_plans_jsonl() -> str:
    """Build JSONL for plan tiers + entitlements from DEFAULT_PLANS constant."""
    lines = []
    for name, display_name, sort_order, description, entitlements in DEFAULT_PLANS:
        row = {
            "name": name,
            "display_name": display_name,
            "sort_order": sort_order,
            "description": description,
            "entitlements": [
                {"module_key": k, "hard_limit": v}
                for k, v in entitlements.items()
            ],
        }
        lines.append(json.dumps(row, default=str))
    return "\n".join(lines)


# ── Dynamic builders (async DB, paginated) ────────────────────────────────────

async def build_workspaces_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(Workspace).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for ws in rows:
            lines.append(json.dumps({
                "id": str(ws.id),
                "subscription_tier": ws.subscription_tier,
                "created_at": ws.created_at.isoformat(),
            }, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_contacts_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(Contact).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for c in rows:
            row = _redact_contact({
                "id": str(c.id),
                "workspace_id": str(c.workspace_id),
                "external_id": c.external_id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "display_name": c.display_name,
                "zoho_lead_id": c.zoho_lead_id,
                "zoho_last_synced_at": c.zoho_last_synced_at.isoformat() if c.zoho_last_synced_at else None,
                "additional_metadata": dict(c.additional_metadata or {}),
                "created_at": c.created_at.isoformat(),
            })
            lines.append(json.dumps(row, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_conversations_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(Conversation).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for conv in rows:
            status = conv.status.value if hasattr(conv.status, "value") else conv.status
            lines.append(json.dumps({
                "id": str(conv.id),
                "workspace_id": str(conv.workspace_id),
                "contact_id": str(conv.contact_id),
                "status": status,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "created_at": conv.created_at.isoformat(),
            }, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_messages_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(Message).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for msg in rows:
            delivery = msg.delivery_status.value if hasattr(msg.delivery_status, "value") else msg.delivery_status
            row = _redact_message({
                "id": str(msg.id),
                "workspace_id": str(msg.workspace_id),
                "conversation_id": str(msg.conversation_id),
                "direction": msg.direction,
                "content": msg.content,
                "platform": msg.platform,
                "delivery_status": delivery,
                "attempt_count": msg.attempt_count,
                "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
                "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
                "read_at": msg.read_at.isoformat() if msg.read_at else None,
                "additional_metadata": dict(msg.additional_metadata or {}),
                "created_at": msg.created_at.isoformat(),
            })
            lines.append(json.dumps(row, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_flows_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(Flow).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for flow in rows:
            status = flow.status.value if hasattr(flow.status, "value") else flow.status
            lines.append(json.dumps({
                "id": str(flow.id),
                "workspace_id": str(flow.workspace_id),
                "name": _hash(flow.name, 8),  # pseudonymize (may contain business name)
                "status": status,
                "source_template_id": str(flow.source_template_id) if flow.source_template_id else None,
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat(),
            }, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_executions_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(ExecutionInstance).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for ex in rows:
            status = ex.status.value if hasattr(ex.status, "value") else ex.status
            lines.append(json.dumps({
                "id": str(ex.id),
                "workspace_id": str(ex.workspace_id),
                "flow_version_id": str(ex.flow_version_id),
                "contact_id": str(ex.contact_id) if ex.contact_id else None,
                "status": status,
                "abort_reason": ex.abort_reason,
                "created_at": ex.created_at.isoformat(),
                "updated_at": ex.updated_at.isoformat(),
            }, default=str))
        offset += batch_size
    return "\n".join(lines)


async def build_audit_logs_jsonl(session: AsyncSession, batch_size: int) -> str:
    lines = []
    offset = 0
    while True:
        result = await session.execute(select(AdminAuditLog).offset(offset).limit(batch_size))
        rows = result.scalars().all()
        if not rows:
            break
        for log in rows:
            row = _redact_audit_log({
                "id": str(log.id),
                "workspace_id": str(log.workspace_id) if log.workspace_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "actor_type": log.actor_type,
                "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
                "outcome": log.outcome,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "request_path": log.request_path,
                "request_method": log.request_method,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            })
            lines.append(json.dumps(row, default=str))
        offset += batch_size
    return "\n".join(lines)


# ── Dataset card ──────────────────────────────────────────────────────────────

DATASET_README = """\
---
license: mit
task_categories:
  - text-generation
  - text-classification
language:
  - en
  - ar
tags:
  - lead-generation
  - automation
  - whatsapp
  - meta
  - crm
  - saas
pretty_name: LeadPilot Automation Dataset
size_categories:
  - 1K<n<10K
---

# LeadPilot Automation Dataset

Companion dataset for the [LeadPilot HuggingFace Space](https://huggingface.co/spaces/ashrafkassem/LeadPilot).

LeadPilot is a multi-tenant SaaS automation platform for lead capture via WhatsApp and Meta
(Instagram DM, Messenger, Lead Ads), with Zoho CRM sync.

## Dataset Contents

### static/
Pre-seeded catalog data — does not change at runtime.

| File | Rows | Description |
|---|---|---|
| `static/templates.jsonl` | 12 | Automation flow templates (slug, name, category, platforms, builder_graph_json, variables) |
| `static/plans.jsonl` | 3 | Subscription plans (free/growth/enterprise) with module entitlements |

### dynamic/
User-generated operational data, exported daily at 02:00 UTC from the live app.
All PII fields are pseudonymized using SHA-256 truncated hashes before export.

| File | Description |
|---|---|
| `dynamic/workspaces.jsonl` | Workspace records (id, subscription_tier, created_at) |
| `dynamic/contacts.jsonl` | Pseudonymized contacts (hashed name, hashed external_id/zoho_id) |
| `dynamic/conversations.jsonl` | Conversation threads (ids, status, timestamps) |
| `dynamic/messages.jsonl` | Messages (content replaced with [REDACTED], content_length kept) |
| `dynamic/flows.jsonl` | Automation flows (name hashed, status, source_template_id) |
| `dynamic/executions.jsonl` | Flow execution instances (status, timing) |
| `dynamic/audit_logs.jsonl` | Admin audit trail (IPs/UAs stripped, actor/entity ids hashed) |
| `dynamic/meta.json` | Export metadata (exported_at, mode) |

## PII Handling

All personally identifiable information is removed or pseudonymized before export:

- `Contact.first_name`, `last_name`, `display_name` → SHA-256[:8] hex
- `Contact.external_id` (WhatsApp phone / Meta PSID) → SHA-256[:12] hex
- `Contact.zoho_lead_id` → SHA-256[:12] hex
- `Contact.additional_metadata` → replaced with `{}`
- `Message.content` → replaced with `"[REDACTED]"`, `content_length` field added
- `Message.additional_metadata` → replaced with `{}`
- `Flow.name` → SHA-256[:8] hex (may contain business names)
- `AdminAuditLog.ip_address`, `user_agent`, `error_message` → `null`
- `AdminAuditLog.actor_user_id`, `entity_id` → SHA-256[:12] hex

## Export Schedule

Updated daily at 02:00 UTC via Celery Beat.
Last export timestamp is in `dynamic/meta.json`.

## License

MIT
"""


# ── HuggingFace upload ────────────────────────────────────────────────────────

def upload_to_hf(
    files: dict,
    repo_id: str,
    token: str,
    dry_run: bool = False,
) -> None:
    """Upload a dict of {path_in_repo: content_str} to a HuggingFace dataset repo."""
    if dry_run:
        logger.info("[dry-run] Would upload %d files to %s:", len(files), repo_id)
        for path, content in files.items():
            line_count = content.count("\n") + 1 if content.strip() else 0
            logger.info("  %-45s  (%d lines)", path, line_count)
        return

    from huggingface_hub import HfApi, CommitOperationAdd

    api = HfApi(token=token)

    # Create repo if it doesn't exist
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        logger.info("Dataset repo %s already exists.", repo_id)
    except Exception:
        logger.info("Dataset repo %s not found — creating it.", repo_id)
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)

    operations = [
        CommitOperationAdd(
            path_in_repo=path,
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
        )
        for path, content in files.items()
    ]

    commit_msg = f"chore: automated export {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        operations=operations,
        commit_message=commit_msg,
    )
    logger.info("Committed %d files to %s", len(operations), repo_id)


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def run_export(
    mode: str,
    batch_size: int,
    dry_run: bool,
    hf_token: str,
    repo_id: str,
) -> None:
    files: dict = {}

    # ── Static files (always from constants, never from DB) ───────────────────
    if mode in ("static", "all"):
        logger.info("Building static/templates.jsonl ...")
        files["static/templates.jsonl"] = build_templates_jsonl()
        logger.info("Building static/plans.jsonl ...")
        files["static/plans.jsonl"] = build_plans_jsonl()

    # ── Dynamic files (from live DB) ──────────────────────────────────────────
    if mode in ("dynamic", "all"):
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            logger.info("Building dynamic/workspaces.jsonl ...")
            files["dynamic/workspaces.jsonl"] = await build_workspaces_jsonl(session, batch_size)
            logger.info("Building dynamic/contacts.jsonl ...")
            files["dynamic/contacts.jsonl"] = await build_contacts_jsonl(session, batch_size)
            logger.info("Building dynamic/conversations.jsonl ...")
            files["dynamic/conversations.jsonl"] = await build_conversations_jsonl(session, batch_size)
            logger.info("Building dynamic/messages.jsonl ...")
            files["dynamic/messages.jsonl"] = await build_messages_jsonl(session, batch_size)
            logger.info("Building dynamic/flows.jsonl ...")
            files["dynamic/flows.jsonl"] = await build_flows_jsonl(session, batch_size)
            logger.info("Building dynamic/executions.jsonl ...")
            files["dynamic/executions.jsonl"] = await build_executions_jsonl(session, batch_size)
            logger.info("Building dynamic/audit_logs.jsonl ...")
            files["dynamic/audit_logs.jsonl"] = await build_audit_logs_jsonl(session, batch_size)

        files["dynamic/meta.json"] = json.dumps({
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
        })

    # Dataset card (always refreshed)
    files["README.md"] = DATASET_README

    upload_to_hf(files, repo_id=repo_id, token=hf_token, dry_run=dry_run)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export LeadPilot data to HuggingFace dataset repo"
    )
    parser.add_argument(
        "--mode", choices=["static", "dynamic", "all"], default="all",
        help="Which data to export (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be uploaded without making any HF API calls",
    )
    parser.add_argument(
        "--hf-token", default=None,
        help="HuggingFace write token (overrides HF_TOKEN env var)",
    )
    parser.add_argument(
        "--repo-id", default=None,
        help="Dataset repo ID (overrides HF_DATASET_REPO env var)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=5000,
        help="DB pagination batch size for dynamic exports (default: 5000)",
    )
    args = parser.parse_args()

    hf_token = args.hf_token or settings.HF_TOKEN
    repo_id = args.repo_id or settings.HF_DATASET_REPO

    if not args.dry_run and not hf_token:
        logger.error("HF_TOKEN is not set. Use --hf-token or set the HF_TOKEN env var.")
        sys.exit(1)

    asyncio.run(run_export(
        mode=args.mode,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        hf_token=hf_token or "dry-run",
        repo_id=repo_id,
    ))


if __name__ == "__main__":
    main()
