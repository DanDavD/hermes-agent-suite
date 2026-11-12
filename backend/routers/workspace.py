"""Workspace Context Scanner & Safe File Application Router (/api/workspace)."""

import asyncio
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    WorkspaceScanRequest,
    WorkspaceScanResponse,
    WorkspaceWriteFileRequest,
    WorkspaceWriteFileResponse,
)
from backend.services.workspace_scanner import scan_workspace, write_workspace_file

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.post("/pick-folder")
async def pick_folder_native_finder() -> Dict[str, Any]:
    """
    Opens the native macOS Finder folder selection dialog starting at ~/Documents/GitHub
    (or ~/Documents) and returns the selected folder path + scanned workspace metadata.
    """
    default_dir = Path.home() / "Documents" / "GitHub"
    if not default_dir.exists():
        default_dir = Path.home() / "Documents"
    if not default_dir.exists():
        default_dir = Path.home()

    applescript = (
        'tell application "SystemUIServer"\n'
        "    activate\n"
        f'    set chosenFolder to choose folder with prompt "Select Project Folder" default location (POSIX file "{str(default_dir)}")\n'
        "    return POSIX path of chosenFolder\n"
        "end tell"
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript",
            "-e",
            applescript,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return {"cancelled": True, "folder_path": ""}

        chosen_path = stdout.decode("utf-8").strip().rstrip("/")
        if not chosen_path:
            return {"cancelled": True, "folder_path": ""}

        scan_result = scan_workspace(
            folder_path=chosen_path,
            include_context=False,
        )
        return {
            "cancelled": False,
            "folder_path": chosen_path,
            "scan": scan_result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to open Finder dialog: {exc}"
        ) from exc


@router.post("/scan", response_model=WorkspaceScanResponse)
async def scan_local_workspace(payload: WorkspaceScanRequest) -> Dict[str, Any]:
    """
    Safely scans a local macOS directory (pruning Unity Library/Temp/Obj, .git, node_modules, .venv),
    indexes source files, and returns the file tree + token budget breakdown.
    """
    result = scan_workspace(
        folder_path=payload.folder_path,
        selected_files=payload.selected_files,
        include_context=payload.include_context,
    )
    return result


@router.post("/apply", response_model=WorkspaceWriteFileResponse)
async def apply_file_to_workspace(payload: WorkspaceWriteFileRequest) -> Dict[str, Any]:
    """
    Safely writes or updates a generated source file inside the linked workspace directory.
    Blocks '..' path traversal or writing outside the workspace root.
    """
    try:
        return write_workspace_file(
            folder_path=payload.folder_path,
            relative_path=payload.relative_path,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to write workspace file: {exc}"
        ) from exc
