# Mission M-E — Observability & Tests

## Goal
Wire ADK's callback system into the existing runtime event logging infrastructure,
port all 327 existing tests to cover ADK-backed execution paths, add comprehensive
multi-agent scenario tests, and expose agent execution visibility in the admin portal.
After this mission, the engineering team can fully observe, debug, and monitor the
agent graph in production — with zero blind spots.

## What This Unlocks
- Full agent execution trace in `RuntimeEventLog` (every tool call, agent delegation, decision)
- Admin portal "Execution Trace" view — see exactly what each agent did, in what order, why
- Per-workspace agent performance metrics (response time, tool call frequency, qualification rate)
- Failure diagnosis without logs — admins see the full agent reasoning chain
- Test suite fully validates multi-agent behavior end-to-end

## Prerequisites
- Missions M-A, M-B, M-C, M-D all complete
- Existing `RuntimeEventLog` + `log_event()` infrastructure (Mission 18) operational
- Admin portal operational (Mission 13)
- 327 tests passing

---

## Part 1 — ADK Callback Integration

### ADK Callback System

ADK provides callbacks that fire at every significant agent lifecycle moment:
- `on_agent_start` — when an agent (including sub-agents) begins processing
- `on_agent_end` — when an agent finishes
- `on_tool_start` — before a tool function is called
- `on_tool_end` — after a tool returns (with the result)
- `on_llm_request` — before Gemini API call (with full prompt)
- `on_llm_response` — after Gemini responds (with generated text + token counts)
- `on_error` — on any exception inside the agent

### `backend/app/core/adk/callbacks.py`

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.tool_context import ToolContext
from app.services.runtime_event_service import log_event
import time

class LeadPilotCallbackHandler:
    """
    Wires ADK lifecycle events to the existing RuntimeEventLog system.
    Instantiated per-run, holds workspace_id and execution_instance_id for context.
    """

    def __init__(self, workspace_id: str, instance_id: str, db_session):
        self.workspace_id = workspace_id
        self.instance_id = instance_id
        self.session = db_session
        self._agent_start_times: dict[str, float] = {}
        self._tool_start_times: dict[str, float] = {}

    async def on_agent_start(self, callback_context: CallbackContext, agent_name: str) -> None:
        self._agent_start_times[agent_name] = time.time()
        await log_event(
            self.session,
            event_type=f"agent.{agent_name}.started",
            source="adk",
            workspace_id=self.workspace_id,
            related_ids={"execution_instance_id": self.instance_id},
            payload={"agent_name": agent_name},
        )

    async def on_agent_end(
        self, callback_context: CallbackContext, agent_name: str, output
    ) -> None:
        duration_ms = int((time.time() - self._agent_start_times.get(agent_name, time.time())) * 1000)
        await log_event(
            self.session,
            event_type=f"agent.{agent_name}.completed",
            source="adk",
            workspace_id=self.workspace_id,
            duration_ms=duration_ms,
            related_ids={"execution_instance_id": self.instance_id},
            payload={"agent_name": agent_name, "output_type": type(output).__name__},
        )

    async def on_tool_start(self, tool_context: ToolContext, tool_name: str, args: dict) -> None:
        key = f"{tool_name}_{time.time()}"
        self._tool_start_times[key] = time.time()
        await log_event(
            self.session,
            event_type=f"tool.{tool_name}.started",
            source="adk",
            workspace_id=self.workspace_id,
            related_ids={"execution_instance_id": self.instance_id},
            payload={"tool_name": tool_name, "args": _redact_sensitive(args)},
        )

    async def on_tool_end(
        self, tool_context: ToolContext, tool_name: str, args: dict, result: dict
    ) -> None:
        await log_event(
            self.session,
            event_type=f"tool.{tool_name}.completed",
            source="adk",
            workspace_id=self.workspace_id,
            related_ids={"execution_instance_id": self.instance_id},
            payload={
                "tool_name": tool_name,
                "result_keys": list(result.keys()) if isinstance(result, dict) else None,
            },
        )

    async def on_llm_request(
        self, callback_context: CallbackContext, request: LlmRequest
    ) -> None:
        # Log token estimate (not full prompt — too large and may contain PII)
        await log_event(
            self.session,
            event_type="agent.llm_request",
            source="adk",
            workspace_id=self.workspace_id,
            related_ids={"execution_instance_id": self.instance_id},
            payload={
                "model": request.model,
                "message_count": len(request.messages or []),
                "tool_count": len(request.tools or []),
            },
        )

    async def on_llm_response(
        self, callback_context: CallbackContext, response: LlmResponse
    ) -> None:
        await log_event(
            self.session,
            event_type="agent.llm_response",
            source="adk",
            workspace_id=self.workspace_id,
            related_ids={"execution_instance_id": self.instance_id},
            payload={
                "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None,
                "tool_calls": [c.name for c in (response.candidates[0].content.parts or [])
                               if hasattr(c, "function_call")] if response.candidates else [],
            },
        )

    async def on_error(self, callback_context: CallbackContext, error: Exception) -> None:
        await log_event(
            self.session,
            event_type="agent.error",
            source="adk",
            workspace_id=self.workspace_id,
            outcome="failure",
            error_message=str(error),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"error_type": type(error).__name__},
        )


