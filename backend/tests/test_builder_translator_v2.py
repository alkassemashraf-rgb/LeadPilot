"""
Mission M-D: Builder translator v2 tests.
Tests for new node types: CONDITION, WAIT_DELAY, PARALLEL, AGENT_HANDOFF,
QUALIFICATION_GATE, INTENT_ROUTER, and the dual translate() output.
No DB required — pure logic tests.
"""
import pytest
from app.domain.builder_translator import validate_graph, translate, translate_to_adk_pipeline


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_builder_translator to keep tests isolated)
# ---------------------------------------------------------------------------

def make_trigger_node(node_id="trigger-1", node_type="MESSAGE_INBOUND", platform="whatsapp"):
    return {
        "id": node_id,
        "type": "triggerNode",
        "position": {"x": 250, "y": 50},
        "data": {"nodeType": node_type, "platform": platform, "config": {}},
    }


def make_action_node(node_id, node_type, config=None):
    return {
        "id": node_id,
        "type": "actionNode",
        "position": {"x": 250, "y": 220},
        "data": {"nodeType": node_type, "config": config or {}},
    }


def make_edge(edge_id, source, target, source_handle=None):
    e = {"id": edge_id, "source": source, "target": target}
    if source_handle:
        e["sourceHandle"] = source_handle
    return e


# ---------------------------------------------------------------------------
# Test 1 — CONDITION node translates to condition_branches entry
# ---------------------------------------------------------------------------

def test_condition_node_translates_to_condition_branches():
    """CONDITION node should populate pipeline.condition_branches with true/false branch IDs."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("cond-1", "CONDITION", {
                "condition_type": "qualification_status",
                "operator": "equals",
                "value": "qualified",
            }),
            make_action_node("true-node", "ZOHO_UPSERT_LEAD", {}),
            make_action_node("false-node", "WAIT_DELAY", {"delay_seconds": 3600}),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "cond-1"),
            make_edge("e2", "cond-1", "true-node", source_handle="true"),
            make_edge("e3", "cond-1", "false-node", source_handle="false"),
        ],
    }
    pipeline = translate_to_adk_pipeline(graph)

    assert len(pipeline["condition_branches"]) == 1
    branch = pipeline["condition_branches"][0]
    assert branch["node_id"] == "cond-1"
    assert branch["condition_type"] == "qualification_status"
    assert branch["operator"] == "equals"
    assert branch["value"] == "qualified"
    assert branch["true_branch"] == "true-node"
    assert branch["false_branch"] == "false-node"


# ---------------------------------------------------------------------------
# Test 2 — WAIT_DELAY node translates to wait_delays entry
# ---------------------------------------------------------------------------

def test_wait_delay_node_translates_to_wait_delays():
    """WAIT_DELAY node should populate pipeline.wait_delays with delay config."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("wait-1", "WAIT_DELAY", {
                "delay_seconds": 3600,
                "delay_unit": "hours",
            }),
            make_action_node("after-wait", "AI_REPLY", {"goal": "Follow up"}),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "wait-1"),
            make_edge("e2", "wait-1", "after-wait"),
        ],
    }
    pipeline = translate_to_adk_pipeline(graph)

    assert len(pipeline["wait_delays"]) == 1
    delay = pipeline["wait_delays"][0]
    assert delay["node_id"] == "wait-1"
    assert delay["delay_seconds"] == 3600
    assert delay["delay_unit"] == "hours"
    assert delay["resume_node_id"] == "after-wait"


# ---------------------------------------------------------------------------
# Test 3 — PARALLEL node adds parallel routing rule
# ---------------------------------------------------------------------------

