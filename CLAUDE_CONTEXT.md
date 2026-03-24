# LeadPilot — Claude Context File

> This file exists so a new Claude instance on any device can immediately understand
> the project history, architecture, and how to continue development.

---

## Project Overview

**LeadPilot** is a multi-tenant SaaS platform for lead capture + automation via
WhatsApp/Meta + CRM (Zoho). Built across 27 missions (as of 2026-02-28).

| Layer | Stack |
|---|---|
| Backend | FastAPI + SQLModel + Alembic, Python 3.11, async |
| Frontend | Next.js 16.1.6 + React 19 + TypeScript + Tailwind 4 |
| DB | SQLite (dev/HuggingFace) / PostgreSQL-ready |
| Queue | Celery + Redis |
| Email | SendGrid / SMTP / console fallback |
| Hosting | HuggingFace Spaces (Docker) + nginx reverse proxy |
| CI | GitHub Actions (`.github/workflows/ci.yml`) — runs ruff + pytest |

---

## Git Remotes

```
origin  git@github.com:alkassemashraf-rgb/LeadPilot.git
hf      https://huggingface.co/spaces/ashrafkassem/LeadPilot
```

**Current HEAD (both remotes):** `d4d1956` — Mission 27 (Automation Builder v2 + Template Catalog Foundation).

### Important git notes
- The project lives in iCloud Drive (`~/Library/Mobile Documents/com~apple~CloudDocs/Personal Projects/LeadPilot`).
  **Do NOT run `git commit` or `git add` from there** — iCloud Drive causes SIGBUS (signal 10)
  on `pack-objects` and "short read" errors when git tries to write objects.
- The Desktop (`~/Desktop`) is ALSO iCloud-synced on this machine — same problem.
- **Safe git workflow:** clone to `/tmp/leadpilot`, make changes, commit + push from there.
  Or open the project from `~/Desktop/LeadPilot V2/` in a new Claude Code session
  (the Desktop copy has a fresh `.venv` and git set up, but files may become iCloud stubs
  over time — always `wc -c` check a few files before trusting git add).
- **Credentials:** macOS Keychain stores HuggingFace token. `git push hf main` works
  without prompts. GitHub uses the same osxkeychain helper.

---

## Mission Completion Status

| # | Mission | Status |
|---|---|---|
| 1 | Auth (signup, login, JWT, refresh) | ✅ |
| 2 | Workspace management + multi-tenancy | ✅ |
| 3 | Zoho CRM integration | ✅ |
| 4 | WhatsApp + Meta webhook integration | ✅ |
| 5 | Automation engine (flows, versions, execution) | ✅ |
| 6 | Prompt studio (configs, versions, test chat) | ✅ |
| 7 | Email system (SendGrid, SMTP, console, outbox) | ✅ |
| 8 | Dispatch queue + inbox + human takeover | ✅ |
| 9 | Analytics + diagnostics | ✅ |
| 10 | Email verification + verification policy | ✅ |
| 11 | OAuth (Google), RBAC groundwork | ✅ |
| 12 | Module system (feature flags per workspace) | ✅ |
| 13 | Admin control plane (SuperAdmin portal, RBAC, impersonation) | ✅ |
| 14+15 | Commercial entitlements + agency reseller model | ✅ |
| 17 | Enterprise Audit Logging Framework | ✅ |
| 18 | High-Volume Runtime Event Trail | ✅ |
| 19+20 | Catalog Standardization + Prompt Studio KB v2 + Dynamic Lead Qualification | ✅ |
| 21 | Settings Center + Data-Driven Dropdowns | ✅ |
| 27 | Automation Builder v2 + Template Catalog Foundation | ✅ |
| **28** | **Next mission** | **Next** |

---

## Running the Project

