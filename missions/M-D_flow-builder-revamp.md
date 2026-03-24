# Mission M-D — Flow Builder Revamp

## Goal
Update the visual flow builder (React Flow frontend + `builder_translator.py` backend)
to natively represent agent graphs instead of rigid sequential nodes. Unlock the two
currently blocked node types (`CONDITION`, `WAIT_DELAY`) and add two new ones
(`PARALLEL`, `AGENT_HANDOFF`). The builder becomes a tool for configuring HOW the
agent graph behaves — not for scripting every step like a flowchart.

## What This Unlocks
- `CONDITION` — conditional branching based on lead state (qualification status, intent, etc.)
- `WAIT_DELAY` — pause execution and resume after a timer (follow-up flows)
- `PARALLEL` — run multiple agent tasks simultaneously (e.g., CRM sync + send reply at once)
- `AGENT_HANDOFF` — explicitly route to a named sub-agent in the graph
- Flow builder becomes genuinely more powerful than Manychat's template system
- Workspace owners can configure the agent's behavior without writing code

## Prerequisites
- Missions M-A, M-B, M-C complete
- ADK OrchestratorAgent running in production
- Existing React Flow builder operational (Automation Builder v2, Mission 27)

---

## Conceptual Shift: Flowcharts → Agent Policies

### Old mental model (Mission 27)
The builder was a flowchart: draw a path, the runtime follows it step by step.
```
Trigger → AI_REPLY → ZOHO_UPSERT_LEAD → SEND_MESSAGE
```

### New mental model (M-D)
The builder configures agent *policies*: what agents exist, what tools they have,
what routing rules apply. The agent graph uses this config at runtime to decide.
```
Trigger → OrchestratorPolicy
  ├── QualificationPolicy (questions, criteria, tone)
  ├── CRMPolicy (which CRM fields to sync, when)
  ├── ReplyPolicy (tone, length, platform rules)
  └── HandoverPolicy (trigger conditions, announcement template)
```

The user is no longer drawing every arrow — they're configuring the agents' decision rules.

---

## New Node Type Catalog

### Existing (keep, refine)
| Node | Change |
|---|---|
| `MESSAGE_INBOUND` | Keep as trigger |
| `LEAD_AD_SUBMIT` | Keep as trigger |
| `AI_REPLY` | Rename to `AGENT_REPLY` — now maps to ReplyAgent config |
| `SEND_MESSAGE` | Keep — static message, no AI needed |
| `ZOHO_UPSERT_LEAD` | Keep — explicit CRM sync node |
| `HUMAN_HANDOVER` | Keep — explicit escalation node |
| `TAG_CONTACT` | Keep — contact tagging |

### Newly unlocked
| Node | Maps to ADK |
|---|---|
| `CONDITION` | ADK conditional routing in OrchestratorAgent |
| `WAIT_DELAY` | ADK session state + Celery beat timer |

### New
| Node | Purpose |
|---|---|
| `PARALLEL` | `ParallelAgent` — runs two sub-agents simultaneously |
| `AGENT_HANDOFF` | Explicit delegation to a named sub-agent |
| `QUALIFICATION_GATE` | Conditional branch based on qualification status |
| `INTENT_ROUTER` | Route based on detected conversation intent |

---

## Backend Changes

### `backend/app/domain/builder_translator.py`

**Current:** Translates React Flow JSON → runtime `definition_json` (node list + edges).
**New:** Translates React Flow JSON → ADK pipeline config + runtime `definition_json` (dual output).

The dual output ensures backwards compatibility — the `definition_json` is still stored
in `FlowVersion` for audit/display, while the new `adk_pipeline_config` drives execution.

