# Mission 19 — Data Flow Map

Maps every dynamic UI element to its API endpoint, service layer, and database source.

---

## Plans & Billing

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/plans` waitlist dropdown | `WaitlistForm` | `GET /api/v1/catalog/plans` | catalog router | `plan` + `plan_entitlement` |
| `/admin/plans` list | Admin Plans page | `GET /api/v1/admin/plans` | admin router | `plan` |
| `/admin/plans/:id` detail | Plan detail page | `GET /api/v1/admin/plans/:id` | admin router | `plan` + `plan_entitlement` |
| `/admin/workspaces/:id` plan badge | Workspace detail | `GET /api/v1/admin/workspaces/:id/plan` | admin router | `workspace_plan_assignment` |

## Modules

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/admin/modules` toggle list | Modules page | `GET /api/v1/admin/modules` | admin router | `system_module_config` |
| `/admin/workspaces/:id` module overrides | Workspace detail | `GET /api/v1/admin/workspaces/:id/modules` | admin router | `workspace_module_override` |
| Catalog reference | Any page via `useCatalog` | `GET /api/v1/catalog/modules` | catalog router | `system_module_config` + registry labels |

## Roles

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/team` role badges | Team page (placeholder) | `GET /api/v1/catalog/workspace-roles` | catalog router | Registry (enum) |
| `/admin/agencies` role display | Agency detail | `GET /api/v1/catalog/admin-roles` | catalog router | Registry (enum) |
| Member invite role picker | Workspace settings | `GET /api/v1/catalog/workspace-roles` | catalog router | Registry (enum) |

## Integrations

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/integrations` provider cards | Integrations page | `GET /api/v1/catalog/integration-providers` | catalog router | Registry |
| `/integrations` connected list | Integrations page | `GET /api/v1/integrations` | integrations router | `integration` |
| `/integrations` connect modal fields | Dynamic form | `GET /api/v1/catalog/integration-providers` | catalog router | Registry (`.fields`) |
| `/integrations` provider validation | Backend | `POST /api/v1/integrations/:provider/connect` | integrations router | `VALID_PROVIDERS` set |

## Automations

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/automations/new` trigger cards | Builder wizard | `GET /api/v1/catalog/automation-trigger-types` | catalog router | Registry |
| `/automations/new` step type buttons | Builder wizard | `GET /api/v1/catalog/automation-node-types` | catalog router | Registry |
| `/automations/new` step labels | Review panel | `GET /api/v1/catalog/automation-node-types` | catalog router | Registry |
| `/automations` flow list | Automations page | `GET /api/v1/automations` | automations router | `flow` |
| Backend step validation | `create_from_builder` | — | `VALID_NODE_TYPES` set | Registry |
| Backend trigger validation | `create_from_builder` | — | `VALID_TRIGGER_TYPES` set | Registry |

## Inbox / Conversations

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/inbox` status filter dropdown | Inbox page | `GET /api/v1/catalog/conversation-statuses` | catalog router | Registry (enum) |
| `/inbox` status badges | `StatusBadge` component | `GET /api/v1/catalog/conversation-statuses` | catalog router | Registry (enum) |
| `/inbox` conversation list | Inbox page | `GET /api/v1/inbox/conversations` | inbox router | `conversation` |
| `/inbox` messages | Message panel | `GET /api/v1/inbox/conversations/:id/messages` | inbox router | `message` |

## Dispatch / Message Delivery

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/admin/dispatch` status filter | Admin dispatch page | `GET /api/v1/catalog/message-delivery-statuses` | catalog router | Registry (enum) |
| `/admin/dispatch` message list | Admin dispatch page | `GET /api/v1/admin/dispatch` | admin router | `outbound_message` |
| `/dispatch` status badges | Dashboard dispatch | `GET /api/v1/catalog/message-delivery-statuses` | catalog router | Registry (enum) |
| `/dispatch` message queue | Dashboard dispatch | `GET /api/v1/dispatch/queue` | dispatch router | `outbound_message` |

## Email Engine

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/admin/email-logs` status filter | Email logs page | Local constants (registry-traced) | — | — |
| `/admin/email-logs` type filter | Email logs page | Local constants (registry-traced) | — | — |
| `/admin/email-logs` log list | Email logs page | `GET /api/v1/admin/email-logs` | admin router | `email_outbox` |
| `/admin/email-logs` retry action | Retry button | `POST /api/v1/admin/email-logs/:id/retry` | admin router | `email_outbox` |

## Analytics & Dashboard

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/dashboard` stats cards | Dashboard page | `GET /api/v1/analytics/summary` | analytics router | Aggregated queries |
| `/dashboard` time series | Charts | `GET /api/v1/analytics/time-series` | analytics router | Aggregated queries |

## Audit & Runtime Events

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/admin/audit-log` list | Audit log page | `GET /api/v1/admin/audit-log` | admin router | `audit_log` |
| `/admin/audit-log` detail | Detail drawer | `GET /api/v1/admin/audit-log/:id` | admin router | `audit_log` |
| `/admin/runtime-events` list | Runtime events page | `GET /api/v1/admin/runtime-events` | admin router | `runtime_event` |
| `/admin/runtime-events` detail | Detail drawer | `GET /api/v1/admin/runtime-events/:id` | admin router | `runtime_event` |

## Settings

| UI Location | Component | API Endpoint | Service | DB Table |
|---|---|---|---|---|
| `/settings` workspace name | Settings page | `GET /api/v1/workspaces/current` | workspaces router | `workspace` |
| `/admin/system-settings` | System settings | `GET /api/v1/admin/system-settings` | admin router | `system_setting` |

---

## Registry → Validation Cross-Reference

| Registry Constant | Used By (Validation) | Used By (Catalog Endpoint) |
|---|---|---|
| `VALID_PROVIDERS` | `integrations.py` line 46 | `/catalog/integration-providers` |
| `VALID_NODE_TYPES` | `automations.py` line 56 | `/catalog/automation-node-types` |
| `VALID_TRIGGER_TYPES` | `automations.py` line 58 | `/catalog/automation-trigger-types` |
| `CONVERSATION_STATUSES` | — (enum-enforced in DB) | `/catalog/conversation-statuses` |
| `MESSAGE_DELIVERY_STATUSES` | — (enum-enforced in DB) | `/catalog/message-delivery-statuses` |
| `WORKSPACE_ROLES` | — (enum-enforced in DB) | `/catalog/workspace-roles` |
| `AGENCY_ROLES` | — (enum-enforced in DB) | `/catalog/admin-roles` |
| `MODULE_LABELS` | — (display only) | `/catalog/modules` |
