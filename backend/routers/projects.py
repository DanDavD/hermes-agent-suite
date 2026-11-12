"""Claude-style Projects router (/api/projects)."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from backend.database import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from backend.models.schemas import ProjectCreate, ProjectSchema, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectSchema])
async def get_all_projects() -> List[Dict[str, Any]]:
    """Lists all projects with their session counts."""
    return list_projects()


@router.post("", response_model=ProjectSchema)
async def create_new_project(payload: ProjectCreate) -> Dict[str, Any]:
    """Creates a new project with optional local workspace path and description."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Project name is required.")
    return create_project(
        name=payload.name,
        workspace_path=payload.workspace_path or "",
        description=payload.description or "",
    )


@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project_by_id(project_id: str) -> Dict[str, Any]:
    """Retrieves a single project by ID."""
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return proj


@router.patch("/{project_id}", response_model=ProjectSchema)
@router.put("/{project_id}", response_model=ProjectSchema)
async def update_project_by_id(
    project_id: str, payload: ProjectUpdate
) -> Dict[str, Any]:
    """Updates project name, description, or local workspace path."""
    updated = update_project(
        project_id=project_id,
        name=payload.name,
        workspace_path=payload.workspace_path,
        description=payload.description,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return updated


@router.delete("/{project_id}")
async def delete_project_by_id(project_id: str) -> Dict[str, Any]:
    """Deletes a project and unlinks its sessions."""
    deleted = delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return {"success": True, "deleted_id": project_id}
