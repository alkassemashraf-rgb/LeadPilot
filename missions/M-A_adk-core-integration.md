# Mission M-A — ADK Core Integration

## Goal
Replace the sequential MVP runtime engine (`domain/runtime.py` + `core/ai.py`) with
Google ADK's `LlmAgent` + tool system. After this mission the AI does not follow a
fixed node order — it autonomously decides which tools to call (Zoho, WhatsApp reply,
human handover, contact tagging) based on the conversation. Everything else in the
codebase is untouched.

## What This Unlocks
- Autonomous tool selection by the LLM instead of rigid sequential node execution
- Native Gemini integration via ADK (already the model in use)
- Foundation for all subsequent missions (multi-agent, session memory, builder)
- Unblocks CONDITION and WAIT_DELAY from day one (ADK handles branching natively)

## Prerequisites
- Missions 1–38 complete (current state)
- Python 3.11, existing venv at `backend/venv/`
- All 327 tests passing on a clean `test.db`

---

## Architecture Before → After

### Before
```
Webhook → Celery → process_webhook_event() → execute_instance()
           → while loop: AI_REPLY | SEND_MESSAGE | ZOHO_UPSERT_LEAD
           → core/ai.py (raw genai.GenerativeModel)
```

### After
```
Webhook → Celery → process_webhook_event() → adk_runner.run_for_contact()
           → ADK LlmAgent (Gemini) + declared tools
           → tools call: send_reply | upsert_zoho | escalate | tag_contact
           → dispatch_service (unchanged)
```

---

## Files to Create

### `backend/app/core/adk/__init__.py`
Empty init — marks the package.

---

