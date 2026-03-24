# RuntimeEventLog Event Type Taxonomy

All events stored in `RuntimeEventLog.event_type`. Sources are logged in
`RuntimeEventLog.source`.

---

## Agent Lifecycle (`source: adk`)

| Event Type | When |
|---|---|
| `agent.{name}.started` | Before an agent (orchestrator or sub-agent) begins processing |
| `agent.{name}.completed` | After an agent finishes (includes `duration_ms`) |
| `agent.llm_request` | Before a Gemini API call (model name, message/tool counts) |
| `agent.llm_response` | After Gemini responds (token counts, finish_reason) |
| `agent.error` | On any exception inside the agent (phase: llm or tool) |

Agent names: `orchestrator`, `qualification_agent`, `crm_agent`, `reply_agent`,
`handover_agent`.

---

## Tool Lifecycle (`source: adk`)

| Event Type | When |
|---|---|
| `tool.send_reply.started` | Before `send_reply` tool executes |
| `tool.send_reply.completed` | After `send_reply` returns |
| `tool.upsert_zoho_lead.started` | Before Zoho sync tool |
| `tool.upsert_zoho_lead.completed` | After Zoho sync returns |
| `tool.escalate_to_human.started` | Before human escalation |
| `tool.escalate_to_human.completed` | After escalation |
| `tool.tag_contact.started` | Before contact tagging |
| `tool.tag_contact.completed` | After tagging |

---

## Runner Lifecycle (`source: adk_runner`)

| Event Type | When |
|---|---|
| `runtime.adk_turn_started` | Beginning of `run_for_contact()` |
| `runtime.adk_turn_completed` | Successful completion of the runner loop (includes `duration_ms`) |
| `runtime.step_completed` | Each tool call seen in the runner event stream |

---

## Webhook Ingestion (`source: webhook`)

| Event Type | When |
|---|---|
| `webhook.received` | Raw webhook POST received |
| `webhook.queued` | Message queued to Celery |
| `webhook.processing_started` | Worker picks up the message |
| `webhook.processing_completed` | Message processed |
| `webhook.processing_failed` | Processing errored |
| `webhook.signature_invalid` | Webhook signature check failed |
| `webhook.workspace_not_found` | No workspace matched the webhook |

---

## Runtime / Execution (`source: adk_runner`, `runtime`)

| Event Type | When |
|---|---|
| `runtime.execution_created` | New `ExecutionInstance` row inserted |
| `runtime.human_escalation` | `escalate_to_human` tool called (source: adk) |

---

## Dispatch (`source: dispatch`)

| Event Type | When |
|---|---|
| `dispatch.attempt_started` | Outbound send attempt begins |
| `dispatch.attempt_succeeded` | Message delivered |
| `dispatch.attempt_failed` | Send failed (will retry) |
| `dispatch.dead_lettered` | Exceeded max retries |

---

## Zoho CRM (`source: zoho`)

| Event Type | When |
|---|---|
| `zoho.sync_started` | CRM upsert begins |
| `zoho.sync_succeeded` | Lead created/updated in Zoho |
| `zoho.sync_failed` | Zoho API returned error |

---

## Inbox / Manual (`source: inbox`)

| Event Type | When |
|---|---|
| `inbox.manual_reply` | Agent sends reply via inbox UI |
| `inbox.status_changed` | Conversation status changed manually |