```python
# New constants
ADK_SUPPORTED_NODE_TYPES = {
    "AI_REPLY", "AGENT_REPLY", "SEND_MESSAGE", "HUMAN_HANDOVER",
    "TAG_CONTACT", "ZOHO_UPSERT_LEAD",
    "CONDITION", "WAIT_DELAY",           # Now supported
    "PARALLEL", "AGENT_HANDOFF",         # New
    "QUALIFICATION_GATE", "INTENT_ROUTER",  # New
}

BUILDER_ONLY_NODE_TYPES = set()  # Empty — all types now publishable


def translate_to_adk_pipeline(builder_graph: dict) -> dict:
    """
    Translate builder_graph_json to an ADK pipeline config.
    This replaces/extends the existing translate() function.

    Returns:
    {
        "pipeline_type": "orchestrated",
        "agents": {
            "orchestrator": {"routing_rules": [...], "sub_agents": [...]},
            "qualification": {"questions": [...], "criteria": [...]},
            "crm": {"fields": [...], "trigger_on": "qualified"},
            "reply": {"tone": "...", "max_length": 160},
            "handover": {"trigger_conditions": [...], "announcement": "..."}
        },
        "triggers": [...],
        "condition_branches": [...],
        "wait_delays": [...]
    }
    """
    nodes = builder_graph.get("nodes", [])
    edges = builder_graph.get("edges", [])

    pipeline = {
        "pipeline_type": "orchestrated",
        "agents": {
            "orchestrator": {"routing_rules": [], "sub_agents": []},
            "qualification": {},
            "crm": {},
            "reply": {},
            "handover": {},
        },
        "triggers": [],
        "condition_branches": [],
        "wait_delays": [],
    }

    for node in nodes:
        node_type = _get_node_type(node)
        config = node.get("data", {}).get("config", {})

        if node_type in ("MESSAGE_INBOUND", "LEAD_AD_SUBMIT"):
            pipeline["triggers"].append({
                "type": node_type,
                "platform": config.get("platform", "whatsapp"),
            })

        elif node_type in ("AI_REPLY", "AGENT_REPLY"):
            # Configure the ReplyAgent with this node's settings
            pipeline["agents"]["reply"].update({
                "goal": config.get("goal"),
                "tone": config.get("tone", "professional"),
                "max_length": config.get("max_length", 160),
                "extra_instructions": config.get("extra_instructions"),
            })

        elif node_type == "CONDITION":
            pipeline["condition_branches"].append({
                "node_id": node.get("id"),
                "condition_type": config.get("condition_type"),  # e.g. "qualification_status"
                "operator": config.get("operator"),              # e.g. "equals"
                "value": config.get("value"),                    # e.g. "qualified"
                "true_branch": _get_next_node(node.get("id"), edges, handle="true"),
                "false_branch": _get_next_node(node.get("id"), edges, handle="false"),
            })

        elif node_type == "WAIT_DELAY":
            pipeline["wait_delays"].append({
                "node_id": node.get("id"),
                "delay_seconds": config.get("delay_seconds", 3600),
                "delay_unit": config.get("delay_unit", "hours"),  # minutes | hours | days
                "resume_node_id": _get_next_node(node.get("id"), edges),
            })

        elif node_type == "QUALIFICATION_GATE":
            pipeline["agents"]["orchestrator"]["routing_rules"].append({
                "type": "qualification_gate",
                "qualified_branch": _get_next_node(node.get("id"), edges, handle="qualified"),
                "unqualified_branch": _get_next_node(node.get("id"), edges, handle="unqualified"),
            })

        elif node_type == "INTENT_ROUTER":
            pipeline["agents"]["orchestrator"]["routing_rules"].append({
                "type": "intent_router",
                "routes": config.get("routes", []),
                # routes: [{"intent": "complaint", "agent": "handover"}, ...]
            })

        elif node_type == "PARALLEL":
            pipeline["agents"]["orchestrator"]["routing_rules"].append({
                "type": "parallel",
                "parallel_agents": config.get("agents", []),
            })

    return pipeline
```

**Update `translate()` to produce dual output:**
```python
def translate(builder_graph: dict) -> tuple[dict, dict]:
    """
    Returns (definition_json, adk_pipeline_config).
    definition_json: legacy format, stored in FlowVersion for audit/display
    adk_pipeline_config: new format, used by ADK runner
    """
    definition_json = _translate_legacy(builder_graph)    # existing logic
    adk_pipeline = translate_to_adk_pipeline(builder_graph)
    return definition_json, adk_pipeline
```

---

### `backend/app/models/models.py`

Add `adk_pipeline_config` column to `FlowVersion`:

```python
class FlowVersion(WorkspaceScopedModel, table=True):
    ...
    definition_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    adk_pipeline_config: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )  # NEW — ADK pipeline config, generated at publish time
```

