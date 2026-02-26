from typing import List, Any, Optional
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, WorkspaceKnowledgeFile
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.modules import require_module_enabled, MODULE_KNOWLEDGE_FILES
from app.services.entitlements import require_entitlement

router = APIRouter()

STORAGE_DIR = "storage/knowledge"

@router.post("/files", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_KNOWLEDGE_FILES, "write")), Depends(require_entitlement("knowledge_files", increment=True))])
async def upload_knowledge_file(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Upload a file to the workspace knowledge base."""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    extension = os.path.splitext(file.filename)[1]
    storage_path = os.path.join(STORAGE_DIR, f"{file_id}{extension}")

    # Save file
    try:
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        return wrap_error(f"Failed to save file: {str(e)}")

    # Extract text for MVP (txt, md, json, csv)
    extracted_text = None
    if extension.lower() in [".txt", ".md", ".json", ".csv"]:
        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except Exception:
            pass # Extraction failed, keep as None

    knowledge_file = WorkspaceKnowledgeFile(
        id=uuid.UUID(file_id),
        workspace_id=workspace.id,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=os.path.getsize(storage_path),
        storage_path=storage_path,
        extracted_text=extracted_text,
        notes=notes
    )
    
    db.add(knowledge_file)
    await db.commit()
    await db.refresh(knowledge_file)

    return wrap_data({
        "id": str(knowledge_file.id),
        "filename": knowledge_file.filename,
        "extracted": extracted_text is not None
    })

@router.get("/files", response_model=ResponseEnvelope[List[dict]], dependencies=[Depends(require_module_enabled(MODULE_KNOWLEDGE_FILES, "read")), Depends(require_entitlement("knowledge_files"))])
async def list_knowledge_files(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """List all knowledge files for the active workspace."""
    result = await db.execute(
        select(WorkspaceKnowledgeFile).where(WorkspaceKnowledgeFile.workspace_id == workspace.id)
    )
    files = result.scalars().all()
    
    return wrap_data([
        {
            "id": str(f.id),
            "filename": f.filename,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "notes": f.notes,
            "created_at": f.created_at.isoformat()
        }
        for f in files
    ])

@router.delete("/files/{file_id}", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_KNOWLEDGE_FILES, "write")), Depends(require_entitlement("knowledge_files"))])
async def delete_knowledge_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Delete a knowledge file."""
    result = await db.execute(
        select(WorkspaceKnowledgeFile).where(
            WorkspaceKnowledgeFile.id == file_id, 
            WorkspaceKnowledgeFile.workspace_id == workspace.id
        )
    )
    kb_file = result.scalars().first()
    if not kb_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete from storage
    if os.path.exists(kb_file.storage_path):
        os.remove(kb_file.storage_path)

    await db.delete(kb_file)
    await db.commit()

    return wrap_data({"deleted": True})