def _redact_sensitive(args: dict) -> dict:
    """Remove sensitive fields from tool args before logging."""
    SENSITIVE_KEYS = {"access_token", "api_key", "password", "token", "secret"}
    return {k: "***" if k.lower() in SENSITIVE_KEYS else v for k, v in args.items()}
```

### Wire into `runner.py`

```python
from app.core.adk.callbacks import LeadPilotCallbackHandler

async def run_for_contact(...):
    callback_handler = LeadPilotCallbackHandler(
        workspace_id=str(workspace_id),
        instance_id=str(execution_instance.id),
        db_session=session,
    )

    runner = Runner(
        agent=agent,
        app_name="leadpilot",
        session_service=session_service,
        # ADK callback registration (exact API depends on ADK version)
        callbacks=callback_handler,
    )
```

---

## Part 2 — New RuntimeEventLog Event Types

Register all new ADK event types in the existing event taxonomy.
Document in `docs/missions/event-types.md`:

```
# Agent lifecycle
agent.{name}.started
agent.{name}.completed
agent.llm_request
agent.llm_response
agent.error

# Tool lifecycle
tool.send_reply.started / completed
tool.upsert_zoho_lead.started / completed
tool.escalate_to_human.started / completed
tool.tag_contact.started / completed
tool.mark_qualified.started / completed
tool.mark_disqualified.started / completed