**Alembic migration:** `XXXX_add_adk_pipeline_config_to_flow_version.py`

---

### `backend/app/api/v1/automations.py`

Update the `publish` endpoint to call both translators:

```python
# On publish
definition_json, adk_pipeline = translate(draft.builder_graph_json)
flow_version.definition_json = definition_json
flow_version.adk_pipeline_config = adk_pipeline  # NEW
```

---

### `backend/app/core/adk/runner.py`

Load `adk_pipeline_config` from `FlowVersion` and use it to configure the agent graph:

```python
async def run_for_contact(..., flow_version: FlowVersion):
    pipeline_config = flow_version.adk_pipeline_config or {}

    agent = await build_orchestrator(
        workspace_id=workspace_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        pipeline_config=pipeline_config,  # NEW — passes builder config to orchestrator
        session=session,
    )
```

---

### `backend/app/core/adk/agents/orchestrator.py`

Accept and apply `pipeline_config`:

```python
async def build_orchestrator(
    ...,
    pipeline_config: dict,   # NEW
) -> LlmAgent:
    # Extract routing rules from builder config
    routing_rules = pipeline_config.get("agents", {}).get("orchestrator", {}).get("routing_rules", [])
    reply_config = pipeline_config.get("agents", {}).get("reply", {})

    # Build routing instruction from rules
    routing_instruction = _build_routing_instruction(routing_rules)

    # Override reply agent config from builder
    reply_agent = build_reply_agent(
        tone=reply_config.get("tone", "professional"),
        max_length=reply_config.get("max_length", 160),
        ...
    )
    ...
```

---

## WAIT_DELAY Implementation

`WAIT_DELAY` requires Celery beat scheduling — it cannot be handled inside a single
ADK runner invocation.

### How it works
1. Agent reaches a WAIT_DELAY node
2. ADK runner stores `{"waiting_for": "delay", "resume_at": <timestamp>, "resume_node_id": "..."}` in session state
3. Sets `ExecutionInstance.status = WAITING`
4. A Celery beat task runs every minute to check for ready-to-resume instances

### New Celery task: `resume_waiting_instances_task`

```python
@celery_app.task(name="app.workers.tasks.resume_waiting_instances_task")
def resume_waiting_instances_task():
    """
    Every-minute task: find WAITING ExecutionInstances whose delay has elapsed
    and re-trigger the ADK runner for them.
    """
    async def _run():
        now = datetime.utcnow()
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(ExecutionInstance).where(
                    ExecutionInstance.status == ExecutionStatus.WAITING,
                    ExecutionInstance.resume_at <= now,
                )
            )
            instances = result.scalars().all()
            for instance in instances:
                instance.status = ExecutionStatus.RUNNING
                session.add(instance)
                # Re-trigger ADK runner from the resume node
                await run_for_contact(
                    workspace_id=instance.workspace_id,
                    contact_id=instance.contact_id,
                    ...
                    resume_from_node=instance.resume_node_id,
                )
            await session.commit()
    run_async(_run())
```

### New columns on `ExecutionInstance`
```python
resume_at: Optional[datetime] = Field(default=None)
resume_node_id: Optional[str] = Field(default=None)
```

---

## Frontend Changes

### New Node Components

Location: `frontend/src/components/automation/nodes/`

#### `ConditionNode.tsx`
Visual: Diamond shape with two outgoing handles ("true" / "false").
Config panel: condition type selector (qualification status, intent, tag, custom field),
operator (equals, contains, greater than), value input.

#### `WaitDelayNode.tsx`
Visual: Clock icon, shows delay duration prominently.
Config panel: duration input + unit selector (minutes / hours / days).

#### `ParallelNode.tsx`
Visual: Forked arrows showing simultaneous execution paths.
Config panel: multi-select of which agents run in parallel.

#### `AgentHandoffNode.tsx`
Visual: Agent icon + name of target agent.
Config panel: dropdown of available sub-agents.

#### `QualificationGateNode.tsx`
Visual: Funnel icon with "Qualified" / "Not Qualified" branches.
Config panel: read-only (pulls from workspace qualification config).

#### `IntentRouterNode.tsx`
Visual: Multiple arrows labeled by intent.
Config panel: intent-to-agent mapping table.

---

