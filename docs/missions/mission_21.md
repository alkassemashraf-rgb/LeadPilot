# Mission 21 — Settings Center + Data-Driven Dropdowns

## Summary

Mission 21 eliminates all hardcoded frontend dropdowns by extending the catalog registry, adds user profile management, and restructures the settings page with a Profile tab.

1. **8 new catalog endpoints** — timezones, languages, AI models, dedupe strategies, event sources, event outcomes, audit actions, contact fields — all served from the catalog registry.
2. **LookupsProvider** — single React context preloading all lookups on mount via `Promise.all`, consumed by `useLookups()` hook.
3. **Profile management** — `PATCH /auth/me` lets users update their name. Settings page gains a Profile section.
4. **Sidebar shows real user data** — fetches `/auth/me` on mount, displays actual name + computed initials.
5. **Every hardcoded dropdown replaced** — 13 occurrences across 7 files now use catalog data.

## What Changed

### Backend

| File | Change |
|---|---|
| `app/schemas/user.py` | Added `ProfileUpdate` schema |
| `app/api/v1/auth.py` | Added `PATCH /auth/me` endpoint with audit logging |
| `app/core/catalog_registry.py` | Added 8 new catalog constants (TIMEZONES, LANGUAGES, AI_MODELS, DEDUPE_STRATEGIES, EVENT_SOURCES, EVENT_OUTCOMES, AUDIT_ACTIONS, CONTACT_FIELDS) |
| `app/api/v1/catalog.py` | Registered 8 new static endpoints |

### Frontend

| File | Change |
|---|---|
| `src/lib/catalog.ts` | Extended `CatalogKey` type with 8 new keys; exported `fetchCatalog` |
| `src/lib/lookups.tsx` | **NEW** — LookupsProvider context + useLookups hook |
| `src/components/AppShell.tsx` | Wrapped with `<LookupsProvider>` |
| `src/app/(dashboard)/settings/page.tsx` | Added Profile section; replaced 3 hardcoded dropdowns with `CatalogSelectField` |
| `src/components/Sidebar.tsx` | Real user name from `/auth/me`, dynamic initials |
| `src/app/(dashboard)/logs/page.tsx` | Action + outcome filters from catalog |
| `src/app/(dashboard)/integrations/zoho/mapping/page.tsx` | Contact fields + dedupe strategies from catalog |
| `src/app/(admin)/admin/runtime-events/page.tsx` | Source + outcome filters from catalog |
| `src/app/(admin)/admin/system-settings/page.tsx` | Plan tier select from `/catalog/plans` |

### Tests

| File | Tests |
|---|---|
| `tests/test_profile.py` | 6 tests — update name, whitespace strip, empty rejected, no-op body, GET reflects PATCH, unauthenticated |
| `tests/test_catalog_lookups.py` | 19 tests — 8 endpoints return data with key/label, 8 have Cache-Control header, contact fields have required flag |

## New API Endpoints

| Method | Path | Description |
|---|---|---|
| PATCH | `/api/v1/auth/me` | Update authenticated user's profile (full_name) |
| GET | `/api/v1/catalog/timezones` | List of common timezones |
| GET | `/api/v1/catalog/languages` | Supported languages |
| GET | `/api/v1/catalog/ai-models` | Available AI models |
| GET | `/api/v1/catalog/dedupe-strategies` | CRM dedupe strategies |
| GET | `/api/v1/catalog/event-sources` | Runtime event sources |
| GET | `/api/v1/catalog/event-outcomes` | Event outcome types |
| GET | `/api/v1/catalog/audit-actions` | Audit log action types |
| GET | `/api/v1/catalog/contact-fields` | Standard contact fields |

## Architecture: LookupsProvider

```
<LookupsProvider>           ← wraps AppShell (dashboard layout)
  │
  ├── Promise.all on mount
  │     ├── fetchCatalog("timezones")
  │     ├── fetchCatalog("languages")
  │     ├── fetchCatalog("ai-models")
  │     ├── fetchCatalog("dedupe-strategies")
  │     ├── fetchCatalog("event-sources")
  │     ├── fetchCatalog("event-outcomes")
  │     ├── fetchCatalog("audit-actions")
  │     ├── fetchCatalog("contact-fields")
  │     ├── fetchCatalog("automation-trigger-types")
  │     └── fetchCatalog("automation-node-types")
  │
  └── useLookups() → { timezones, languages, aiModels, ... loading }
```

Admin pages (separate layout) use `useCatalog()` hook directly.

## Hardcoded Dropdowns Replaced

| File | Before | After |
|---|---|---|
| `settings/page.tsx` | 6 inline timezone options | `lookups.timezones` |
| `settings/page.tsx` | 6 inline language options | `lookups.languages` |
| `settings/page.tsx` | 3 inline AI model options | `lookups.aiModels` |
| `logs/page.tsx` | 11 inline action options | `lookups.auditActions` |
| `logs/page.tsx` | 2 inline outcome options | `lookups.eventOutcomes` |
| `zoho/mapping/page.tsx` | 6 hardcoded LEADPILOT_FIELDS | `lookups.contactFields` |
| `zoho/mapping/page.tsx` | 3 inline dedupe strategies | `lookups.dedupeStrategies` |
| `admin/runtime-events/page.tsx` | 6 inline source options | `useCatalog("event-sources")` |
| `admin/runtime-events/page.tsx` | 3 inline outcome options | `useCatalog("event-outcomes")` |
| `admin/system-settings/page.tsx` | 4 hardcoded plan tiers | `useCatalog("plans")` |

## How to Test

1. **Backend tests**: `cd backend && rm -f test.db && python3 -m pytest tests/ -v`
2. **Frontend build**: `cd frontend && npm run build`
3. **Manual — Profile**: Settings → Profile tab → edit name → save → sidebar updates
4. **Manual — Dropdowns**: Settings → General → timezone dropdown shows catalog values
5. **Manual — Logs**: Activity Logs → action filter populated from catalog
6. **Manual — API**: `curl /api/v1/catalog/timezones` returns list with key/label
7. **Manual — Profile API**: `curl -X PATCH /api/v1/auth/me -d '{"full_name":"Test"}' -H 'Authorization: Bearer ...'`
