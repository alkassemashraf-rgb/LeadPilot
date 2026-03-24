# ADK Migration Missions

Google ADK migration plan — replacing the sequential MVP runtime with a
multi-agent autonomous execution engine.

## Mission Index

| Mission | Name | Status | Key Outcome |
|---|---|---|---|
| [M-A](./M-A_adk-core-integration.md) | ADK Core Integration | Pending | Replace `runtime.py` + `core/ai.py` with ADK LlmAgent + tools |
| [M-B](./M-B_multi-agent-orchestration.md) | Multi-Agent Orchestration | Pending | OrchestratorAgent → Qualification / CRM / Reply / Handover agents |
| [M-C](./M-C_session-and-memory.md) | Session & Memory | Pending | Persistent ADK sessions backed by DB — stateful multi-turn conversations |
| [M-D](./M-D_flow-builder-revamp.md) | Flow Builder Revamp | Pending | Unlock CONDITION + WAIT_DELAY, add PARALLEL + AGENT_HANDOFF nodes |
| [M-E](./M-E_observability-and-tests.md) | Observability & Tests | Pending | ADK callbacks → RuntimeEventLog, admin trace view, full test suite |

## Execution Order

M-A → M-B → M-C → M-D → M-E

Each mission must pass all its success criteria and tests before starting the next.
M-A is the gate mission — if ADK proves unstable after M-A, re-evaluate before M-B.

## What Does NOT Change

The following are preserved across all missions:
- All FastAPI routes and ResponseEnvelope contract
- All DB models (only additions, no removals)
- Auth / JWT / admin portal
- `dispatch_service.py` and WhatsApp/Meta adapters
- `prompt_compiler.py` (feeds into ADK system_instruction)
- Zoho adapter (wrapped as ADK tool)
- Celery + Redis infrastructure
- All 327 pre-existing tests (must remain green)

## Competitive Context

These missions directly address Manychat's structural ceiling:
- Manychat: fixed flowcharts, template-driven, no AI autonomy
- LeadPilot after M-A→M-E: autonomous agents that decide, qualify, sync CRM,
  and escalate — without the user scripting every step
