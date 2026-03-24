# Mission M-B — Multi-Agent Orchestration

## Goal
Build the actual agent graph that makes LeadPilot structurally different from Manychat.
Replace the single `LlmAgent` from M-A with a hierarchy of specialized agents:
an `OrchestratorAgent` that routes conversations to purpose-built sub-agents
(`QualificationAgent`, `CRMAgent`, `ReplyAgent`, `HandoverAgent`) based on
conversation state and lead progression.

## What This Unlocks
- True multi-agent handoffs — each agent has a focused role and specialized instruction
- Lead qualification as a first-class autonomous process (not a prompt trick)
- CRM sync decoupled from conversation — CRM agent can run independently
- Human escalation as a dedicated agent with its own logic
- The Manychat differentiation: flows that *think*, not just *follow steps*

## Prerequisites
- Mission M-A complete and passing all tests
- ADK tools (send_reply, upsert_zoho_lead, escalate_to_human, tag_contact) working
- Workspace prompt compiler feeding correctly into LlmAgent

---

## Agent Architecture

```
OrchestratorAgent
│
├── QualificationAgent
│     Tools: ask_question, tag_contact, mark_qualified, mark_disqualified
│
├── CRMAgent
│     Tools: upsert_zoho_lead, fetch_zoho_lead, update_contact_field
│
├── ReplyAgent
│     Tools: send_reply, send_media_message, send_template_message
│
└── HandoverAgent
      Tools: escalate_to_human, notify_team, send_handover_summary
```

### Agent Roles

**OrchestratorAgent**
- Entry point for every inbound message
- Has no tools directly
- Uses `AgentTool` to delegate to sub-agents
- Decides routing based on: conversation state, lead qualification status, user intent
- System instruction: high-level orchestration logic — "if lead not qualified, delegate to
  QualificationAgent. If qualified and CRM not synced, delegate to CRMAgent. Always
  delegate final reply to ReplyAgent."

**QualificationAgent**
- Specialized in lead qualification dialogue
- Knows all qualification questions and criteria (injected from `prompt_compiler`)
- Tracks which questions have been answered (via ADK session state)
- Calls `tag_contact` when qualification decision is made
- Calls `mark_qualified` / `mark_disqualified` to update contact metadata
- System instruction: focused entirely on qualification flow

**CRMAgent**
- Specialized in Zoho CRM operations
- Called when lead is qualified or when explicit CRM sync is needed
- Has access to `upsert_zoho_lead`, `fetch_zoho_lead`, `update_contact_field`
- System instruction: "You handle CRM data operations. Sync lead data to Zoho when called.
  Return a summary of what was synced."

**ReplyAgent**
- Specialized in crafting and sending replies
- Has access to all send_* tools
- Receives context from the orchestrator (what to communicate)
- System instruction: tone, length, platform-appropriate formatting rules

**HandoverAgent**
- Specialized in human escalation
- Sends a handover summary to the team (future: Slack/email notification)
- Sends an announcement to the lead
- Updates conversation status
- System instruction: empathetic, clear escalation messaging

---

## Files to Create

### `backend/app/core/adk/agents/`
New sub-package for each agent definition.

#### `backend/app/core/adk/agents/__init__.py`
Empty init.

#### `backend/app/core/adk/agents/qualification.py`

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.core.config import settings

def build_qualification_agent(
    qualification_questions: list[dict],
    qualification_criteria: list[dict],
    contact_id: str,
    workspace_id: str,
    session,  # AsyncSession
) -> LlmAgent:
    """
    Build the qualification agent with workspace-specific questions and criteria.
    """
    questions_text = "\n".join(
        f"- {q['label']}" for q in qualification_questions if q.get("enabled", True)
    )
    criteria_text = "\n".join(
        f"- {c['label']}: {c.get('description', '')}" for c in qualification_criteria
    )

    instruction = f"""
You are the Lead Qualification Agent for this business.

Your ONLY job is to collect the following information from the lead through natural conversation:
{questions_text}

Evaluate against these criteria:
{criteria_text}

Rules:
- Ask ONE question at a time. Never ask multiple questions in one message.
- Be conversational and friendly. Never sound like a form.
- Once all required information is collected, call mark_qualified() or mark_disqualified()
  based on the criteria above.
- If the lead asks to speak to a human at any point, immediately signal escalation.
"""

    async def ask_followup_question(question: str) -> dict:
        """Ask the lead a specific qualification question. Use this to guide the conversation."""
        # Returns instruction to the orchestrator to send this question via ReplyAgent
        return {"next_question": question, "action": "send_to_lead"}

    async def mark_qualified(reason: str) -> dict:
        """
        Mark this lead as qualified based on collected information.
        Call this when all qualification criteria are met.
        """
        # Updates contact.additional_metadata["qualification_status"] = "qualified"
        # Tags contact with "qualified"
        # Returns signal to orchestrator to trigger CRM sync
        ...

    async def mark_disqualified(reason: str) -> dict:
        """
        Mark this lead as disqualified.
        Call this when the lead does not meet qualification criteria.
        """
        ...

    return LlmAgent(
        name="qualification_agent",
        model=settings.GEMINI_MODEL,
        instruction=instruction,
        tools=[
            FunctionTool(func=ask_followup_question),
            FunctionTool(func=mark_qualified),
            FunctionTool(func=mark_disqualified),
        ],
    )
