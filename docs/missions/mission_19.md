# Mission 19 — Data Flow Integrity & Catalog Standardization Gate

## Summary

Mission 19 introduces a backend catalog registry and API layer that serves as the single source of truth for all enum-based reference data in LeadPilot V2. The frontend was swept to replace 11+ hardcoded arrays with a `useCatalog()` hook that fetches from the new `/api/v1/catalog/*` endpoints.

**Result:** Adding a new integration provider, automation step type, or status enum now requires only a backend change to `catalog_registry.py` — the frontend picks it up automatically.

## Catalog Endpoints

| # | Endpoint | Source | Auth |
|---|---|---|---|
| 1 | `GET /api/v1/catalog/plans` | DB: `Plan` + `PlanEntitlement` | None |
| 2 | `GET /api/v1/catalog/tiers` | Alias for /plans | None |
| 3 | `GET /api/v1/catalog/modules` | DB: `SystemModuleConfig` + registry labels | None |
| 4 | `GET /api/v1/catalog/workspace-roles` | Registry | None |
| 5 | `GET /api/v1/catalog/admin-roles` | Registry | None |
| 6 | `GET /api/v1/catalog/integration-providers` | Registry | None |
| 7 | `GET /api/v1/catalog/automation-node-types` | Registry | None |
| 8 | `GET /api/v1/catalog/automation-trigger-types` | Registry | None |
| 9 | `GET /api/v1/catalog/conversation-statuses` | Registry | None |
| 10 | `GET /api/v1/catalog/message-delivery-statuses` | Registry | None |

All endpoints return `ResponseEnvelope` with `Cache-Control: public, max-age=60`. No authentication required — these are public reference data.

## Backend Changes

### New Files
- **`backend/app/core/catalog_registry.py`** — Canonical enum registry. Exports typed lists (`INTEGRATION_PROVIDERS`, `AUTOMATION_NODE_TYPES`, etc.) and validation sets (`VALID_PROVIDERS`, `VALID_NODE_TYPES`, `VALID_TRIGGER_TYPES`).
- **`backend/app/api/v1/catalog.py`** — 10 GET-only endpoints using factory pattern for static endpoints.
- **`backend/tests/test_catalog.py`** — 12 test cases covering all endpoints, structure validation, cache headers, and 404 handling.

### Modified Files
- **`backend/main.py`** — Registered catalog router, added `/catalog` to maintenance mode exempt prefixes.
- **`backend/app/api/v1/integrations.py`** — Replaced hardcoded `["zoho", "whatsapp", "meta"]` with `VALID_PROVIDERS` from registry.
- **`backend/app/api/v1/automations.py`** — Added server-side validation of step types and trigger types against registry.
- **`backend/tests/test_automation.py`** — Updated test trigger type from `WEBHOOK` to `MESSAGE_INBOUND` (now validated).

## Frontend Changes

### New Files
- **`frontend/src/lib/catalog.ts`** — `useCatalog<T>(key)` hook with 60s in-memory cache, `catalogLabel()` helper.

### Hardcoded Sweep Report

| Page | What was removed | What replaced it |
|---|---|---|
| `/integrations` | `PROVIDER_METADATA` object (name, description, fields) | `useCatalog("integration-providers")` |
| `/inbox` | Hardcoded `<option>` status elements + switch-case labels | `useCatalog("conversation-statuses")` + `catalogLabel()` |
| `/automations/new` | Hardcoded trigger cards + step type buttons | `useCatalog("automation-node-types")` + `useCatalog("automation-trigger-types")` |
| `/admin/dispatch` | `STATUS_OPTIONS` array | `useCatalog("message-delivery-statuses")` |
| `/dispatch` | Hardcoded status labels in `getStatusBadge()` | `catalogLabel(deliveryStatuses, ...)` |
| `/plans` (marketing) | Hardcoded waitlist `<select>` options | `useCatalog<PlanCatalogEntry[]>("plans")` |
| `/admin/email-logs` | _(kept as-is)_ | Added traceability comment to registry |
| `/lib/admin-api.ts` | _(kept as-is)_ | Added deprecation comment on `MODULE_LABELS` |

### Intentionally Unchanged
- **Marketing tier cards** (`/plans` page) — Rich marketing copy (features, pricing, CTAs) is a presentation concern, not catalog data.
- **Admin email log filters** — Admin-internal statuses, different enum from message delivery. Kept as local constants with traceability comment.
- **Team page** — Static placeholder with no backend wiring.

## Test Results

```
Backend:  105 passed, 0 failed (16.60s)
Frontend: npm run build — 48 pages, 0 errors
```

## Key Decisions

1. **No auth on catalog** — Public reference data, safe with 60s cache header.
2. **No DB migration** — Reads existing Plan/Module tables + in-memory registry.
3. **Factory pattern** — 7 identical static handlers collapsed to 1 factory function.
4. **Icons stay frontend-side** — `icon_hint` in registry maps to Lucide components via local mapping.
5. **Maintenance mode exempt** — Catalog is reference data, available even during maintenance.
