"""
ADK callback handler — Mission M-E.

LeadPilotCallbackHandler wires ADK agent lifecycle events into the existing
RuntimeEventLog system. Instantiated once per run_for_contact() call.

Callback conventions (google-adk 1.27.3):
- before_agent_callback(*, callback_context)
- after_agent_callback(*, callback_context)
- before_model_callback(*, callback_context, llm_request)
- after_model_callback(*, callback_context, llm_response)
- before_tool_callback(*, tool, args, tool_context)
- after_tool_callback(*, tool, args, tool_context, tool_response)
All are called with keyword arguments and may return None (no override).
"""
import time
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.runtime_event_service import log_event
from app.services.metrics_service import metrics

_SENSITIVE_KEYS = frozenset({"access_token", "api_key", "password", "token", "secret"})


def _redact_sensitive(args: dict) -> dict:
    """Remove sensitive fields from tool args before logging."""
    return {k: "***" if k.lower() in _SENSITIVE_KEYS else v for k, v in args.items()}


class LeadPilotCallbackHandler:
    """
    Maps ADK lifecycle callbacks to RuntimeEventLog entries.
    Instantiated per run_for_contact() call with workspace/instance context.
    """

    def __init__(self, workspace_id: str, instance_id: str, db_session: AsyncSession):
        self.workspace_id = workspace_id
        self.instance_id = instance_id
        self.session = db_session
        self._agent_start_times: dict[str, float] = {}

    # ─── Agent callbacks ─────────────────────────────────────────────────────

    async def before_agent(self, *, callback_context) -> None:
        agent_name = getattr(callback_context, "agent_name", "unknown")
        self._agent_start_times[agent_name] = time.time()
        await log_event(
            self.session,
            event_type=f"agent.{agent_name}.started",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"agent_name": agent_name},
        )

    async def after_agent(self, *, callback_context) -> None:
        agent_name = getattr(callback_context, "agent_name", "unknown")
        duration_ms = int(
            (time.time() - self._agent_start_times.get(agent_name, time.time())) * 1000
        )
        await log_event(
            self.session,
            event_type=f"agent.{agent_name}.completed",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            duration_ms=duration_ms,
            related_ids={"execution_instance_id": self.instance_id},
            payload={"agent_name": agent_name},
        )

    # ─── Model callbacks ─────────────────────────────────────────────────────

    async def before_model(self, *, callback_context, llm_request) -> None:
        model = getattr(llm_request, "model", None)
        contents = getattr(llm_request, "contents", None) or []
        tools_dict = getattr(llm_request, "tools_dict", None) or {}
        await log_event(
            self.session,
            event_type="agent.llm_request",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            related_ids={"execution_instance_id": self.instance_id},
            payload={
                "model": model,
                "message_count": len(contents),
                "tool_count": len(tools_dict),
            },
        )

    async def after_model(self, *, callback_context, llm_response) -> None:
        usage = getattr(llm_response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None
        finish_reason = getattr(llm_response, "finish_reason", None)

        await log_event(
            self.session,
            event_type="agent.llm_response",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            related_ids={"execution_instance_id": self.instance_id},
            payload={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "finish_reason": str(finish_reason) if finish_reason else None,
            },
        )
        # Track token usage in metrics
        if total_tokens is not None:
            metrics.gauge("agent.avg_tokens_per_turn", total_tokens)

    # ─── Tool callbacks ──────────────────────────────────────────────────────

    async def before_tool(self, *, tool, args: dict, tool_context) -> None:
        tool_name = getattr(tool, "name", str(tool))
        await log_event(
            self.session,
            event_type=f"tool.{tool_name}.started",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"tool_name": tool_name, "args": _redact_sensitive(args)},
        )
        metrics.increment("agent.tool_calls", labels={"tool": tool_name})

    async def after_tool(self, *, tool, args: dict, tool_context, tool_response) -> None:
        tool_name = getattr(tool, "name", str(tool))
        result_fields = (
            list(tool_response.keys()) if isinstance(tool_response, dict) else None
        )
        await log_event(
            self.session,
            event_type=f"tool.{tool_name}.completed",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"tool_name": tool_name, "result_fields": result_fields},
        )

    # ─── Error callbacks ─────────────────────────────────────────────────────

    async def on_model_error(self, *, callback_context, llm_request, error: Exception) -> None:
        await log_event(
            self.session,
            event_type="agent.error",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            outcome="failure",
            error_message=str(error),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"error_type": type(error).__name__, "phase": "llm"},
        )

    async def on_tool_error(self, *, tool, args: dict, tool_context, error: Exception) -> None:
        tool_name = getattr(tool, "name", str(tool))
        await log_event(
            self.session,
            event_type="agent.error",
            source="adk",
            workspace_id=_to_uuid(self.workspace_id),
            outcome="failure",
            error_message=str(error),
            related_ids={"execution_instance_id": self.instance_id},
            payload={"error_type": type(error).__name__, "phase": "tool", "tool_name": tool_name},
        )


def _to_uuid(value: str) -> Optional[UUID]:
    """Safely convert a string to UUID for log_event workspace_id arg."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None