```

#### `backend/app/core/adk/agents/crm.py`

```python
def build_crm_agent(contact_id, workspace_id, session) -> LlmAgent:
    instruction = """
You are the CRM Sync Agent. Your job is to synchronize lead data to Zoho CRM.

When called:
1. Call upsert_zoho_lead() to create or update the lead record
2. Report back what was synced and whether it was a create or update
3. Do not engage in conversation with the lead — this is a background operation
"""
    # tools: upsert_zoho_lead, update_contact_field
```

#### `backend/app/core/adk/agents/reply.py`

```python
def build_reply_agent(workspace_tone, platform, contact_id, workspace_id, session) -> LlmAgent:
    instruction = f"""
You are the Reply Agent. Your job is to craft and send messages to the lead on {platform}.

Rules:
- Keep messages under 160 characters for WhatsApp unless detail is required
- Match the business tone: {workspace_tone}
- Never send multiple messages when one will do
- Use send_reply() for text, send_media_message() for images/documents
"""
    # tools: send_reply, send_media_message
```

#### `backend/app/core/adk/agents/handover.py`

```python
def build_handover_agent(contact_id, workspace_id, session) -> LlmAgent:
    instruction = """
You are the Human Handover Agent. Escalate the conversation to a human agent.

Steps:
1. Send a warm acknowledgment to the lead that a human will assist them
2. Call escalate_to_human() to update conversation status and notify the team
3. Send a brief summary of the conversation to help the human agent pick up context
"""
    # tools: escalate_to_human, send_handover_summary
```

---

### `backend/app/core/adk/agents/orchestrator.py`

The central routing agent. Uses `AgentTool` to wrap each sub-agent as a callable tool.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from app.core.config import settings

async def build_orchestrator(
    workspace_id: UUID,
    contact_id: UUID,
    conversation_id: UUID,
    session: AsyncSession,
) -> LlmAgent:
    """
    Build the full agent graph for one conversation turn.
    """
    from app.core.adk.agents.qualification import build_qualification_agent
    from app.core.adk.agents.crm import build_crm_agent
    from app.core.adk.agents.reply import build_reply_agent
    from app.core.adk.agents.handover import build_handover_agent
    from app.services.prompt_compiler import compile_workspace_prompt

    # Load workspace context
    compiled = await compile_workspace_prompt(workspace_id, session, include_qualification=True)
    contact = await session.get(Contact, contact_id)
    conversation = await session.get(Conversation, conversation_id)

    # Build sub-agents
    qualification_agent = build_qualification_agent(
        qualification_questions=...,  # from compiled
        qualification_criteria=...,   # from compiled
        contact_id=str(contact_id),
        workspace_id=str(workspace_id),
        session=session,
    )
    crm_agent = build_crm_agent(str(contact_id), str(workspace_id), session)
    reply_agent = build_reply_agent(
        workspace_tone="professional",  # from workspace settings
        platform=conversation.platform,
        contact_id=str(contact_id),
        workspace_id=str(workspace_id),
        session=session,
    )
    handover_agent = build_handover_agent(str(contact_id), str(workspace_id), session)

    # Determine current state for context injection
    is_qualified = (contact.additional_metadata or {}).get("qualification_status") == "qualified"
    crm_synced = contact.zoho_lead_id is not None
    status = conversation.status.value

    orchestrator_instruction = f"""
You are the Conversation Orchestrator for this business's AI system.

Current lead state:
- Qualification status: {"qualified" if is_qualified else "not yet qualified"}
- CRM synced: {"yes" if crm_synced else "no"}
- Conversation status: {status}

Routing rules:
1. If the lead is NOT qualified → delegate to qualification_agent to collect information
2. If the lead IS qualified and CRM is NOT synced → delegate to crm_agent first, then reply_agent
3. If the lead IS qualified and CRM IS synced → delegate to reply_agent
4. If the lead requests a human OR expresses strong frustration → delegate to handover_agent
5. After any sub-agent completes its work, delegate to reply_agent to send the response

Business context:
{compiled.system_instruction}
"""

    return LlmAgent(
        name="orchestrator",
        model=settings.GEMINI_MODEL,
        instruction=orchestrator_instruction,
        tools=[
            AgentTool(agent=qualification_agent),
            AgentTool(agent=crm_agent),
            AgentTool(agent=reply_agent),
            AgentTool(agent=handover_agent),
        ],
    )
```

