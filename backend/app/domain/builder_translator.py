"""
Builder Translator — Mission 27

Converts builder_graph_json (React Flow native format) into the runtime
definition_json contract, validates graphs before publish, and simulates
traversal without side effects.

Builder graph format (stored in FlowDraft.builder_graph_json):
{
    "nodes": [
        {"id": "trigger-1", "type": "triggerNode", "position": {"x": 250, "y": 50},
         "data": {"nodeType": "MESSAGE_INBOUND", "platform": "whatsapp", "config": {}}},
        {"id": "node-2", "type": "actionNode", "position": {"x": 250, "y": 220},
         "data": {"nodeType": "AI_REPLY", "config": {"goal": "Help user", "tasks": []}}}
    ],
    "edges": [{"id": "e1", "source": "trigger-1", "target": "node-2"}]
}

Runtime definition_json format (stored in FlowVersion.definition_json):
{
    "start_node_id": "trigger-1",
    "nodes": [{"id": "...", "type": "TRIGGER", "config": {...}}, ...],
    "edges": [{"id": "...", "source_node_id": "...", "target_node_id": "...", "source_handle": null}]
}
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Trigger node types that map to runtime TRIGGER node type
TRIGGER_NODE_TYPES = {"MESSAGE_INBOUND", "LEAD_AD_SUBMIT"}

# Node types supported by the runtime engine
RUNTIME_SUPPORTED_NODE_TYPES = {
    "AI_REPLY", "SEND_MESSAGE", "HUMAN_HANDOVER",
    "TAG_CONTACT", "ZOHO_UPSERT_LEAD",
}

# Builder-only node types (visual palette only; blocked from publishing)
BUILDER_ONLY_NODE_TYPES = {"CONDITION", "WAIT_DELAY"}


def validate_graph(builder_graph: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Validate a builder_graph_json.
    Returns a list of validation errors: [{node_id, field, message}].
    Empty list means valid.
    """
    errors: list[dict[str, Any]] = []
    nodes: list[dict] = builder_graph.get("nodes", [])
    edges: list[dict] = builder_graph.get("edges", [])

    if not nodes:
        errors.append({"node_id": None, "field": "graph", "message": "Flow must have at least one node."})
        return errors

    # Identify trigger nodes
    trigger_nodes = [n for n in nodes if _get_node_type(n) in TRIGGER_NODE_TYPES]
    action_nodes = [n for n in nodes if _get_node_type(n) not in TRIGGER_NODE_TYPES]

    # Must have exactly one trigger
    if len(trigger_nodes) == 0:
        errors.append({
            "node_id": None,
            "field": "trigger",
            "message": "Flow must have exactly one trigger node (e.g. WhatsApp Message, Meta Lead Ads)."
        })
    elif len(trigger_nodes) > 1:
        for tn in trigger_nodes[1:]:
            errors.append({
                "node_id": tn.get("id"),
                "field": "trigger",
                "message": "Flow can only have one trigger node."
            })

    # Check builder-only (unsupported runtime) node types
    for node in nodes:
        nt = _get_node_type(node)
        if nt in BUILDER_ONLY_NODE_TYPES:
            errors.append({
                "node_id": node.get("id"),
                "field": "type",
                "message": f"Node type '{nt}' is not yet supported by the runtime engine — cannot publish. Remove it or replace it with a supported action."
            })

    # Build reachability set from trigger (BFS/DFS)
    if trigger_nodes:
        trigger_id = trigger_nodes[0].get("id")
        reachable = _reachable_nodes(trigger_id, edges)
        for node in action_nodes:
            nid = node.get("id")
            if nid not in reachable:
                errors.append({
                    "node_id": nid,
                    "field": "connection",
                    "message": "This node is not connected to the trigger. Every node must be reachable from the trigger."
                })

    # Trigger must have at least one outgoing edge
    if trigger_nodes:
        trigger_id = trigger_nodes[0].get("id")
        outgoing = [e for e in edges if e.get("source") == trigger_id]
        if not outgoing and action_nodes:
            errors.append({
                "node_id": trigger_id,
                "field": "edges",
                "message": "Trigger node has no outgoing connections. Connect it to at least one action."
            })

    # Per-type config validation
    for node in nodes:
        nt = _get_node_type(node)
        config = node.get("data", {}).get("config", {})
        nid = node.get("id")

        if nt == "AI_REPLY":
            goal = (config.get("goal") or "").strip()
            if not goal:
                errors.append({
                    "node_id": nid,
                    "field": "config.goal",
                    "message": "AI Reply node requires a 'Goal' — describe what the AI should accomplish."
                })

        elif nt == "SEND_MESSAGE":
            content = (config.get("content") or "").strip()
            if not content:
                errors.append({
                    "node_id": nid,
                    "field": "config.content",
                    "message": "Send Message node requires message content."
                })

        elif nt == "TAG_CONTACT":
            tag = (config.get("tag") or "").strip()
            if not tag:
                errors.append({
                    "node_id": nid,
                    "field": "config.tag",
                    "message": "Tag Contact node requires a tag name."
                })

    return errors


