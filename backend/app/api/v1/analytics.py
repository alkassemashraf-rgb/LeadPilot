from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import select, func, text, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Date, cast, String

from app.core.db import get_db
from app.api import deps
from app.schemas.envelope import ResponseEnvelope, wrap_data
from app.models.models import (
    User, Workspace, Conversation, Message, Contact, 
    ExecutionInstance, ExecutionStepLog, DeliveryStatus, 
    ExecutionStatus, WorkspaceRole, FlowNode
)
from app.core.modules import require_module_enabled, MODULE_ANALYTICS

router = APIRouter()

# --- Response Models ---

@router.get("/summary", response_model=ResponseEnvelope, dependencies=[Depends(require_module_enabled(MODULE_ANALYTICS, "read"))])
async def get_analytics_summary(
    range_days: int = Query(7, alias="range", ge=1, le=90),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns summary KPIs for the specified range.
    """
    workspace_id = workspace.id
    start_date = datetime.utcnow() - timedelta(days=range_days)
    
    # helper for executing scalar count queries
    async def get_count(stmt):
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    # 1. Conversations & Contacts
    conversations_count = await get_count(
        select(func.count(Conversation.id))
        .where(Conversation.workspace_id == workspace_id)
        .where(Conversation.updated_at >= start_date)
    )
    
    new_contacts_count = await get_count(
        select(func.count(Contact.id))
        .where(Contact.workspace_id == workspace_id)
        .where(Contact.created_at >= start_date)
    )
    
    # Inbound Messages
    inbound_messages_count = await get_count(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .where(Message.direction == "inbound")
        .where(Message.created_at >= start_date)
    )
    
    # Outbound Messages (Sent vs Failed)
    outbound_stats_res = await session.execute(
        select(
            func.count(case((Message.delivery_status == DeliveryStatus.SENT, 1))),
            func.count(case((Message.delivery_status == DeliveryStatus.FAILED, 1)))
        )
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .where(Message.direction == "outbound")
        .where(Message.created_at >= start_date)
    )
    outbound_stats = outbound_stats_res.one()
    outbound_sent_count = outbound_stats[0] or 0
    outbound_failed_count = outbound_stats[1] or 0
    
    # Zoho Synced Contacts
    zoho_synced_contacts_count = await get_count(
        select(func.count(Contact.id))
        .where(Contact.workspace_id == workspace_id)
        .where(Contact.zoho_last_synced_at >= start_date)
    )
    
    # Execution Stats
    exec_stats_res = await session.execute(
        select(
            func.count(case((ExecutionInstance.status == ExecutionStatus.COMPLETED, 1))),
            func.count(case((ExecutionInstance.status == ExecutionStatus.ABORTED, 1))),
            func.count(case((ExecutionInstance.status == ExecutionStatus.FAILED, 1)))
        )
        .where(ExecutionInstance.workspace_id == workspace_id)
        .where(ExecutionInstance.created_at >= start_date)
    )
    exec_stats = exec_stats_res.one()
    
    execution_completed = exec_stats[0] or 0
    execution_aborted = exec_stats[1] or 0
    execution_failed = exec_stats[2] or 0
    
    total_completed_failed = execution_completed + execution_failed
    automation_success_rate = 0.0
    if total_completed_failed > 0:
        automation_success_rate = (execution_completed / total_completed_failed) * 100
        
    # Dispatch Health
    pending_count = await get_count(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .where(Message.delivery_status == DeliveryStatus.PENDING)
    )
    
    health_failed_window = datetime.utcnow() - timedelta(hours=24)
    failed_count = await get_count(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .where(Message.delivery_status == DeliveryStatus.FAILED)
        .where(Message.created_at >= health_failed_window)
    )
    
    five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
    sending_stale_count = await get_count(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .where(Message.delivery_status == DeliveryStatus.SENDING)
        .where(Message.created_at <= five_mins_ago)
    )

    data = {
        "conversations_count": conversations_count,
        "new_contacts_count": new_contacts_count,
        "inbound_messages_count": inbound_messages_count,
        "outbound_messages_sent_count": outbound_sent_count,
        "outbound_messages_failed_count": outbound_failed_count,
        "zoho_synced_contacts_count": zoho_synced_contacts_count,
        "execution_completed_count": execution_completed,
        "execution_aborted_count": execution_aborted,
        "execution_failed_count": execution_failed,
        "automation_success_rate": round(automation_success_rate, 1),
        "dispatch_health": {
            "pending_count": pending_count,
            "sending_stale_count": sending_stale_count,
            "failed_count": failed_count
        }
    }
    return wrap_data(data)

@router.get("/timeseries", response_model=ResponseEnvelope, dependencies=[Depends(require_module_enabled(MODULE_ANALYTICS, "read"))])
async def get_analytics_timeseries(
    metric: str = Query(..., regex="^(conversations|inbound_messages|outbound_sent|zoho_syncs)$"),
    range_days: int = Query(7, alias="range", ge=1, le=90),
    bucket: str = Query("day", regex="^day$"),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns time series data for charts.
    """
    workspace_id = workspace.id
    # 1. Prepare Date Range (Zero-fill skeleton)
    dates: Dict[str, int] = {}
    today = datetime.utcnow().date()
    
    for i in range(range_days):
        d = today - timedelta(days=range_days - 1 - i)
        dates[d.isoformat()] = 0
        
    start_dt = datetime.combine(today - timedelta(days=range_days - 1), datetime.min.time())
    
    query = None
    
    # Use cast to String (first 10 chars YYYY-MM-DD) for broad compatibility in this stack
    # SQLite 'date()' returns string. Postgres cast(..., Date) returns date.
    # To be safe with 'fromisoformat' error, let's treat it as string or date object manually.
    
    if metric == "conversations":
        date_col = func.date(Conversation.updated_at)
        query = (
            select(
                date_col.label("date"),
                func.count(Conversation.id).label("value")
            )
            .where(Conversation.workspace_id == workspace_id)
            .where(Conversation.updated_at >= start_dt)
            .group_by(date_col)
            .order_by(date_col)
        )
        
    elif metric == "inbound_messages":
        date_col = func.date(Message.created_at)
        query = (
            select(
                date_col.label("date"),
                func.count(Message.id).label("value")
            )
            .join(Conversation)
            .where(Conversation.workspace_id == workspace_id)
            .where(Message.direction == "inbound")
            .where(Message.created_at >= start_dt)
            .group_by(date_col)
            .order_by(date_col)
        )
        
    elif metric == "outbound_sent":
        date_col = func.date(Message.created_at)
        query = (
            select(
                date_col.label("date"),
                func.count(Message.id).label("value")
            )
            .join(Conversation)
            .where(Conversation.workspace_id == workspace_id)
            .where(Message.direction == "outbound")
            .where(Message.delivery_status == DeliveryStatus.SENT)
            .where(Message.created_at >= start_dt)
            .group_by(date_col)
            .order_by(date_col)
        )
        
    elif metric == "zoho_syncs":
        date_col = func.date(Contact.zoho_last_synced_at)
        query = (
            select(
                date_col.label("date"),
                func.count(Contact.id).label("value")
            )
            .where(Contact.workspace_id == workspace_id)
            .where(Contact.zoho_last_synced_at >= start_dt)
            .group_by(date_col)
            .order_by(date_col)
        )
    
    result = await session.execute(query)
    rows = result.all()
    
    # Update skeleton with actual data
    for row in rows:
        d_val = row.date
        d_str = str(d_val) # Handles Date obj or String
        
        # If full timestamp returned (unlikely with func.date but possible), strip time
        if "T" in d_str:
            d_str = d_str.split("T")[0]
        elif " " in d_str:
            d_str = d_str.split(" ")[0]
            
        if d_str in dates:
            dates[d_str] = row.value
            
    # Convert back to list
    final_data = [{"date": d, "value": v} for d, v in dates.items()]
    
    return wrap_data(final_data)

@router.get("/executions/breakdown", response_model=ResponseEnvelope, dependencies=[Depends(require_module_enabled(MODULE_ANALYTICS, "read"))])
async def get_execution_breakdown(
    range_days: int = Query(7, alias="range", ge=1, le=90),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns breakdown of execution statuses.
    """
    workspace_id = workspace.id
    start_date = datetime.utcnow() - timedelta(days=range_days)
    
    result = await session.execute(
        select(ExecutionInstance.status, func.count(ExecutionInstance.id))
        .where(ExecutionInstance.workspace_id == workspace_id)
        .where(ExecutionInstance.created_at >= start_date)
        .group_by(ExecutionInstance.status)
    )
    rows = result.all()
    
    data = {s.value: 0 for s in ExecutionStatus}
    for status, count in rows:
        data[status.value] = count
        
    return wrap_data(data)

@router.get("/ai-usage", response_model=ResponseEnvelope, dependencies=[Depends(require_module_enabled(MODULE_ANALYTICS, "read"))])
async def get_ai_usage(
    range_days: int = Query(7, alias="range", ge=1, le=90),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns AI usage statistics.
    Filters implicitly for AI steps.
    """
    workspace_id = workspace.id
    start_date = datetime.utcnow() - timedelta(days=range_days)
    
    ai_node_types = ["ai_reply", "ai_classify", "llm", "generate"]
    
    result = await session.execute(
        select(func.count(ExecutionStepLog.id))
        .join(ExecutionInstance, ExecutionStepLog.execution_instance_id == ExecutionInstance.id)
        .join(FlowNode, ExecutionStepLog.node_id == FlowNode.id)
        .where(ExecutionInstance.workspace_id == workspace_id)
        .where(ExecutionStepLog.created_at >= start_date)
        .where(
            (FlowNode.type.in_(ai_node_types)) | 
            (FlowNode.type.like("%ai%")) |
            (FlowNode.type.like("%llm%"))
        )
    )
    step_count = result.scalar_one() or 0
    
    return wrap_data({
        "ai_step_count": step_count,
        "total_tokens": None,
        "model_name": "Gemini"
    })
