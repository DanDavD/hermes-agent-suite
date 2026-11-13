"""SQLite database storage for Hermes Studio v2 projects, sessions, messages, and telemetry."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config import BACKEND_DIR, resolve_mode

DB_PATH = BACKEND_DIR / "hermes_studio.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Creates a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    """Initializes SQLite tables and runs seamless schema migrations."""
    conn = get_connection()
    try:
        with conn:
            # 1. Projects table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    workspace_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 2. Sessions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'team:dev-squad',
                    workspace_path TEXT NOT NULL DEFAULT '',
                    project_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # Seamless migration: add project_id column to sessions if upgrading existing DB
            try:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN project_id TEXT NOT NULL DEFAULT '';"
                )
            except sqlite3.OperationalError:
                pass

            # 3. Messages table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent_badge TEXT NOT NULL DEFAULT '',
                    attachments_json TEXT NOT NULL DEFAULT '[]',
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    agent_steps_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE messages ADD COLUMN agent_steps_json TEXT NOT NULL DEFAULT '[]';"
                )
            except sqlite3.OperationalError:
                pass

            # Remove legacy seeded welcome messages, seeded demo projects, and empty placeholder sessions
            conn.execute(
                "DELETE FROM messages WHERE session_id = 'welcome-session-v2' OR content LIKE '# Welcome to Hermes Studio%';"
            )
            conn.execute(
                "DELETE FROM projects WHERE id IN ('proj-web-portfolio', 'proj-horde-carnage', 'proj-hermes-suite');"
            )
            conn.execute(
                "DELETE FROM sessions WHERE id NOT IN (SELECT DISTINCT session_id FROM messages);"
            )
    finally:
        conn.close()


# =============================================================================
# PROJECTS CRUD
# =============================================================================


def list_projects() -> List[Dict[str, Any]]:
    """Returns all projects ordered by updated_at descending with session counts."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.name,
                p.description,
                p.workspace_path,
                p.created_at,
                p.updated_at,
                COUNT(s.id) AS session_count
            FROM projects p
            LEFT JOIN sessions s ON s.project_id = p.id
            GROUP BY p.id
            ORDER BY p.updated_at DESC, p.created_at ASC;
            """
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"] or "",
                "workspace_path": r["workspace_path"] or "",
                "session_count": int(r["session_count"] or 0),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a project by ID along with its session count."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                p.id,
                p.name,
                p.description,
                p.workspace_path,
                p.created_at,
                p.updated_at,
                COUNT(s.id) AS session_count
            FROM projects p
            LEFT JOIN sessions s ON s.project_id = p.id
            WHERE p.id = ?
            GROUP BY p.id;
            """,
            (project_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"] or "",
            "workspace_path": row["workspace_path"] or "",
            "session_count": int(row["session_count"] or 0),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        conn.close()


def create_project(
    name: str,
    workspace_path: str = "",
    description: str = "",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a new project and returns its schema dict."""
    pid = project_id or f"proj-{uuid.uuid4().hex[:8]}"
    now = _utc_now_iso()
    clean_name = (name or "Untitled Project").strip()[:100]
    clean_desc = (description or "").strip()[:500]
    clean_ws = (workspace_path or "").strip()

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, workspace_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (pid, clean_name, clean_desc, clean_ws, now, now),
            )
        return {
            "id": pid,
            "name": clean_name,
            "description": clean_desc,
            "workspace_path": clean_ws,
            "session_count": 0,
            "created_at": now,
            "updated_at": now,
        }
    finally:
        conn.close()


def update_project(
    project_id: str,
    name: Optional[str] = None,
    workspace_path: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Updates a project's name, workspace_path, or description and syncs linked sessions."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM projects WHERE id = ?;", (project_id,)
        ).fetchone()
        if not existing:
            return None

        new_name = name.strip()[:100] if name is not None else existing["name"]
        new_desc = (
            description.strip()[:500]
            if description is not None
            else existing["description"]
        )
        new_ws = (
            workspace_path.strip()
            if workspace_path is not None
            else existing["workspace_path"]
        )
        now = _utc_now_iso()

        with conn:
            conn.execute(
                """
                UPDATE projects
                SET name = ?, description = ?, workspace_path = ?, updated_at = ?
                WHERE id = ?;
                """,
                (new_name, new_desc, new_ws, now, project_id),
            )
            # If workspace_path was updated, propagate to sessions belonging to this project
            if workspace_path is not None:
                conn.execute(
                    """
                    UPDATE sessions
                    SET workspace_path = ?
                    WHERE project_id = ? AND (workspace_path = '' OR workspace_path = ?);
                    """,
                    (new_ws, project_id, existing["workspace_path"] or ""),
                )
    finally:
        conn.close()

    return get_project(project_id)


def delete_project(project_id: str) -> bool:
    """Deletes a project and unlinks any sessions referencing it."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE sessions SET project_id = '' WHERE project_id = ?;",
                (project_id,),
            )
            cur = conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# =============================================================================
# SESSIONS & MESSAGES CRUD
# =============================================================================


def _row_to_message(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite message row into a dictionary matching MessageResponse."""
    try:
        attachments = json.loads(row["attachments_json"] or "[]")
    except Exception:
        attachments = []

    agent_steps = []
    if "agent_steps_json" in row.keys():
        try:
            agent_steps = json.loads(row["agent_steps_json"] or "[]")
        except Exception:
            agent_steps = []

    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "role": row["role"],
        "content": row["content"],
        "agent_badge": row["agent_badge"] or "",
        "attachments": attachments,
        "attachments_json": row["attachments_json"] or "[]",
        "agent_steps": agent_steps,
        "tokens_used": int(row["tokens_used"] or 0),
        "created_at": row["created_at"],
    }


def list_sessions(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns sessions ordered by updated_at descending with message counts."""
    conn = get_connection()
    try:
        if project_id is not None and project_id != "":
            rows = conn.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.mode,
                    s.workspace_path,
                    s.project_id,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS message_count,
                    COALESCE(SUM(m.tokens_used), 0) AS total_tokens
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                WHERE s.project_id = ?
                GROUP BY s.id
                ORDER BY s.updated_at DESC;
                """,
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.mode,
                    s.workspace_path,
                    s.project_id,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) AS message_count,
                    COALESCE(SUM(m.tokens_used), 0) AS total_tokens
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC;
                """
            ).fetchall()

        return [
            {
                "id": r["id"],
                "title": r["title"],
                "mode": r["mode"],
                "workspace_path": r["workspace_path"] or "",
                "project_id": r["project_id"] or "",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": int(r["message_count"] or 0),
                "total_tokens": int(r["total_tokens"] or 0),
            }
            for r in rows
        ]
    finally:
        conn.close()


def create_session(
    title: str = "New Session",
    mode: str = "team:dev-squad",
    workspace_path: str = "",
    project_id: str = "",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a new chat session (inheriting project workspace_path if not provided)."""
    sid = session_id or str(uuid.uuid4())
    now = _utc_now_iso()
    normalized_mode = resolve_mode(mode)
    clean_title = (title or "New Session").strip()[:120]
    clean_project_id = (project_id or "").strip()
    clean_workspace = (workspace_path or "").strip()

    conn = get_connection()
    try:
        # Inherit workspace_path from parent project if session workspace_path is empty
        if clean_project_id and not clean_workspace:
            p_row = conn.execute(
                "SELECT workspace_path FROM projects WHERE id = ?;",
                (clean_project_id,),
            ).fetchone()
            if p_row and p_row["workspace_path"]:
                clean_workspace = p_row["workspace_path"]

        with conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, mode, workspace_path, project_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sid,
                    clean_title,
                    normalized_mode,
                    clean_workspace,
                    clean_project_id,
                    now,
                    now,
                ),
            )
        return {
            "id": sid,
            "title": clean_title,
            "mode": normalized_mode,
            "workspace_path": clean_workspace,
            "project_id": clean_project_id,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "total_tokens": 0,
            "messages": [],
        }
    finally:
        conn.close()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a session along with its ordered messages."""
    conn = get_connection()
    try:
        s_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?;", (session_id,)
        ).fetchone()
        if not s_row:
            return None

        m_rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC, rowid ASC;",
            (session_id,),
        ).fetchall()
        messages = [_row_to_message(m) for m in m_rows]
        total_tokens = sum(m["tokens_used"] for m in messages)

        project_id_val = s_row["project_id"] if "project_id" in s_row.keys() else ""
        return {
            "id": s_row["id"],
            "title": s_row["title"],
            "mode": s_row["mode"],
            "workspace_path": s_row["workspace_path"] or "",
            "project_id": project_id_val or "",
            "created_at": s_row["created_at"],
            "updated_at": s_row["updated_at"],
            "message_count": len(messages),
            "total_tokens": total_tokens,
            "messages": messages,
        }
    finally:
        conn.close()


