"""Workspace Context Scanner & Safe File Applicator for macOS / Unity C# / Python projects."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.config import MAX_SINGLE_FILE_BYTES, WORKSPACE_TOKEN_BUDGET

# Noisy Unity, Python, Node, and Git directories to prune automatically
PRUNED_DIRECTORIES: Set[str] = {
    "Library",
    "Temp",
    "Obj",
    "obj",
    "Build",
    "Builds",
    "Logs",
    "UserSettings",
    "Packages",
    "MemoryCaptures",
    "Recordings",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vs",
    ".vscode",
    "dist",
    "out",
    "target",
}

# Supported source file extensions mapped to human-readable language labels
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".cs": "C#",
    ".shader": "ShaderLab",
    ".compute": "Compute Shader",
    ".hlsl": "HLSL",
    ".cginc": "HLSL",
    ".uxml": "Unity UXML",
    ".uss": "Unity USS",
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".json": "JSON",
    ".md": "Markdown",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sh": "Shell",
}

# Priority order for context injection so core code scripts enter the prompt before config files
EXTENSION_PRIORITY: Dict[str, int] = {
    ".cs": 1,
    ".shader": 2,
    ".compute": 2,
    ".hlsl": 2,
    ".cginc": 2,
    ".uxml": 3,
    ".uss": 3,
    ".py": 4,
    ".ts": 5,
    ".tsx": 5,
    ".js": 6,
    ".jsx": 6,
    ".sh": 7,
    ".md": 8,
    ".yaml": 9,
    ".yml": 9,
    ".json": 10,
}

# Noisy lockfiles or generated JSON files to skip
IGNORED_FILENAMES: Set[str] = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "composer.lock",
    "Cargo.lock",
}

# System & credential directories strictly blocked from scanning or writing
RESTRICTED_SYSTEM_ROOTS: Set[str] = {
    "/",
    "/etc",
    "/private/etc",
    "/var",
    "/private/var",
    "/System",
    "/Library",
    "/bin",
    "/sbin",
    "/usr",
    "/dev",
    "/proc",
}

RESTRICTED_CREDENTIAL_DIRNAMES: Set[str] = {
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".docker",
}


def _check_restricted_path(base_path: Path) -> Optional[str]:
    """Returns an error string if base_path points to a restricted OS or credential directory."""
    resolved_str = str(base_path)
    if resolved_str in RESTRICTED_SYSTEM_ROOTS:
        return f"Scanning system root directory '{resolved_str}' is forbidden by security policy."
    for sys_root in ("/etc/", "/private/etc/", "/System/", "/bin/", "/sbin/", "/usr/"):
        if resolved_str.startswith(sys_root):
            return f"Scanning system directory '{resolved_str}' is forbidden by security policy."
    if any(part in RESTRICTED_CREDENTIAL_DIRNAMES for part in base_path.parts):
        return f"Scanning credential directory '{resolved_str}' is forbidden by security policy."
    return None


def estimate_tokens_from_bytes(size_bytes: int) -> int:
    """Approximates LLM token count from byte size (~4 bytes per token)."""
    return max(1, size_bytes // 4) if size_bytes > 0 else 0


def estimate_tokens_from_text(text: str) -> int:
    """Approximates LLM token count from string length (~4 chars per token)."""
    return max(1, len(text) // 4) if text else 0


def _detect_project_type(base_path: Path, lang_counts: Dict[str, int]) -> str:
    """Determines the high-level project type based on directory markers and languages."""
    if (base_path / "Assets").is_dir() and (base_path / "ProjectSettings").is_dir():
        return "Unity C# Project"
    if lang_counts.get("C#", 0) > 0 or lang_counts.get("ShaderLab", 0) > 0:
        return "Unity / C# Project"
    if (base_path / "pyproject.toml").is_file() or (base_path / "requirements.txt").is_file():
        return "Python Project"
    if (base_path / "package.json").is_file():
        return "TypeScript / Web Project"
    if lang_counts.get("Python", 0) > 0:
        return "Python Project"
    return "Software Workspace"


def scan_workspace(
    folder_path: str,
    selected_files: Optional[List[str]] = None,
    include_context: bool = False,
    token_budget: int = WORKSPACE_TOKEN_BUDGET,
) -> Dict[str, Any]:
    """
    Safely scans a local macOS directory, pruning noisy Unity/dev folders,
    indexing source files, and optionally assembling the XML context block.
    """
    raw_path = (folder_path or "").strip()
    if not raw_path:
        return {
            "folder_path": "",
            "workspace_path": "",
            "valid": False,
            "error": "Workspace path is empty.",
            "project_type": "Unknown",
            "total_files": 0,
            "total_size_bytes": 0,
            "total_estimated_tokens": 0,
            "capped_tokens": 0,
            "token_budget": token_budget,
            "files": [],
            "language_breakdown": {},
            "pruned_dirs": sorted(PRUNED_DIRECTORIES),
            "context_preview": None,
        }

    try:
        base_path = Path(raw_path).expanduser().resolve()
    except Exception as exc:
        return {
            "folder_path": raw_path,
            "workspace_path": raw_path,
            "valid": False,
            "error": f"Invalid directory path: {exc}",
            "project_type": "Unknown",
            "total_files": 0,
            "total_size_bytes": 0,
            "total_estimated_tokens": 0,
            "capped_tokens": 0,
            "token_budget": token_budget,
            "files": [],
            "language_breakdown": {},
            "pruned_dirs": sorted(PRUNED_DIRECTORIES),
            "context_preview": None,
        }

    if not base_path.exists():
        return {
            "folder_path": str(base_path),
            "workspace_path": str(base_path),
            "valid": False,
            "error": f"Directory does not exist: {base_path}",
            "project_type": "Unknown",
            "total_files": 0,
            "total_size_bytes": 0,
            "total_estimated_tokens": 0,
            "capped_tokens": 0,
            "token_budget": token_budget,
            "files": [],
            "language_breakdown": {},
            "pruned_dirs": sorted(PRUNED_DIRECTORIES),
            "context_preview": None,
        }

    if not base_path.is_dir():
        return {
            "folder_path": str(base_path),
            "workspace_path": str(base_path),
            "path": str(base_path),
            "project_name": base_path.name,
            "is_unity_project": False,
            "valid": False,
            "error": f"Path is not a directory: {base_path}",
            "project_type": "Unknown",
            "summary": "Unknown",
            "total_files": 0,
            "included_files": 0,
            "total_size_bytes": 0,
            "total_estimated_tokens": 0,
            "capped_tokens": 0,
            "total_tokens": 0,
            "token_budget": token_budget,
            "files": [],
            "language_breakdown": {},
            "pruned_dirs": sorted(PRUNED_DIRECTORIES),
            "context_preview": None,
        }

    security_err = _check_restricted_path(base_path)
    if security_err:
        return {
            "folder_path": str(base_path),
            "workspace_path": str(base_path),
            "path": str(base_path),
            "project_name": base_path.name or str(base_path),
            "is_unity_project": False,
            "valid": False,
            "error": security_err,
            "project_type": "Restricted",
            "summary": "Restricted",
            "total_files": 0,
            "included_files": 0,
            "total_size_bytes": 0,
            "total_estimated_tokens": 0,
            "capped_tokens": 0,
            "total_tokens": 0,
            "token_budget": token_budget,
            "files": [],
            "language_breakdown": {},
            "pruned_dirs": sorted(PRUNED_DIRECTORIES),
            "context_preview": None,
        }

    indexed_files: List[Dict[str, Any]] = []
    language_breakdown: Dict[str, int] = {}
    total_size = 0
    total_tokens = 0
    pruned_encountered: Set[str] = set()

    for root, dirs, files in os.walk(base_path, topdown=True, followlinks=False):
        # Prune noisy directories in-place
        kept_dirs: List[str] = []
        for d in dirs:
            if d in PRUNED_DIRECTORIES or (d.startswith(".") and d != ".github"):
                pruned_encountered.add(d)
            else:
                kept_dirs.append(d)
        dirs[:] = sorted(kept_dirs)

        for fname in sorted(files):
            if fname in IGNORED_FILENAMES or fname.startswith("."):
                continue

            ext = Path(fname).suffix.lower()
            if ext not in EXTENSION_LANGUAGE_MAP:
                continue

            full_file_path = Path(root) / fname
            try:
                stat = full_file_path.stat()
            except OSError:
                continue

            if stat.st_size > MAX_SINGLE_FILE_BYTES or stat.st_size == 0:
                continue

            rel_path = full_file_path.relative_to(base_path).as_posix()
            lang = EXTENSION_LANGUAGE_MAP[ext]
            est_tokens = estimate_tokens_from_bytes(stat.st_size)

            indexed_files.append(
                {
                    "path": rel_path,
                    "relative_path": rel_path,
                    "name": fname,
                    "extension": ext,
                    "size": stat.st_size,
                    "size_bytes": stat.st_size,
                    "language": lang,
                    "category": lang,
                    "estimated_tokens": est_tokens,
                    "tokens": est_tokens,
                    "included": True if not selected_files else (rel_path in selected_files),
                }
            )
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1
            total_size += stat.st_size
            total_tokens += est_tokens

    project_type = _detect_project_type(base_path, language_breakdown)
    is_unity = "unity" in project_type.lower() or language_breakdown.get("C#", 0) > 0
    capped_tokens = min(total_tokens, token_budget)

    context_preview: Optional[str] = None
    if include_context:
        context_str, injected_paths, used_tokens = build_workspace_context(
            str(base_path),
            selected_files=selected_files,
            token_budget=token_budget,
        )
        context_preview = context_str
        capped_tokens = used_tokens

    included_count = sum(1 for f in indexed_files if f.get("included", True))
    return {
        "folder_path": str(base_path),
        "workspace_path": str(base_path),
        "path": str(base_path),
        "project_name": base_path.name or str(base_path),
        "is_unity_project": is_unity,
        "valid": True,
        "error": None,
        "project_type": project_type,
        "summary": project_type,
        "total_files": len(indexed_files),
        "included_files": included_count,
        "total_size_bytes": total_size,
        "total_estimated_tokens": total_tokens,
        "capped_tokens": capped_tokens,
        "total_tokens": capped_tokens,
        "token_budget": token_budget,
        "files": indexed_files,
        "language_breakdown": language_breakdown,
        "pruned_dirs": sorted(pruned_encountered) if pruned_encountered else sorted(PRUNED_DIRECTORIES),
        "context_preview": context_preview,
    }


def build_workspace_context(
    folder_path: str,
    selected_files: Optional[List[str]] = None,
    token_budget: int = WORKSPACE_TOKEN_BUDGET,
) -> Tuple[str, List[str], int]:
    """
    Builds a structured XML/Markdown workspace context block capped at `token_budget` tokens.
    Returns (context_string, list_of_injected_relative_paths, total_tokens_injected).
    """
    scan = scan_workspace(folder_path, include_context=False, token_budget=token_budget)
    if not scan["valid"] or not scan["files"]:
        return "", [], 0

    base_path = Path(scan["folder_path"])
    files: List[Dict[str, Any]] = scan["files"]

    # Build file tree summary header
    tree_lines = [
        f"<workspace_summary path=\"{base_path}\" project_type=\"{scan['project_type']}\" total_files=\"{scan['total_files']}\">",
        "Indexed Project Files:",
    ]
    for f in files[:250]:
        tree_lines.append(f"  - {f['path']} ({f['language']}, ~{f['estimated_tokens']} tokens)")
    if len(files) > 250:
        tree_lines.append(f"  ... and {len(files) - 250} more files")
    tree_lines.append("</workspace_summary>\n")

    header_block = "\n".join(tree_lines)
    used_tokens = estimate_tokens_from_text(header_block)

    # Filter or prioritize files
    selected_set = {p.strip().lstrip("/") for p in (selected_files or []) if p and p.strip()}
    if selected_set:
        prioritized_files = [f for f in files if f["path"] in selected_set]
        # If selected_files didn't match exact paths, also allow remaining files by priority
        remaining_files = sorted(
            [f for f in files if f["path"] not in selected_set],
            key=lambda item: (EXTENSION_PRIORITY.get(item["extension"], 99), item["path"]),
        )
        candidate_files = prioritized_files + remaining_files
    else:
        candidate_files = sorted(
            files,
            key=lambda item: (EXTENSION_PRIORITY.get(item["extension"], 99), item["path"]),
        )

    file_blocks: List[str] = [header_block]
    injected_paths: List[str] = []

    for f in candidate_files:
        if used_tokens >= token_budget:
            break

        full_path = base_path / f["path"]
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        block = (
            f"<workspace_file path=\"{f['path']}\" language=\"{f['language']}\">\n"
            f"{content}\n"
            f"</workspace_file>\n"
        )
        block_tokens = estimate_tokens_from_text(block)

        if used_tokens + block_tokens > token_budget:
            # If we still have room for at least 500 tokens, truncate the file gracefully
            remaining_budget = token_budget - used_tokens
            if remaining_budget > 500:
                char_allowance = remaining_budget * 4
                truncated_content = content[:char_allowance] + "\n/* ... [Truncated to fit 45,000 token workspace budget] ... */"
                block = (
                    f"<workspace_file path=\"{f['path']}\" language=\"{f['language']}\" truncated=\"true\">\n"
                    f"{truncated_content}\n"
                    f"</workspace_file>\n"
                )
                file_blocks.append(block)
                injected_paths.append(f["path"])
                used_tokens += estimate_tokens_from_text(block)
            break

        file_blocks.append(block)
        injected_paths.append(f["path"])
        used_tokens += block_tokens

    return "\n".join(file_blocks), injected_paths, used_tokens


def write_workspace_file(
    folder_path: str,
    relative_path: str,
    content: str,
) -> Dict[str, Any]:
    """
    Safely writes or updates a source file inside the user's local workspace.
    Strictly prevents '..' directory traversal or writing outside `folder_path`.
    """
    if not folder_path or not folder_path.strip():
        raise ValueError("Workspace folder_path is required.")
    if not relative_path or not relative_path.strip():
        raise ValueError("Target relative_path is required.")

    base_dir = Path(folder_path.strip()).expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        raise ValueError(f"Workspace directory does not exist: {base_dir}")

    # Normalize relative path and reject traversal attempts
    clean_rel = relative_path.strip().replace("\\", "/").lstrip("/")
    rel_parts = Path(clean_rel).parts
    if not rel_parts or ".." in rel_parts:
        raise ValueError(f"Path traversal detected or invalid relative path: '{relative_path}'")

    # Block writing into .git, .venv, credential folders, or secret .env files
    if rel_parts[0] in {".git", ".venv", "Library", "Temp"} or any(
        p in RESTRICTED_CREDENTIAL_DIRNAMES for p in rel_parts
    ):
        raise ValueError(f"Writing into protected directory '{rel_parts[0]}' is not permitted.")

    target_filename = rel_parts[-1]
    if (
        target_filename == ".env"
        or target_filename.startswith(".env.")
        or target_filename.endswith((".pem", ".key", ".sqlite3", ".db"))
    ):
        raise ValueError(f"Writing to protected secret or database file '{target_filename}' is forbidden.")

    target_path = (base_dir / clean_rel).resolve()

    # Verify target_path is strictly inside base_dir
    if not target_path.is_relative_to(base_dir) or target_path == base_dir:
        raise ValueError(f"Target path '{target_path}' escapes workspace root '{base_dir}'.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8")
    target_path.write_bytes(encoded)

    normalized_rel = target_path.relative_to(base_dir).as_posix()
    return {
        "success": True,
        "folder_path": str(base_dir),
        "relative_path": normalized_rel,
        "full_path": str(target_path),
        "bytes_written": len(encoded),
        "message": f"Successfully wrote {len(encoded):,} bytes to {normalized_rel}",
    }