### Backend tests
```bash
# MUST run from backend/ directory
cd backend
DATABASE_URL="sqlite+aiosqlite:///./test.db" \
REDIS_URL="redis://localhost:6379/0" \
JWT_SECRET="test_jwt_secret_ci_only" \
ENCRYPTION_KEY_FERNET="ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=" \
python -m pytest tests/ -v
# Expected: 57+ passed (full suite ~3 min with fresh test.db)
```

### Required env vars (no defaults)
`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ENCRYPTION_KEY_FERNET`

### Makefile shortcuts
```bash
make test        # run backend tests
make dev         # start backend dev server
```

### HuggingFace deployment
- Auto-deploys on push to `hf` remote
- Persistent DB at `/data/leadpilot.db` (must enable Persistent Storage in HF Space Settings)
- Admin URL: `https://leadpilot.ashrafkassem.com/admin/login`
- Admin credentials: `admin@leadpilot.io` / `LeadPilot@password123` (self-healed by seed.py)

---

## Critical Architecture

### Auth (Single JWT)
- All routes (product + admin) use `get_current_user` from `app.api.deps` — signed with `JWT_SECRET`
- Admin routes (`admin_auth.py`) check `user.is_superadmin` after standard JWT auth
- Admin token stored in `localStorage["leadpilot_admin_token"]` on the frontend (separate from product `"leadpilot_token"`)

### ResponseEnvelope Contract
ALL endpoints return:
```json
{"success": bool, "data": Any|null, "error": str|null}
```
via `wrap_data()` / `wrap_error()` from `app.schemas.envelope`.
- `wrap_error()` takes **only one arg**: `message: str` — no `code=` kwarg.

### Module System
- Global modules in `SystemModuleConfig` table
- Per-workspace overrides in `WorkspaceModuleOverride` table
- `check_module_enabled(module_name, db, workspace_id=None)` in `app.core.modules`
- Cache key: plain `module_name` (global) or `f"{module_name}:{workspace_id}"` (workspace)
- Constants: `MODULE_ADMIN_PORTAL`, `MODULE_SUPPORT_IMPERSONATION`, etc.

### Email Task Signature
```python
send_email_task_v2.delay(str(outbox.id))  # single UUID arg
# Mock path: @patch("app.workers.email_tasks.send_email_task_v2.delay")
```

### SQLAlchemy NULL Checks — Critical Gotcha
**Never use `Column is None` in `.where()` clauses** — Python identity check, always `False`.
Always use `Column.is_(None)` for SQL `IS NULL`. This was a ruff E711 regression we fixed.

### ORM → Pydantic
SQLModel ORM objects need `ConfigDict(from_attributes=True)` on Pydantic response models.

---

## Key File Paths

| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app entrypoint, middleware, exception handlers |
| `backend/app/api/deps.py` | Auth dependencies (`get_current_user`) |
| `backend/app/api/v1/admin.py` | Admin action endpoints |
| `backend/app/api/v1/admin_auth.py` | Admin login/me (uses `get_current_user` + superadmin check) |
| `backend/app/api/v1/auth.py` | Product auth (signup, login, verify, reset) |
| `backend/app/api/v1/automations.py` | Automation builder CRUD + execution |
| `backend/app/api/v1/templates.py` | Template catalog endpoints |
| `backend/app/models/models.py` | All models (User, Workspace, AdminUser, AdminRole, etc.) |
| `backend/app/core/modules.py` | Module cache + `check_module_enabled()` |
| `backend/app/core/audit.py` | `redact_metadata()` for audit log |
| `backend/app/core/seed.py` | Self-healing superadmin seeding on startup |
| `backend/app/core/security.py` | `create_access_token()`, `verify_password()` |
| `backend/app/workers/email_tasks.py` | `send_email_task_v2` Celery task |
| `backend/tests/conftest.py` | Test fixtures (`db_session`, `async_client`) |
| `backend/alembic/versions/` | DB migrations |
| `frontend/src/lib/auth.ts` | Product JWT storage (`localStorage["leadpilot_token"]`) |
| `frontend/src/lib/admin-auth.ts` | Admin JWT storage (`localStorage["leadpilot_admin_token"]`) |
| `frontend/src/lib/admin-api.ts` | Standalone admin API client |
| `frontend/src/lib/api.ts` | Product API client |
| `frontend/src/app/(admin)/layout.tsx` | Protected admin shell with AdminContext |
| `start.sh` | Docker entrypoint: DB migration → seed → start services |
| `Dockerfile` | Multi-stage: python:3.11-slim-bookworm + node:20-bookworm-slim |
| `nginx.conf` | Reverse proxy: /api → backend:8000, / → frontend:3000 |