### Node Palette Update

`frontend/src/components/automation/NodePalette.tsx`

Add new nodes to the palette. Group them:

```
TRIGGERS
  ├── WhatsApp Message
  └── Meta Lead Ad

AGENT NODES
  ├── Agent Reply (was AI Reply)
  ├── Send Message
  ├── Zoho CRM Sync
  ├── Tag Contact
  └── Human Handover

FLOW CONTROL
  ├── Condition
  ├── Wait / Delay
  ├── Parallel
  └── Agent Handoff

ROUTING
  ├── Qualification Gate
  └── Intent Router
```

---

### `builder_translator.py` Frontend Equivalent

`frontend/src/lib/builder-validator.ts` — update client-side validation:

```typescript
// Remove CONDITION and WAIT_DELAY from blocked types
const UNSUPPORTED_TYPES = new Set<string>([])  // Empty — all types supported

// Add validation for new node types
function validateConditionNode(node: BuilderNode): ValidationError[] {
    const { condition_type, operator, value } = node.data.config
    if (!condition_type) return [{ field: "condition_type", message: "Select a condition" }]
    if (!operator) return [{ field: "operator", message: "Select an operator" }]
    return []
}

function validateWaitDelayNode(node: BuilderNode): ValidationError[] {
    const { delay_seconds } = node.data.config
    if (!delay_seconds || delay_seconds < 60) {
        return [{ field: "delay_seconds", message: "Minimum delay is 1 minute" }]
    }
    return []
}
```

---

## Tests to Write

### Backend: `backend/tests/test_builder_translator_v2.py`

### Test 1 — CONDITION node translates to condition_branches entry
```
given: builder graph with CONDITION node (condition_type="qualification_status")
when: translate_to_adk_pipeline() called
then: pipeline.condition_branches has one entry with true/false branches
```

### Test 2 — WAIT_DELAY node translates to wait_delays entry
```
given: WAIT_DELAY node with delay_seconds=3600
then: pipeline.wait_delays[0].delay_seconds == 3600
```

### Test 3 — PARALLEL node adds parallel routing rule
```
given: PARALLEL node with agents=["crm", "reply"]
then: orchestrator routing_rules includes parallel rule
```

### Test 4 — All new node types pass validation (no longer blocked)
```
given: graph with CONDITION + WAIT_DELAY
when: validate_graph() called
then: returns empty errors list
```

### Test 5 — FlowVersion stores adk_pipeline_config on publish
```
given: valid builder graph published via /automations/{id}/publish
then: FlowVersion.adk_pipeline_config is not None, contains pipeline dict
```

### Test 6 — resume_waiting_instances_task resumes WAITING instances
```
given: ExecutionInstance with status=WAITING, resume_at=5 minutes ago
when: resume_waiting_instances_task runs
then: instance.status=RUNNING, ADK runner invoked
```

---

## Success Criteria

- [ ] `CONDITION` and `WAIT_DELAY` nodes publishable (not blocked)
- [ ] `PARALLEL` and `AGENT_HANDOFF` nodes appear in palette and validate
- [ ] `translate_to_adk_pipeline()` produces valid ADK config for all node types
- [ ] `FlowVersion.adk_pipeline_config` populated on publish
- [ ] `resume_waiting_instances_task` Celery task registered and functional
- [ ] `ExecutionInstance.resume_at` + `resume_node_id` columns added via migration
- [ ] Frontend node palette shows all new node types
- [ ] All new node validation rules working (no publish without required config)
- [ ] All M-A, M-B, M-C tests still pass
- [ ] All new M-D tests pass

---

## How to Verify End-to-End

1. Open Automation Builder UI
2. Drag in: Trigger → Qualification Gate → (qualified) → Zoho Sync + Reply (PARALLEL) → (unqualified) → WAIT_DELAY (2 hours) → Agent Reply
3. Publish the flow — no validation errors
4. Check `FlowVersion.adk_pipeline_config` in DB — non-null, contains pipeline dict
5. Send a qualified lead webhook → Zoho sync and reply happen simultaneously (PARALLEL)
6. Send an unqualified lead webhook → WAIT_DELAY sets `ExecutionInstance.status=WAITING`
7. Wait for Celery beat (or manually trigger resume task) → flow resumes
