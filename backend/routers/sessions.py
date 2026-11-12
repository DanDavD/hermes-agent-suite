"""Session management router (/api/sessions)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.database import (
    create_session,
    delete_session,
    get_session,
    list_sessions,
    update_session,
)
from backend.models.schemas import (
    SessionCreateRequest,
    SessionDetailResponse,
    SessionSummary,
    SessionUpdateRequest,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=List[SessionSummary])
async def get_all_sessions(
    project_id: Optional[str] = Query(default=None, description="Optional project ID filter"),
) -> List[Dict[str, Any]]:
    """Lists all chat sessions ordered by most recently updated, optionally filtered by project_id."""
    return list_sessions(project_id=project_id)


@router.post("", response_model=SessionDetailResponse)
async def create_new_session(payload: SessionCreateRequest) -> Dict[str, Any]:
    """Creates a new chat session (optionally bound to a project_id)."""
    return create_session(
        title=payload.title or "New Session",
        mode=payload.mode or "team:dev-squad",
        workspace_path=payload.workspace_path or "",
        project_id=payload.project_id or "",
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_by_id(session_id: str) -> Dict[str, Any]:
    """Retrieves a single session and its full message history."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session


@router.patch("/{session_id}", response_model=SessionDetailResponse)
@router.put("/{session_id}", response_model=SessionDetailResponse)
async def update_session_by_id(
    session_id: str, payload: SessionUpdateRequest
) -> Dict[str, Any]:
    """Updates session title, active mode, workspace path, or project_id."""
    updated = update_session(
        session_id=session_id,
        title=payload.title,
        mode=payload.mode,
        workspace_path=payload.workspace_path,
        project_id=payload.project_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return updated


@router.delete("/{session_id}")
async def delete_session_by_id(session_id: str) -> Dict[str, Any]:
    """Deletes a session and all of its messages."""
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"success": True, "deleted_id": session_id}
