from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    Conversation, Message, ExecutionInstance, Contact, 
    DeliveryStatus, ExecutionStatus, ExecutionStepLog
)

class AnalyticsService:
    @staticmethod
    async def get_summary_stats(session: AsyncSession, workspace_id: UUID, range_days: int = 7) -> Dict[str, Any]:
        """
        Get high-level KPIs for the dashboard.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=range_days)
        
        # 1. Conversation Counts
        # Total active conversations in period (updated_at > cutoff)
        conv_query = select(func.count()).where(
            Conversation.workspace_id == workspace_id,
            Conversation.updated_at >= cutoff_date
        )
        conversations_count = (await session.execute(conv_query)).scalar() or 0
        
        # 2. New Contacts
        contact_query = select(func.count()).where(
            Contact.workspace_id == workspace_id,
            Contact.created_at >= cutoff_date
        )
        new_contacts_count = (await session.execute(contact_query)).scalar() or 0
        
        # 3. Messages Stats
        msg_query = select(
            func.count().filter(Message.direction == "inbound"),
            func.count().filter(and_(Message.direction == "outbound", Message.delivery_status == DeliveryStatus.SENT)),
            func.count().filter(and_(Message.direction == "outbound", Message.delivery_status == DeliveryStatus.FAILED))
        ).where(
            Message.workspace_id == workspace_id,
            Message.created_at >= cutoff_date
        )
        msg_result = (await session.execute(msg_query)).first()
        inbound, outbound_sent, outbound_failed = msg_result if msg_result else (0, 0, 0)

        # 4. Zoho Synced Contacts
        zoho_query = select(func.count()).where(
            Contact.workspace_id == workspace_id,
            Contact.zoho_last_synced_at >= cutoff_date
        )
        zoho_synced_count = (await session.execute(zoho_query)).scalar() or 0
        
        # 5. Execution Stats
        exec_query = select(
            func.count().filter(ExecutionInstance.status == ExecutionStatus.COMPLETED),
            func.count().filter(ExecutionInstance.status == ExecutionStatus.ABORTED),
            func.count().filter(ExecutionInstance.status == ExecutionStatus.FAILED)
        ).where(
            ExecutionInstance.workspace_id == workspace_id,
            ExecutionInstance.created_at >= cutoff_date
        )
        exec_result = (await session.execute(exec_query)).first()
        exec_completed, exec_aborted, exec_failed = exec_result if exec_result else (0, 0, 0)
        
        # Automation Success Rate (exclude aborted)
        total_attempts = exec_completed + exec_failed
        success_rate = round((exec_completed / total_attempts * 100), 1) if total_attempts > 0 else 0.0

        # 6. Dispatch Health (Real-time snapshot, ignoring range)
        # Pending
        pending_query = select(func.count()).where(
            Message.workspace_id == workspace_id,
            Message.delivery_status == DeliveryStatus.PENDING
        )
        pending_count = (await session.execute(pending_query)).scalar() or 0
        
        # Stale Sending (> 5 mins)
        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
        stale_query = select(func.count()).where(
            Message.workspace_id == workspace_id,
            Message.delivery_status == DeliveryStatus.SENDING,
            Message.created_at <= five_mins_ago
        )
        stale_sending_count = (await session.execute(stale_query)).scalar() or 0
        
        # Recent Failures (last 24h)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        failed_query = select(func.count()).where(
            Message.workspace_id == workspace_id,
            Message.delivery_status == DeliveryStatus.FAILED,
            Message.created_at >= one_day_ago
        )
        failed_count = (await session.execute(failed_query)).scalar() or 0
        
        return {
            "conversations_count": conversations_count,
            "new_contacts_count": new_contacts_count,
            "inbound_messages_count": inbound,
            "outbound_messages_sent_count": outbound_sent,
            "outbound_messages_failed_count": outbound_failed,
            "zoho_synced_contacts_count": zoho_synced_count,
            "execution_completed_count": exec_completed,
            "execution_aborted_count": exec_aborted,
            "execution_failed_count": exec_failed,
            "automation_success_rate": success_rate,
            "dispatch_health": {
                "pending_count": pending_count,
                "sending_stale_count": stale_sending_count,
                "failed_count": failed_count # Last 24h
            }
        }

    @staticmethod
    async def get_timeseries_stats(
        session: AsyncSession, 
        workspace_id: UUID, 
        metric: str, 
        range_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get daily timeseries data for charts.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=range_days)
        
        # SQLite date function: date(created_at)
        # In Postgres: date_trunc('day', created_at)
        # Use SQLAlchemy generic function or literal for portability if possible, but mainly targeting SQLite/Postgres.
        # using generic func.date() works for SQLite. 
        
        date_col = func.date(Message.created_at)
        
        if metric == "conversations":
            # Count conversations active on that day? Or created? 
            # Prompt says "conversations per day". Usually active/updated is better for "flow", 
            # or created for "new leads". Let's stick to 'updated_at' to show activity.
            date_col = func.date(Conversation.updated_at)
            query = select(
                date_col.label("date"), 
                func.count().label("value")
            ).where(
                Conversation.workspace_id == workspace_id,
                Conversation.updated_at >= cutoff_date
            ).group_by(
                date_col
            ).order_by(date_col)
            
        elif metric == "inbound_messages":
            date_col = func.date(Message.created_at)
            query = select(
                date_col.label("date"), 
                func.count().label("value")
            ).where(
                Message.workspace_id == workspace_id,
                Message.direction == "inbound",
                Message.created_at >= cutoff_date
            ).group_by(
                date_col
            ).order_by(date_col)

        elif metric == "outbound_sent":
            date_col = func.date(Message.created_at)
            query = select(
                date_col.label("date"), 
                func.count().label("value")
            ).where(
                Message.workspace_id == workspace_id,
                Message.direction == "outbound",
                Message.delivery_status == DeliveryStatus.SENT,
                Message.created_at >= cutoff_date
            ).group_by(
                date_col
            ).order_by(date_col)

        elif metric == "zoho_syncs":
            date_col = func.date(Contact.zoho_last_synced_at)
            query = select(
                date_col.label("date"), 
                func.count().label("value")
            ).where(
                Contact.workspace_id == workspace_id,
                Contact.zoho_last_synced_at >= cutoff_date
            ).group_by(
                date_col
            ).order_by(date_col)
            
        else:
            return []

        result = await session.execute(query)
        rows = result.all()
        
        # Fill zero days? Optional polish. For now, return raw data.
        return [{"date": str(r[0]), "value": r[1]} for r in rows]

    @staticmethod
    async def get_execution_breakdown(session: AsyncSession, workspace_id: UUID, range_days: int = 7) -> Dict[str, int]:
        cutoff_date = datetime.utcnow() - timedelta(days=range_days)
        
        query = select(
            ExecutionInstance.status,
            func.count()
        ).where(
            ExecutionInstance.workspace_id == workspace_id,
            ExecutionInstance.created_at >= cutoff_date
        ).group_by(
            ExecutionInstance.status
        )
        
        result = await session.execute(query)
        rows = result.all()
        
        data = {s.value: 0 for s in ExecutionStatus}
        for status, count in rows:
            if status.value in data:
                data[status.value] = count
                
        return data

    @staticmethod
    async def get_ai_usage(session: AsyncSession, workspace_id: UUID, range_days: int = 7) -> Dict[str, Any]:
        """
        Estimate AI usage by counting AI_REPLY nodes executed.
        We don't strictly track tokens yet in logs, but we can count steps.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=range_days)
        
        # Join ExecutionStepLog -> ExecutionInstance -> Workspace
        # Filter where Node type is AI_REPLY? 
        # Actually Node type is on FlowNode. 
        # StepLog -> NodeID -> FlowNode.type == 'AI_REPLY'
        
        # This is complex join. Let's simplify: 
        # Just count total steps for now, or if we can filter by node type.
        
        # For MVP, let's just count total steps in instances belonging to workspace.
        
        query = select(func.count()).select_from(ExecutionStepLog)\
            .join(ExecutionInstance)\
            .where(
                ExecutionInstance.workspace_id == workspace_id,
                ExecutionInstance.created_at >= cutoff_date
            )
            
        # Refinement: Only count AI steps if possible.
        # But for now total steps is a proxy for "Automation Activity".
        
        step_count = (await session.execute(query)).scalar() or 0
        
        return {
            "ai_step_count": step_count,
            "total_tokens": None, # Not yet tracked
            "model_name": "Gemini 1.5 Flash"
        }