def test_parallel_node_adds_routing_rule():
    """PARALLEL node should add a parallel routing rule to orchestrator.routing_rules."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("par-1", "PARALLEL", {"agents": ["crm", "reply"]}),
        ],
        "edges": [make_edge("e1", "trigger-1", "par-1")],
    }
    pipeline = translate_to_adk_pipeline(graph)

    routing_rules = pipeline["agents"]["orchestrator"]["routing_rules"]
    parallel_rule = next((r for r in routing_rules if r["type"] == "parallel"), None)
    assert parallel_rule is not None
    assert parallel_rule["parallel_agents"] == ["crm", "reply"]


# ---------------------------------------------------------------------------
# Test 4 — All new node types pass validation with valid config
# ---------------------------------------------------------------------------

def test_all_new_node_types_pass_validation():
    """A graph with CONDITION + WAIT_DELAY + PARALLEL + AGENT_HANDOFF + QUALIFICATION_GATE + INTENT_ROUTER
    should all pass validation when properly configured."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("cond-1", "CONDITION", {
                "condition_type": "qualification_status",
                "operator": "equals",
                "value": "qualified",
            }),
            make_action_node("wait-1", "WAIT_DELAY", {"delay_seconds": 3600}),
            make_action_node("par-1", "PARALLEL", {"agents": ["crm", "reply"]}),
            make_action_node("handoff-1", "AGENT_HANDOFF", {"target_agent": "handover"}),
            make_action_node("gate-1", "QUALIFICATION_GATE", {}),
            make_action_node("router-1", "INTENT_ROUTER", {
                "routes": [{"intent": "complaint", "agent": "handover"}]
            }),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "cond-1"),
            make_edge("e2", "trigger-1", "wait-1"),
            make_edge("e3", "trigger-1", "par-1"),
            make_edge("e4", "trigger-1", "handoff-1"),
            make_edge("e5", "trigger-1", "gate-1"),
            make_edge("e6", "trigger-1", "router-1"),
        ],
    }
    errors = validate_graph(graph)
    # None of the new node types should produce "not yet supported" errors
    assert not any("not yet supported" in e.get("message", "") for e in errors)
    # No config errors for these properly-configured nodes
    new_type_ids = {"cond-1", "wait-1", "par-1", "handoff-1", "gate-1", "router-1"}
    config_errors = [e for e in errors if e.get("node_id") in new_type_ids]
    assert config_errors == []


# ---------------------------------------------------------------------------
# Test 5 — translate() returns dual output (definition_json + adk_pipeline_config)
# ---------------------------------------------------------------------------

def test_translate_returns_dual_output():
    """translate() must return a 2-tuple: (definition_json, adk_pipeline_config)."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("n1", "AI_REPLY", {"goal": "Greet lead", "tone": "friendly", "max_length": 120}),
        ],
        "edges": [make_edge("e1", "trigger-1", "n1")],
    }
    result = translate(graph)
    assert isinstance(result, tuple)
    assert len(result) == 2

    definition_json, adk_pipeline = result

    # definition_json has legacy shape
    assert "start_node_id" in definition_json
    assert "nodes" in definition_json
    assert "edges" in definition_json

    # adk_pipeline has new shape
    assert adk_pipeline["pipeline_type"] == "orchestrated"
    assert "agents" in adk_pipeline
    assert "triggers" in adk_pipeline

    # AI_REPLY config should be reflected in reply agent config
    reply_cfg = adk_pipeline["agents"]["reply"]
    assert reply_cfg.get("goal") == "Greet lead"
    assert reply_cfg.get("tone") == "friendly"
    assert reply_cfg.get("max_length") == 120


# ---------------------------------------------------------------------------
# Test 6 — QUALIFICATION_GATE + INTENT_ROUTER produce correct routing rules
# ---------------------------------------------------------------------------

def test_qualification_gate_and_intent_router_routing_rules():
    """QUALIFICATION_GATE adds qualification_gate rule; INTENT_ROUTER adds intent_router rule."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("gate-1", "QUALIFICATION_GATE", {}),
            make_action_node("router-1", "INTENT_ROUTER", {
                "routes": [
                    {"intent": "complaint", "agent": "handover"},
                    {"intent": "pricing", "agent": "reply"},
                ]
            }),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "gate-1"),
            make_edge("e2", "trigger-1", "router-1"),
        ],
    }
    pipeline = translate_to_adk_pipeline(graph)
    routing_rules = pipeline["agents"]["orchestrator"]["routing_rules"]

    gate_rule = next((r for r in routing_rules if r["type"] == "qualification_gate"), None)
    assert gate_rule is not None
    assert gate_rule["node_id"] == "gate-1"

    intent_rule = next((r for r in routing_rules if r["type"] == "intent_router"), None)
    assert intent_rule is not None
    assert len(intent_rule["routes"]) == 2
    assert intent_rule["routes"][0]["intent"] == "complaint"