def translate(builder_graph: dict[str, Any]) -> dict[str, Any]:
    """
    Translate builder_graph_json to runtime definition_json.
    Must only be called after validate_graph() returns an empty list.
    Returns the definition_json ready for FlowVersion.definition_json.
    """
    nodes_in = builder_graph.get("nodes", [])
    edges_in = builder_graph.get("edges", [])

    runtime_nodes = []
    start_node_id: str | None = None

    for node in nodes_in:
        nid = node.get("id")
        node_type = _get_node_type(node)
        data = node.get("data", {})
        config = data.get("config", {})

        if node_type in TRIGGER_NODE_TYPES:
            # Trigger node → runtime TRIGGER type
            runtime_nodes.append({
                "id": nid,
                "type": "TRIGGER",
                "config": {
                    "trigger_type": node_type,
                    "platform": data.get("platform", config.get("platform", "whatsapp")),
                    "keywords": data.get("keywords", config.get("keywords", [])),
                },
            })
            start_node_id = nid
        else:
            # Action node → preserve type and config
            runtime_nodes.append({
                "id": nid,
                "type": node_type,
                "config": config,
            })

    runtime_edges = []
    for edge in edges_in:
        runtime_edges.append({
            "id": edge.get("id"),
            "source_node_id": edge.get("source"),
            "target_node_id": edge.get("target"),
            "source_handle": edge.get("sourceHandle"),
        })

    return {
        "start_node_id": start_node_id,
        "nodes": runtime_nodes,
        "edges": runtime_edges,
    }


def simulate(
    builder_graph: dict[str, Any],
    mock_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Dry-run traversal of builder_graph without any DB access or dispatch.
    Returns a preview of what each node would do.
    No Message rows, no provider adapter calls, no side effects.
    """
    nodes_in = builder_graph.get("nodes", [])
    edges_in = builder_graph.get("edges", [])

    node_map = {n.get("id"): n for n in nodes_in}
    edge_map: dict[str, list[str]] = {}
    for edge in edges_in:
        src = edge.get("source")
        if src not in edge_map:
            edge_map[src] = []
        edge_map[src].append(edge.get("target"))

    # Find trigger node
    trigger_nodes = [n for n in nodes_in if _get_node_type(n) in TRIGGER_NODE_TYPES]
    if not trigger_nodes:
        return {
            "steps": [],
            "dispatch_blocked": True,
            "message": "No trigger node found. Add a trigger to simulate the flow.",
        }

    steps = []
    current_id: str | None = trigger_nodes[0].get("id")
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        node = node_map.get(current_id)
        if not node:
            break

        node_type = _get_node_type(node)
        config = node.get("data", {}).get("config", {})

        step: dict[str, Any] = {
            "node_id": current_id,
            "node_type": node_type,
            "dispatch_blocked": True,
        }

        if node_type in TRIGGER_NODE_TYPES:
            step["description"] = f"Trigger: {node_type}"
            if mock_payload:
                step["mock_payload"] = mock_payload
        elif node_type == "AI_REPLY":
            step["description"] = "AI Reply — would generate a response using your workspace prompt configuration."
            step["goal"] = config.get("goal", "(no goal set)")
            step["would_dispatch"] = False
        elif node_type == "SEND_MESSAGE":
            content = config.get("content", "")
            step["description"] = "Send Message — would send the following message."
            step["would_send"] = content
            step["would_dispatch"] = False
        elif node_type == "HUMAN_HANDOVER":
            msg = config.get("announcement", "A team member will contact you.")
            step["description"] = "Human Handover — would transfer conversation to a human agent."
            step["announcement"] = msg
            step["would_dispatch"] = False
        elif node_type == "TAG_CONTACT":
            step["description"] = f"Tag Contact — would apply tag '{config.get('tag', '')}' to the contact."
        elif node_type == "ZOHO_UPSERT_LEAD":
            step["description"] = "Zoho CRM — would upsert the contact as a lead in Zoho CRM."
        elif node_type in BUILDER_ONLY_NODE_TYPES:
            step["description"] = f"{node_type} — not yet supported by runtime. This node would be skipped."
            step["warning"] = "Builder-only node type"
        else:
            step["description"] = f"Unknown node type: {node_type}"

        steps.append(step)

        next_nodes = edge_map.get(current_id, [])
        current_id = next_nodes[0] if next_nodes else None

    return {
        "steps": steps,
        "dispatch_blocked": True,
        "message": f"Simulation complete. {len(steps)} step(s) previewed. No messages were sent.",
    }


def _get_node_type(node: dict) -> str:
    """Extract the business logic node type from a builder node."""
    data = node.get("data", {})
    return data.get("nodeType", "")


def _reachable_nodes(start_id: str, edges: list[dict]) -> set[str]:
    """BFS to find all node IDs reachable from start_id via edges."""
    edge_map: dict[str, list[str]] = {}
    for edge in edges:
        src = edge.get("source")
        if src not in edge_map:
            edge_map[src] = []
        tgt = edge.get("target")
        if tgt:
            edge_map[src].append(tgt)

    visited: set[str] = set()
    queue = [start_id]
    while queue:
        node_id = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(edge_map.get(node_id, []))
    return visited
