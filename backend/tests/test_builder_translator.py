"""
Unit tests for the builder translator (Mission 27).
No DB required — pure logic tests.
"""
import pytest
from app.domain.builder_translator import validate_graph, translate, simulate

# ---------------------------------------------------------------------------
# Helpers
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

def make_edge(edge_id, source, target):
    return {"id": edge_id, "source": source, "target": target}

def make_valid_graph():
    return {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "AI_REPLY", {"goal": "Help user", "tasks": []}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }


# ---------------------------------------------------------------------------
# validate_graph tests
# ---------------------------------------------------------------------------

def test_validate_graph_valid():
    """A well-formed graph with a trigger and a valid AI_REPLY should pass."""
    errors = validate_graph(make_valid_graph())
    assert errors == []


def test_validate_graph_no_nodes():
    """Empty graph should return an error."""
    errors = validate_graph({"nodes": [], "edges": []})
    assert len(errors) == 1
    assert "node" in errors[0]["message"].lower()


def test_validate_graph_no_trigger():
    """Graph without a trigger node should return an error."""
    graph = {
        "nodes": [make_action_node("node-1", "AI_REPLY", {"goal": "test"})],
        "edges": [],
    }
    errors = validate_graph(graph)
    assert any("trigger" in e["message"].lower() for e in errors)


def test_validate_graph_multiple_triggers():
    """Graph with two trigger nodes should return an error for the second."""
    graph = {
        "nodes": [
            make_trigger_node("trigger-1"),
            make_trigger_node("trigger-2"),
            make_action_node("node-1", "SEND_MESSAGE", {"content": "Hello"}),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "node-1"),
            make_edge("e2", "trigger-2", "node-1"),
        ],
    }
    errors = validate_graph(graph)
    assert any("one trigger" in e["message"].lower() for e in errors)


def test_validate_graph_ai_reply_missing_goal():
    """AI_REPLY node without goal should return a field-specific error."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "AI_REPLY", {"goal": ""}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert any(e["node_id"] == "node-1" and "goal" in e["field"] for e in errors)


def test_validate_graph_send_message_missing_content():
    """SEND_MESSAGE without content should return an error."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "SEND_MESSAGE", {"content": ""}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert any(e["node_id"] == "node-1" and "content" in e["field"] for e in errors)


def test_validate_graph_tag_contact_missing_tag():
    """TAG_CONTACT without tag should return an error."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "TAG_CONTACT", {"tag": ""}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert any(e["node_id"] == "node-1" for e in errors)


def test_validate_graph_condition_node_requires_config():
    """CONDITION node without condition_type should return a config error (not a 'not supported' error)."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "CONDITION", {}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    # Should have config errors, NOT a "not yet supported" error
    assert any(e["node_id"] == "node-1" for e in errors)
    assert not any("not yet supported" in e["message"] for e in errors)
    assert any("condition_type" in e.get("field", "") for e in errors)


def test_validate_graph_condition_node_valid():
    """CONDITION node with required config should pass validation."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "CONDITION", {
                "condition_type": "qualification_status",
                "operator": "equals",
                "value": "qualified",
            }),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert errors == []


def test_validate_graph_wait_delay_requires_delay_seconds():
    """WAIT_DELAY node without delay_seconds should return a config error (not 'not supported')."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "WAIT_DELAY", {}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert any(e["node_id"] == "node-1" for e in errors)
    assert not any("not yet supported" in e["message"] for e in errors)
    assert any("delay_seconds" in e.get("field", "") for e in errors)


def test_validate_graph_wait_delay_valid():
    """WAIT_DELAY node with sufficient delay_seconds should pass."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "WAIT_DELAY", {"delay_seconds": 3600}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
    }
    errors = validate_graph(graph)
    assert errors == []


def test_validate_graph_disconnected_node():
    """Action node not connected to trigger should return a reachability error."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("node-1", "AI_REPLY", {"goal": "test"}),
            make_action_node("orphan", "SEND_MESSAGE", {"content": "Hello"}),
        ],
        "edges": [make_edge("e1", "trigger-1", "node-1")],
        # "orphan" is not connected
    }
    errors = validate_graph(graph)
    assert any(e["node_id"] == "orphan" and "not connected" in e["message"] for e in errors)


def test_validate_graph_lead_ad_submit_trigger():
    """LEAD_AD_SUBMIT trigger type should be valid."""
    graph = {
        "nodes": [
            make_trigger_node("t1", "LEAD_AD_SUBMIT", "meta"),
            make_action_node("node-1", "AI_REPLY", {"goal": "Qualify lead"}),
        ],
        "edges": [make_edge("e1", "t1", "node-1")],
    }
    errors = validate_graph(graph)
    assert errors == []


# ---------------------------------------------------------------------------
# translate tests
# ---------------------------------------------------------------------------