---

## Test Status (as of 2026-02-25)

- **57 tests total, 57 pass** on a fresh `test.db`
- **Known flaky (pre-existing, not regressions):** `test_worker_crash_stuck_processing_recovery`
  and `test_idempotency_same_token_and_new_token` — fail in full suite due to SQLAlchemy
  transaction state leak from earlier tests; pass when run in isolation.
- **Always delete `test.db` before a fresh suite run** to avoid "database is locked" cascades.

---

## Admin Portal (Mission 13 Summary)

### Backend
- `AdminUser` table — separate from product `User`, has RBAC via `AdminRole`/`AdminPermission`
- `WorkspaceModuleOverride` — per-workspace feature flag overrides
- `AdminAuditLog` — all admin actions logged with secret field redaction
- Impersonation: 3 gates — module enabled + RBAC permission + 30-min token TTL

### Frontend Admin Pages
`/admin/login`, `/admin`, `/admin/users`, `/admin/modules`, `/admin/workspaces`,
`/admin/workspaces/[id]`, `/admin/email-logs`, `/admin/dispatch`, `/admin/automations`,
`/admin/audit-log`, `/admin/prompt-configs`, `/admin/zoho-health`, `/admin/monitoring`

---

## CI/CD Notes

- **GitHub Actions** (`.github/workflows/ci.yml`): runs `ruff check .` + `pytest` on push/PR to `main`
- **Ruff config** in `backend/pyproject.toml` — all 187 violations were fixed; CI passes
- **Critical ruff rule:** E711 auto-fix changes `== None` to `is None` in SQLAlchemy queries
  which BREAKS them. If ruff is upgraded, re-check for this regression.

---

## ADK Architecture (Missions M-A through M-E)

- Entry point: `app/core/adk/runner.py` → `run_for_contact()` (get-or-create session pattern)
- Agent graph: `app/core/adk/agents/orchestrator.py` → `build_orchestrator()` → routes to
  QualificationAgent, CRMAgent, ReplyAgent, HandoverAgent via `AgentTool`
- Session service: `app/core/adk/session_service.py` → `LeadPilotSessionService`
- Callbacks (M-E): `app/core/adk/callbacks.py` → `LeadPilotCallbackHandler` → `RuntimeEventLog`
  - Fires on every agent start/end, LLM request/response, tool start/end
  - Attached to orchestrator agent in `runner.py` after `build_orchestrator()`
- Builder: `FlowVersion.adk_pipeline_config` stores ADK pipeline config (M-D)
- Execution trace: `GET /api/v1/admin/executions/{id}/trace` → ordered `RuntimeEventLog` rows
- Event types documented in `docs/missions/event-types.md`
- Metrics: `MetricsService.gauge()` added (M-E); agent metrics exposed at `GET /admin/metrics`
- Tests: 360 total (8 new M-E tests: `test_callbacks.py` + `test_e2e_agent_flow.py`)

### Mission Status
| Mission | Description | Status |
|---|---|---|
| M-A | ADK Core Integration | ✅ |
| M-B | Multi-Agent Orchestration | ✅ |
| M-C | Session & Memory | ✅ |
| M-D | Flow Builder Revamp | ✅ |
| M-E | Observability & Tests | ✅ |

---

## Docs Location

Project docs (mission notes): `docs/missions/`