# Session
agent_session.created
agent_session.resumed
agent_session.state_updated
```

---

## Part 3 — Admin Portal: Execution Trace View

### Backend: `GET /api/v1/admin/executions/{instance_id}/trace`

Returns all `RuntimeEventLog` rows for a given `ExecutionInstance`, ordered by
`created_at`, formatted as an execution trace.

```python
@router.get("/executions/{instance_id}/trace")
async def get_execution_trace(
    instance_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check_superadmin(current_user)
    events = await db.execute(
        select(RuntimeEventLog)
        .where(RuntimeEventLog.related_ids["execution_instance_id"].as_string() == str(instance_id))
        .order_by(RuntimeEventLog.created_at)
    )
    return wrap_data([...])
```

### Frontend: Admin → Automations → Execution → Trace Tab

Timeline view showing:
```
12:01:00 [webhook]       webhook.processing_started
12:01:00 [runtime]       runtime.execution_created
12:01:01 [adk]           agent.orchestrator.started
12:01:01 [adk]           agent.llm_request (model: gemini-2.0-flash, 3 tools)
12:01:02 [adk]           agent.llm_response (input: 847 tokens, output: 23 tokens)
12:01:02 [adk]           agent.qualification_agent.started
12:01:02 [adk]           tool.send_reply.started ("What's your budget?")
12:01:02 [adk]           tool.send_reply.completed
12:01:03 [adk]           agent.qualification_agent.completed (2.1s)
12:01:03 [adk]           agent.orchestrator.completed (2.3s)
12:01:03 [runtime]       runtime.execution_completed
```

Color-coded by source (webhook=blue, runtime=green, adk=purple, tool=orange, error=red).

---

## Part 4 — Metrics Additions

### `backend/app/services/metrics_service.py`

Add new counters to the existing `MetricsService`:

```python
# Existing
metrics.increment("messages_sent", labels={"platform": "whatsapp"})

# New
metrics.increment("agent.turns_processed")
metrics.increment("agent.tool_calls", labels={"tool": "send_reply"})
metrics.increment("agent.qualifications_completed", labels={"outcome": "qualified"})
metrics.increment("agent.escalations")
metrics.gauge("agent.avg_tokens_per_turn", token_count)
metrics.gauge("agent.avg_turn_duration_ms", duration_ms)
```

### Admin → Monitoring Page

Add "Agent Metrics" section showing:
- Total agent turns (today / 7d / 30d)
- Most called tools (pie chart)
- Qualification funnel (started → qualified → crm synced)
- Average turn duration (p50, p95)
- Gemini token usage (for cost tracking)
- Escalation rate

---

## Part 5 — Test Suite Migration

### Strategy

The 327 existing tests are structured around the old runtime. After M-A through M-D,
the following categories need review:

| Test File | Status | Action |
|---|---|---|
| `test_webhooks.py` | Largely unchanged | Verify webhook ingestion still works |
| `test_automations.py` | Needs update | Add `adk_pipeline_config` assertions on publish |
| `test_dispatch.py` | Unchanged | No change — dispatch service untouched |
| `test_zoho.py` | Unchanged | Zoho adapter untouched |
| `test_auth.py` | Unchanged | Auth untouched |
| `test_admin.py` | Add new tests | Add execution trace endpoint tests |
| `test_runtime.py` (if exists) | Rewrite | Replace old `execute_instance` tests with ADK runner tests |

### Mocking Strategy for ADK in Tests

All ADK tests must use `InMemorySessionService` and mock Gemini responses — no real API calls.

```python
# conftest.py additions

@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API to return a fixed response without API calls."""
    with patch("google.generativeai.GenerativeModel") as mock:
        mock.return_value.generate_content_async.return_value = MockResponse(
            text="I understand. Could you tell me your budget range?"
        )
        yield mock

@pytest.fixture
def adk_test_runner(mock_gemini_response):
    """Creates an ADK runner with InMemorySessionService for testing."""
    from google.adk.sessions import InMemorySessionService
    # Returns a runner factory for tests
    ...
```

### New Test Files

#### `backend/tests/test_adk_runner.py` (M-A)
6 tests — defined in M-A mission doc.

#### `backend/tests/test_multi_agent.py` (M-B)
5 tests — defined in M-B mission doc.

#### `backend/tests/test_session_service.py` (M-C)
6 tests — defined in M-C mission doc.

#### `backend/tests/test_builder_translator_v2.py` (M-D)
6 tests — defined in M-D mission doc.

#### `backend/tests/test_callbacks.py` (M-E)

### Test 1 — Callback logs agent.started event
```
given: ADK runner with LeadPilotCallbackHandler
when: agent starts processing
then: RuntimeEventLog row created with event_type="agent.orchestrator.started"
```

### Test 2 — Callback logs tool.send_reply.completed event
```
given: agent calls send_reply tool
when: tool completes successfully
then: RuntimeEventLog row with event_type="tool.send_reply.completed"
```

### Test 3 — Callback logs agent.error on exception
```
given: Gemini raises exception mid-turn
when: on_error callback fires
then: RuntimeEventLog row with outcome="failure", error_message set
```

### Test 4 — Sensitive args redacted from tool logs
```
given: tool called with args={"access_token": "secret123", "message": "hello"}
when: on_tool_start logs the call
then: logged payload has access_token="***", message="hello"
```

### Test 5 — Execution trace endpoint returns ordered events
```
given: ExecutionInstance with 8 RuntimeEventLog rows
when: GET /api/v1/admin/executions/{id}/trace
then: returns 8 events in chronological order
```

#### `backend/tests/test_e2e_agent_flow.py` — Full End-to-End Scenarios

### E2E Test 1 — Full qualification → CRM → reply flow
```
given: workspace with 3 qualification questions, Zoho connected
simulate:
  - webhook: "Hi"
  - agent asks Q1
  - webhook: answer to Q1
  - agent asks Q2
  - webhook: answer to Q2
  - agent asks Q3
  - webhook: answer to Q3
  - agent marks qualified, syncs Zoho, sends confirmation
then:
  - Contact.qualification_status == "qualified"
  - Contact.zoho_lead_id is set
  - 4 outbound Messages in DB
  - AgentSession.state.qualification_progress.status == "qualified"
  - All RuntimeEventLog events present
```

### E2E Test 2 — Human handover mid-qualification
```
simulate:
  - webhook: "Hi"
  - agent asks Q1
  - webhook: "I just want to talk to a real person"
  - agent escalates
then:
  - Conversation.status == HUMAN_TAKEOVER
  - Announcement message in DB
  - AgentSession.state.escalation_requested == True
```

### E2E Test 3 — WAIT_DELAY resumes correctly (M-D dependency)
```
simulate:
  - webhook triggers flow with WAIT_DELAY node
  - ExecutionInstance.status == WAITING
  - Celery beat task runs
  - Flow resumes
then:
  - ExecutionInstance.status == COMPLETED
  - Reply sent after delay
```

---

## Part 6 — Documentation Update

### `CLAUDE_CONTEXT.md` Updates

Add new sections:
```markdown
## ADK Architecture (Missions M-A through M-E)
- Runtime: app/core/adk/ — LlmAgent + tools + orchestrator + session service
- Agent graph: OrchestratorAgent → [QualificationAgent, CRMAgent, ReplyAgent, HandoverAgent]
- Session: AgentSession table, LeadPilotSessionService
- Callbacks: LeadPilotCallbackHandler → RuntimeEventLog
- Builder: FlowVersion.adk_pipeline_config stores ADK pipeline config
```

### Update mission status table in `CLAUDE_CONTEXT.md`
```
| M-A | ADK Core Integration | ✅ |
| M-B | Multi-Agent Orchestration | ✅ |
| M-C | Session & Memory | ✅ |
| M-D | Flow Builder Revamp | ✅ |
| M-E | Observability & Tests | ✅ |
```

---

## Success Criteria

- [ ] `LeadPilotCallbackHandler` fires for every ADK lifecycle event
- [ ] All agent events appear in `RuntimeEventLog` with correct event types
- [ ] Execution trace admin endpoint returns full event chain
- [ ] Admin UI shows execution timeline with color-coded event sources
- [ ] New agent metrics appear in admin monitoring page
- [ ] `test_callbacks.py` — 5 tests passing
- [ ] `test_e2e_agent_flow.py` — 3 E2E scenarios passing
- [ ] All 327 pre-existing tests still pass (zero regressions)
- [ ] Total test count: 327 + ~50 new = ~377 tests passing
- [ ] `CLAUDE_CONTEXT.md` updated to reflect ADK architecture

---

## Final Verification Checklist

After all 5 missions complete, verify the full system:

**Functional:**
- [ ] WhatsApp webhook → qualification dialogue → Zoho sync → reply, end-to-end
- [ ] Meta Lead Ad → qualification → CRM → reply, end-to-end
- [ ] Human takeover via natural language ("speak to someone")
- [ ] WAIT_DELAY flow resumes after timer
- [ ] PARALLEL agents (CRM + reply) execute simultaneously
- [ ] CONDITION node routes qualified vs unqualified leads correctly

**Observability:**
- [ ] Every agent turn produces ≥5 RuntimeEventLog rows
- [ ] Admin trace view shows full reasoning chain
- [ ] Token usage tracked per workspace

**Stability:**
- [ ] Server restart between turns: conversation resumes correctly
- [ ] Redis unavailable: dispatch fallback works
- [ ] Gemini API error: ExecutionInstance marked FAILED, error logged
- [ ] 377 tests passing on fresh test.db

**No regressions:**
- [ ] `/api/v1/test-chat` (Prompt Studio) still works
- [ ] Admin portal all pages load
- [ ] Zoho health check passes
- [ ] WhatsApp + Meta dispatch still sends messages