### `backend/app/core/adk/tools.py`
Declares all ADK FunctionTools wrapping existing business logic.
Each tool is a plain async function with type-annotated parameters and a docstring
(ADK uses the docstring as the LLM's tool description).

**Tools to declare:**

```python
from google.adk.tools import FunctionTool

async def send_reply(
    message_content: str,
    contact_id: str,
    workspace_id: str,
    platform: str,
) -> dict:
    """
    Send a text reply to the contact on their messaging platform (WhatsApp or Meta).
    Use this when you want to respond to the lead with a message.
    Returns: {"status": "sent", "message_id": "..."}
    """
    # wraps handle_send_message logic from runtime.py
    # stores Message row, triggers dispatch_message_task.delay()

async def upsert_zoho_lead(
    contact_id: str,
    workspace_id: str,
) -> dict:
    """
    Sync the contact's current data to Zoho CRM as a lead.
    Use this when enough information has been collected to create or update a CRM record.
    Returns: {"zoho_lead_id": "...", "action": "create"|"update"}
    """
    # wraps handle_zoho_upsert logic from runtime.py

async def escalate_to_human(
    contact_id: str,
    workspace_id: str,
    announcement_message: str,
) -> dict:
    """
    Transfer the conversation to a human agent and send an announcement message.
    Use this when the lead requests a human, expresses frustration, or when you
    cannot resolve their query.
    Returns: {"status": "escalated"}
    """
    # sets Conversation.status = HUMAN_TAKEOVER
    # stores announcement as outbound Message
    # triggers dispatch

async def tag_contact(
    contact_id: str,
    workspace_id: str,
    tag: str,
) -> dict:
    """
    Apply a classification tag to the contact for segmentation.
    Use this after determining a lead's category, intent, or qualification status.
    Returns: {"tag": "...", "applied": true}
    """
    # stores tag in contact.additional_metadata["tags"]
```

Each function receives a `db_session` injected via a context mechanism (see runner.py).
The tool functions do NOT take `db_session` as a parameter visible to the LLM — it is
injected as a closure or via a tool context wrapper.

**Pattern for DB injection:**
```python
def make_tools(session: AsyncSession, instance: ExecutionInstance) -> list:
    """Factory that creates tool functions with DB session pre-bound."""

    async def send_reply(message_content: str, platform: str) -> dict:
        """Send a text reply to the contact on their messaging platform."""
        ...  # uses session, instance from closure

    return [
        FunctionTool(func=send_reply),
        FunctionTool(func=upsert_zoho_lead_fn),
        ...
    ]
```

---

### `backend/app/core/adk/agent.py`
Factory function that builds a configured `LlmAgent` for a workspace.

```python
from google.adk.agents import LlmAgent
from app.services.prompt_compiler import compile_workspace_prompt
from app.core.adk.tools import make_tools
from app.core.config import settings

async def build_leadpilot_agent(
    workspace_id: UUID,
    session: AsyncSession,
    execution_instance: ExecutionInstance,
) -> LlmAgent:
    """
    Build a fully configured LlmAgent for a workspace conversation.
    Compiles the prompt, injects the contact context, and wires all tools.
    """
    # 1. Compile workspace system instruction (existing prompt_compiler — unchanged)
    compiled = await compile_workspace_prompt(
        workspace_id,
        session,
        include_files=True,
        include_qualification=True,
    )

    # 2. Build tools with DB session bound via closure
    tools = make_tools(session, execution_instance)

    # 3. Build and return the agent
    return LlmAgent(
        name="leadpilot_agent",
        model=settings.GEMINI_MODEL,  # e.g. "gemini-2.0-flash"
        instruction=compiled.system_instruction,
        tools=tools,
    )
```

---

### `backend/app/core/adk/runner.py`
The ADK runner wrapper. This replaces `execute_instance()` as the entry point
called from `tasks.py`.

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.types import Content, Part

async def run_for_contact(
    workspace_id: UUID,
    contact_id: UUID,
    conversation_id: UUID,
    inbound_message: str,
    execution_instance: ExecutionInstance,
    session: AsyncSession,
) -> None:
    """
    Run the ADK agent for one inbound message turn.

    Steps:
    1. Build the LlmAgent for this workspace
    2. Load conversation history from DB → ADK session
    3. Run agent with the new inbound message
    4. Log ADK tool calls as ExecutionStepLog rows (audit trail preserved)
    5. Log final response as a runtime event
    """
    from app.core.adk.agent import build_leadpilot_agent

    agent = await build_leadpilot_agent(workspace_id, session, execution_instance)

    # ADK session service — InMemorySessionService for M-A
    # (replaced with DB-backed service in Mission M-C)
    session_service = InMemorySessionService()
    adk_session_id = str(conversation_id)  # one ADK session per conversation

    runner = Runner(
        agent=agent,
        app_name="leadpilot",
        session_service=session_service,
    )

    # Build history from DB messages
    history = await _build_adk_history(conversation_id, session)
    # Pre-load history into the ADK session
    await _seed_session_history(session_service, adk_session_id, history)

    # Run the agent with the new user message
    user_content = Content(role="user", parts=[Part(text=inbound_message)])

    async for event in runner.run_async(
        user_id=str(contact_id),
        session_id=adk_session_id,
        new_message=user_content,
    ):
        # Log each tool call as an ExecutionStepLog
        if event.get_function_calls():
            for call in event.get_function_calls():
                await _log_tool_call(session, execution_instance, call)

        # Mark instance complete on final response
        if event.is_final_response():
            execution_instance.status = ExecutionStatus.COMPLETED
            session.add(execution_instance)
            await session.commit()
```

**Helper functions in runner.py:**
- `_build_adk_history(conversation_id, db_session)` — loads last N messages from `Message`
  table and converts to ADK `Content` objects
- `_seed_session_history(session_service, session_id, history)` — injects history into ADK session
- `_log_tool_call(db_session, instance, call)` — writes `ExecutionStepLog` row for each tool
  invocation (preserves audit trail from current runtime)

---

## Files to Modify

### `backend/app/workers/tasks.py`

**Change:** Replace the `execute_instance(instance.id)` call with the ADK runner.

```python
# BEFORE (line ~494)
await execute_instance(instance.id)

# AFTER
from app.core.adk.runner import run_for_contact
await run_for_contact(
    workspace_id=event.workspace_id,
    contact_id=contact.id,
    conversation_id=conversation.id,
    inbound_message=info.get("content") or "",
    execution_instance=instance,
    session=session,
)
```

The `ExecutionInstance` row is still created before this call (unchanged). The ADK runner
updates its status (COMPLETED / FAILED) instead of the old execute_instance loop.

---

### `backend/app/domain/runtime.py`

Keep the file. Extract the three handler functions into standalone async functions
that will be called by the ADK tools:
- `handle_zoho_upsert()` → called by the `upsert_zoho_lead` tool
- `handle_send_message()` → called by the `send_reply` tool
- `handle_ai_reply()` → **DELETED** — the LlmAgent IS the AI reply now

Remove `execute_instance()`. Mark the file as deprecated with a comment pointing to
`app/core/adk/runner.py`.

---

### `backend/app/core/ai.py`

Keep the file and `AIProvider` class — it is still used by `test_chat.py` endpoint for
the Prompt Studio test chat feature (which does NOT use the flow runtime).

Do NOT remove it in this mission.

---

### `backend/requirements.txt` (or `pyproject.toml`)

Add:
```
google-adk>=1.0.0
```

Verify the installed `google-generativeai` version is compatible with `google-adk`.
ADK typically pins or re-exports Gemini — check for conflicts.

---

## Database Changes

**None.** All existing tables are preserved:
- `ExecutionInstance` — still created per webhook, status updated by ADK runner
- `ExecutionStepLog` — still written, one row per ADK tool call
- `Message` — still written by tool functions, dispatched by existing dispatch_service
- `FlowVersion` / `Flow` — still queried to find the published flow; the runner uses
  the flow's `system_instruction` context from `prompt_compiler`, not node traversal

The `definition_json` format is still stored but the runtime no longer walks it node
by node. In M-D (builder revamp) the format will evolve.

---

## Environment Variables

Add to `.env` and `.env.example`:
```
# Already present — verify it's set
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash
```

No new env vars required for M-A.

---

## Tests to Write

Location: `backend/tests/test_adk_runner.py`

### Test 1 — Agent builds successfully
```
given: workspace with PromptConfig, knowledge files, qualification config
when: build_leadpilot_agent() is called
then: returns LlmAgent with non-empty instruction, correct model, 4 tools declared
```

### Test 2 — send_reply tool stores message and triggers dispatch
```
given: contact, conversation, ADK tool call to send_reply
when: tool executes
then: Message row created with direction=outbound, dispatch_message_task.delay called
```

### Test 3 — upsert_zoho_lead tool calls Zoho adapter
```
given: connected Zoho integration, ZohoLeadMapping configured, contact with data
when: tool executes
then: ZohoAdapter.upsert_lead called, contact.zoho_lead_id updated
```

### Test 4 — escalate_to_human tool updates conversation status
```
given: BOT_ACTIVE conversation
when: escalate_to_human tool executes
then: Conversation.status == HUMAN_TAKEOVER, announcement Message created
```

### Test 5 — run_for_contact marks instance COMPLETED
```
given: full ADK setup with mocked Gemini response (no real API call)
when: run_for_contact() completes
then: ExecutionInstance.status == COMPLETED
```

### Test 6 — run_for_contact marks instance FAILED on Gemini error
```
given: Gemini API raises exception
when: run_for_contact() runs
then: ExecutionInstance.status == FAILED, error logged
```

### Existing tests to verify still pass
Run full suite. Key regression checkpoints:
- `test_webhooks.py` — webhook ingestion unchanged
- `test_dispatch.py` — dispatch service unchanged
- `test_automations.py` — flow CRUD unchanged
- `test_zoho.py` — Zoho adapter unchanged

---

## Success Criteria

- [ ] `google-adk` installed, `import google.adk` works in venv
- [ ] `build_leadpilot_agent()` returns a valid `LlmAgent` with 4 tools
- [ ] Sending a WhatsApp webhook → ADK runner executes → reply stored in `Message` table
- [ ] Tool calls logged as `ExecutionStepLog` rows
- [ ] `ExecutionInstance` status transitions: RUNNING → COMPLETED or FAILED
- [ ] All 327 existing tests still pass
- [ ] New ADK runner tests: 6 passing
- [ ] No imports of `execute_instance` remain in production code paths

---

## How to Verify End-to-End

1. Start backend in dev mode
2. Send a test WhatsApp webhook via the existing test endpoint or Postman
3. Check `ExecutionInstance` table — status should be COMPLETED
4. Check `ExecutionStepLog` — rows for each tool the agent called
5. Check `Message` table — outbound message with `direction=outbound`
6. Check `RuntimeEventLog` — `runtime.step_completed` events per tool
7. Verify no regression in existing `/api/v1/test-chat` (uses `core/ai.py` directly — unchanged)