---

## Files to Modify

### `backend/app/core/adk/runner.py`

Replace `build_leadpilot_agent()` call with `build_orchestrator()`:

```python
# BEFORE (M-A)
agent = await build_leadpilot_agent(workspace_id, session, execution_instance)

# AFTER (M-B)
from app.core.adk.agents.orchestrator import build_orchestrator
agent = await build_orchestrator(
    workspace_id=workspace_id,
    contact_id=contact_id,
    conversation_id=conversation_id,
    session=session,
)
```

The rest of runner.py (session management, history loading, tool call logging) is unchanged.

---

### `backend/app/core/adk/agent.py`

Keep `build_leadpilot_agent()` — it is still used by tests and potentially by the
Prompt Studio test chat in the future. Mark it as the "single-agent mode" (non-orchestrated).

---

## New ADK Session State Schema

ADK session state (stored in the session service, later persisted in M-C) uses:

```python
# Keys stored in ADK session state after each turn
{
    "qualification_progress": {
        "answered_questions": ["full_name", "email"],
        "pending_questions": ["budget", "timeline"],
        "status": "in_progress"  # | "qualified" | "disqualified"
    },
    "crm_sync": {
        "synced": False,
        "zoho_lead_id": None,
        "last_sync_at": None
    },
    "conversation_intent": "qualification"  # | "support" | "purchase" | "complaint"
}
```

This state is read by the OrchestratorAgent at the start of each turn to route correctly.

---

## Database Changes

### New column: `Contact.qualification_status`
```python
qualification_status: Optional[str] = Field(default=None)
# values: None | "in_progress" | "qualified" | "disqualified"
```

### New column: `Contact.intent`
```python
intent: Optional[str] = Field(default=None)
# values: None | "qualification" | "support" | "purchase" | "complaint"
```

**Alembic migration:** Create `alembic/versions/XXXX_add_contact_qualification_fields.py`

---

## Tests to Write

Location: `backend/tests/test_multi_agent.py`

### Test 1 — Orchestrator routes unqualified lead to QualificationAgent
```
given: contact with no qualification_status
when: orchestrator processes inbound "Hi, I'm interested"
then: qualification_agent is invoked (via AgentTool), asks first question
```

### Test 2 — Orchestrator routes qualified lead to CRMAgent then ReplyAgent
```
given: contact with qualification_status="qualified", no zoho_lead_id
when: orchestrator processes any inbound message
then: crm_agent invoked first, then reply_agent
```

### Test 3 — QualificationAgent marks lead as qualified after all questions answered
```
given: all qualification questions answered in session state
when: qualification_agent processes final answer
then: mark_qualified() called, contact.qualification_status updated
```

### Test 4 — HandoverAgent triggered on "I want to speak to a person"
```
given: any conversation state
when: inbound message = "I want to speak to a real person"
then: handover_agent invoked, conversation.status = HUMAN_TAKEOVER
```

### Test 5 — OrchestratorAgent builds correctly for each workspace state combination
```
given: 4 state combos (qualified/not × crm-synced/not)
when: build_orchestrator() called for each
then: instruction contains correct routing context for each state
```

---

## Success Criteria

- [ ] OrchestratorAgent builds with 4 sub-agents as AgentTools
- [ ] Unqualified lead → QualificationAgent handles first N turns
- [ ] Qualified lead → CRMAgent syncs → ReplyAgent sends confirmation
- [ ] "Speak to human" → HandoverAgent escalates correctly
- [ ] `qualification_status` column added via Alembic migration
- [ ] All M-A tests still pass
- [ ] All new M-B tests pass
- [ ] Admin portal "Automations" view still works (reads Flow/FlowVersion — unchanged)

---

## How to Verify End-to-End

1. Create a workspace with qualification questions configured
2. Send a sequence of WhatsApp webhooks simulating a full lead journey:
   - Message 1: "Hi" → expect qualification question
   - Message 2: answer → expect next question
   - Message N: final answer → expect qualification confirmed + Zoho sync + CRM confirmation reply
3. Check `Contact.qualification_status = "qualified"` and `Contact.zoho_lead_id` set
4. Send "I want to speak to someone" → expect `Conversation.status = HUMAN_TAKEOVER`
5. Verify `ExecutionStepLog` shows agent delegation chain per turn