def update_session(
    session_id: str,
    title: Optional[str] = None,
    mode: Optional[str] = None,
    workspace_path: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Updates session fields (including project_id) and bumps updated_at."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM sessions WHERE id = ?;", (session_id,)
        ).fetchone()
        if not existing:
            return None

        new_title = title.strip()[:120] if title is not None else existing["title"]
        new_mode = resolve_mode(mode) if mode is not None else existing["mode"]
        new_ws = (
            workspace_path.strip()
            if workspace_path is not None
            else existing["workspace_path"]
        )
        existing_pid = existing["project_id"] if "project_id" in existing.keys() else ""
        new_pid = project_id.strip() if project_id is not None else (existing_pid or "")
        now = _utc_now_iso()

        with conn:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, mode = ?, workspace_path = ?, project_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (new_title, new_mode, new_ws, new_pid, now, session_id),
            )
    finally:
        conn.close()

    return get_session(session_id)


def delete_session(session_id: str) -> bool:
    """Deletes a session and its cascading messages."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?;", (session_id,))
            cur = conn.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def add_message(
    session_id: str,
    role: str,
    content: str,
    agent_badge: str = "",
    attachments: Optional[List[Dict[str, Any]]] = None,
    tokens_used: int = 0,
    agent_steps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Inserts a message into SQLite and updates the parent session's timestamp."""
    msg_id = str(uuid.uuid4())
    now = _utc_now_iso()
    attachments_json = json.dumps(attachments or [])
    steps_json = json.dumps(agent_steps or [])

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, session_id, role, content, agent_badge,
                    attachments_json, tokens_used, agent_steps_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg_id,
                    session_id,
                    role,
                    content,
                    agent_badge or "",
                    attachments_json,
                    int(tokens_used or 0),
                    steps_json,
                    now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?;",
                (now, session_id),
            )
    finally:
        conn.close()

    return {
        "id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "agent_badge": agent_badge or "",
        "attachments": attachments or [],
        "attachments_json": attachments_json,
        "agent_steps": agent_steps or [],
        "tokens_used": int(tokens_used or 0),
        "created_at": now,
    }


def get_telemetry_stats() -> Dict[str, Any]:
    """Computes aggregate local SQLite usage statistics."""
    conn = get_connection()
    try:
        p_count = conn.execute("SELECT COUNT(*) AS cnt FROM projects;").fetchone()["cnt"]
        s_count = conn.execute("SELECT COUNT(*) AS cnt FROM sessions;").fetchone()["cnt"]
        m_row = conn.execute(
            """
            SELECT
                COUNT(*) AS msg_cnt,
                COALESCE(SUM(tokens_used), 0) AS total_tokens
            FROM messages;
            """
        ).fetchone()
        mode_rows = conn.execute(
            "SELECT mode, COUNT(*) AS cnt FROM sessions GROUP BY mode;"
        ).fetchall()
        mode_breakdown = {r["mode"]: int(r["cnt"]) for r in mode_rows}

        return {
            "total_projects": int(p_count or 0),
            "total_sessions": int(s_count or 0),
            "total_messages": int(m_row["msg_cnt"] or 0),
            "total_tokens_used": int(m_row["total_tokens"] or 0),
            "sessions_by_mode": mode_breakdown,
        }
    finally:
        conn.close()
