from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Any
from uuid import UUID

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, Message, DeliveryStatus
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.services.dispatch_service import DispatchService
from app.core.modules import require_module_enabled, MODULE_DISPATCH_ENGINE

router = APIRouter()

@router.post("/run", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_DISPATCH_ENGINE, "write"))])
async def trigger_dispatch(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member"]))
) -> Any:
    """Manually trigger dispatch for current workspace."""
    processed, failed = await DispatchService.dispatch_pending_messages(db, workspace_id=workspace.id)
    return wrap_data({
        "processed_count": processed,
        "failed_count": failed
    })

@router.get("/queue", response_model=ResponseEnvelope[List[dict]], dependencies=[Depends(require_module_enabled(MODULE_DISPATCH_ENGINE, "read"))])
async def get_dispatch_queue(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member"]))
) -> Any:
    """Returns latest 50 outbound messages with statuses."""
    result = await db.execute(
        select(Message)
        .where(Message.workspace_id == workspace.id, Message.direction == "outbound")
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    messages = result.scalars().all()
    
    # Format for UI
    output = []
    for m in messages:
        output.append({
            "id": str(m.id),
            "content": m.content[:50] + "..." if len(m.content) > 50 else m.content,
            "status": m.delivery_status,
            "attempts": m.attempt_count,
            "last_error": m.last_error,
            "platform": m.platform,
            "created_at": m.created_at.isoformat()
        })
    
    return wrap_data(output)