def test_translate_produces_valid_contract():
    """translate() should produce a valid runtime definition_json (first tuple element)."""
    graph = make_valid_graph()
    definition, adk_pipeline = translate(graph)

    assert "nodes" in definition
    assert "edges" in definition
    assert "start_node_id" in definition
    assert definition["start_node_id"] == "trigger-1"

    # Trigger node
    trigger = next(n for n in definition["nodes"] if n["type"] == "TRIGGER")
    assert trigger["id"] == "trigger-1"
    assert trigger["config"]["trigger_type"] == "MESSAGE_INBOUND"
    assert trigger["config"]["platform"] == "whatsapp"

    # Action node
    action = next(n for n in definition["nodes"] if n["type"] == "AI_REPLY")
    assert action["config"]["goal"] == "Help user"

    # Edge
    assert len(definition["edges"]) == 1
    edge = definition["edges"][0]
    assert edge["source_node_id"] == "trigger-1"
    assert edge["target_node_id"] == "node-1"

    # ADK pipeline also returned
    assert "pipeline_type" in adk_pipeline
    assert adk_pipeline["pipeline_type"] == "orchestrated"


def test_translate_sets_start_node_id():
    """start_node_id in output should match the trigger node id."""
    graph = {
        "nodes": [
            make_trigger_node("my-trigger"),
            make_action_node("step-1", "SEND_MESSAGE", {"content": "Hello"}),
        ],
        "edges": [make_edge("e1", "my-trigger", "step-1")],
    }
    definition, _ = translate(graph)
    assert definition["start_node_id"] == "my-trigger"


def test_translate_edge_format():
    """Edges in runtime format should use source_node_id and target_node_id."""
    graph = make_valid_graph()
    definition, _ = translate(graph)
    edge = definition["edges"][0]
    assert "source_node_id" in edge
    assert "target_node_id" in edge
    assert "source" not in edge  # React Flow format stripped


def test_translate_multiple_nodes():
    """Multiple action nodes should all be translated correctly."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("n1", "AI_REPLY", {"goal": "Greet"}),
            make_action_node("n2", "ZOHO_UPSERT_LEAD", {}),
            make_action_node("n3", "HUMAN_HANDOVER", {}),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "n1"),
            make_edge("e2", "n1", "n2"),
            make_edge("e3", "n2", "n3"),
        ],
    }
    definition, _ = translate(graph)
    assert len(definition["nodes"]) == 4
    assert len(definition["edges"]) == 3
    types = {n["type"] for n in definition["nodes"]}
    assert "TRIGGER" in types
    assert "AI_REPLY" in types
    assert "ZOHO_UPSERT_LEAD" in types


# ---------------------------------------------------------------------------
# simulate tests
# ---------------------------------------------------------------------------

def test_simulate_returns_steps():
    """simulate() should return a steps array for a valid graph."""
    graph = make_valid_graph()
    result = simulate(graph)
    assert "steps" in result
    assert len(result["steps"]) >= 1
    assert result["dispatch_blocked"] is True


def test_simulate_no_dispatch_side_effects():
    """simulate() should explicitly mark dispatch as blocked."""
    graph = make_valid_graph()
    result = simulate(graph)
    assert result["dispatch_blocked"] is True
    # All steps with dispatch info should have it blocked
    for step in result["steps"]:
        if "would_dispatch" in step:
            assert step["would_dispatch"] is False


def test_simulate_empty_graph():
    """simulate() with no trigger should return empty steps with message."""
    graph = {"nodes": [], "edges": []}
    result = simulate(graph)
    assert result["steps"] == []
    assert "No trigger" in result["message"]


def test_simulate_with_mock_payload():
    """simulate() should include mock payload in trigger step."""
    graph = make_valid_graph()
    mock = {"content": "Hello!", "sender": "+1234567890"}
    result = simulate(graph, mock_payload=mock)
    trigger_step = next(
        (s for s in result["steps"] if s["node_type"] in ("MESSAGE_INBOUND", "LEAD_AD_SUBMIT")),
        None
    )
    if trigger_step:
        assert "mock_payload" in trigger_step


def test_simulate_send_message_shows_content():
    """Simulate should show SEND_MESSAGE content in would_send field."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("n1", "SEND_MESSAGE", {"content": "Welcome!"}),
        ],
        "edges": [make_edge("e1", "trigger-1", "n1")],
    }
    result = simulate(graph)
    send_step = next(s for s in result["steps"] if s["node_type"] == "SEND_MESSAGE")
    assert send_step["would_send"] == "Welcome!"


def test_simulate_multiple_steps_in_order():
    """Simulate traversal should follow edges in order."""
    graph = {
        "nodes": [
            make_trigger_node(),
            make_action_node("n1", "AI_REPLY", {"goal": "Greet"}),
            make_action_node("n2", "TAG_CONTACT", {"tag": "interested"}),
        ],
        "edges": [
            make_edge("e1", "trigger-1", "n1"),
            make_edge("e2", "n1", "n2"),
        ],
    }
    result = simulate(graph)
    node_types = [s["node_type"] for s in result["steps"]]
    # Trigger comes first, then AI_REPLY, then TAG_CONTACT
    assert node_types.index("AI_REPLY") < node_types.index("TAG_CONTACT")
