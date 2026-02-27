# Mission 21 — Pre-Mission Baseline

Captured before any Mission 21 changes.

## Hardcoded Dropdowns

| File | Values |
|---|---|
| `settings/page.tsx` | Timezones (6 hardcoded), Languages (6), AI Models (3) |
| `automations/new/page.tsx` | TRIGGER_CARDS array (3 hardcoded triggers) |
| `zoho/mapping/page.tsx` | LEADPILOT_FIELDS (6 contact fields), Dedupe strategies (3), Fallback Zoho fields |
| `admin/system-settings/page.tsx` | Plan tiers: free, starter, growth, enterprise |
| `admin/runtime-events/page.tsx` | Event sources (6), Event outcomes (3) |
| `logs/page.tsx` | Action filter (11 types), Outcome filter (2) |

## User Profile

- `GET /auth/me` existed — returns user data
- `PATCH /auth/me` did NOT exist — no way to update profile
- No `ProfileUpdate` schema

## Sidebar

- Fetched `/auth/me` but showed `userName || "Loading..."` with no initials fallback
- No role display

## Settings Page

- Workspace settings only (5 tabs: General, Messaging, AI, Automation, Notifications)
- No Profile section
- All dropdowns hardcoded with inline arrays

## Catalog Registry (Mission 19)

8 existing catalogs:
- integration-providers, automation-node-types, automation-trigger-types
- conversation-statuses, message-delivery-statuses
- workspace-roles, admin-roles
- plans, modules (DB-backed)

No lookup catalogs for: timezones, languages, AI models, dedupe strategies, event sources, event outcomes, audit actions, contact fields.

## Frontend Data Layer

- `useCatalog()` hook existed in `catalog.ts` for individual catalog fetching
- No `LookupsProvider` — no bulk preload of lookups
- `fetchCatalog` was a private function (not exported)

## Test Count

118 tests across 20 files, all passing.
