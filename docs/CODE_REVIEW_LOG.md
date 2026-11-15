# Hermes Studio v2 — Principal Architect Cross-Stack Code Review & Security Audit Log

> **Review ID:** `ARCH-REV-2026-11-11-V2`  
> **Reviewer:** Lead Software Architect & Principal Code Reviewer  
> **Scope:** Full-Stack Implementation Review (`/backend` Python FastAPI + `/frontend` Next.js 14 TypeScript/Tailwind)  
> **Verdict:** **APPROVED FOR PRODUCTION (All Critical & Minor Findings Remediated)**

---

## 1. Executive Summary

A comprehensive cross-stack architectural, type-contract, and security review was conducted across the **FastAPI Backend (`/backend`)** and **Next.js Workstation UI (`/frontend`)**. All REST/SSE endpoints, Pydantic v2 schemas, TypeScript interfaces, SQLite persistence operations, and local filesystem boundaries were audited line-by-line and verified via automated integration assertions (`fastapi.testclient.TestClient` and `next build` strict TypeScript/ESLint compilation).

---

## 2. Cross-Stack API Contract Verification Matrix

Every endpoint consumed by [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) and typed in [`frontend/src/lib/types.ts`](../frontend/src/lib/types.ts) was audited against [`backend/models/schemas.py`](../backend/models/schemas.py) and [`backend/routers/`](../backend/routers/):

| Endpoint | HTTP Method | Frontend Caller (`api.ts`) | Backend Router & Schema | Contract Alignment Status |
| :--- | :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | Health Probe | `main.py::healthcheck` | **100% Verified** (`status`, `api_key_configured`, `available_modes_count`) |
| `/api/sessions` | `GET` | `fetchSessions()` | `sessions.py::get_all_sessions` (`List[SessionSummary]`) | **100% Verified** (`id`, `title`, `mode`, `workspace_path`, `message_count`, `total_tokens`) |
| `/api/sessions` | `POST` | `createNewSession()` | `sessions.py::create_new_session` (`SessionDetailResponse`) | **100% Verified** |
| `/api/sessions/{id}` | `GET` | `fetchSessionById()` | `sessions.py::get_session_by_id` (`SessionDetailResponse`) | **100% Verified** (ordered `messages` with `agent_steps` & `attachments`) |
| `/api/sessions/{id}` | `PATCH` / `PUT` | `updateSessionById()` | `sessions.py::update_session_by_id` (`SessionDetailResponse`) | **100% Verified** (persists linked `workspace_path` & `mode` to SQLite) |
| `/api/sessions/{id}` | `DELETE` | `deleteSessionById()` | `sessions.py::delete_session_by_id` | **100% Verified** (`ON DELETE CASCADE` cleans up session messages) |
| `/api/chat` | `POST` | `sendChatMessage()` | `chat.py::execute_chat` (`ChatRequest` -> `ChatResponse`) | **100% Verified** (`user_message`, `assistant_message`, `agent_steps`, `workspace_files_injected`) |
| `/api/chat/stream` | `POST` (SSE) | SSE Consumer | `chat.py::stream_chat` (`text/event-stream`) | **100% Verified** (`step`, `complete`, `error`, and `done` event frames) |
| `/api/workspace/scan` | `POST` | `scanWorkspaceDirectory()` | `workspace.py::scan_local_workspace` (`WorkspaceScanResponse`) | **100% Verified** (`files`, `total_tokens`, `capped_tokens`, `token_budget`, `is_unity_project`) |
| `/api/workspace/apply` | `POST` | `applyCodeToWorkspace()` | `workspace.py::apply_file_to_workspace` (`WorkspaceWriteFileResponse`) | **100% Verified** (`success`, `full_path`, `relative_path`, `bytes_written`) |
| `/api/telemetry` | `GET` | `fetchTelemetry()` | `telemetry.py::get_telemetry` (`TelemetryResponse`) | **100% Verified** (`remaining_credits`, `total_usage`, `total_sessions`, `total_tokens_used`) |
| `/api/settings` | `POST` | `updateRuntimeSettings()` | `telemetry.py::update_settings` (`SettingsUpdateRequest`) | **100% Verified** (updates memory + `.env` and returns refreshed telemetry) |

---

## 3. Defects Identified & Remediated During Review

During the Principal Architect inspection, five cross-stack and security issues were identified and patched directly in the codebase prior to sign-off:

### 3.1. `[FIXED]` Duplicate Function Definition in `backend/services/openrouter_client.py`
- **Issue:** An incomplete stub of `async def fetch_openrouter_telemetry()` existed at lines 203–239 immediately above `_http_get_json()` and the full implementation of `fetch_openrouter_telemetry()`. While Python bound the later symbol at runtime, the shadowed stub violated static analysis (`F811`) and code hygiene standards.
- **Remediation:** Removed the dead stub in [`backend/services/openrouter_client.py`](../backend/services/openrouter_client.py).

### 3.2. `[FIXED]` Hardened OS Root & Credential Directory Denylist in `backend/services/workspace_scanner.py`
- **Issue:** While `scan_workspace()` canonicalized paths via `Path.expanduser().resolve()` and skipped dot-directories during traversal, passing a sensitive system root directly (e.g., `/etc`, `/System`, or `~/.ssh`) was not explicitly blocked at the entry gate. Additionally, `write_workspace_file()` blocked `.git`, `.venv`, `Library`, and `Temp`, but did not explicitly block writing to `.env`, `.env.*`, `*.pem`, `*.key`, or `*.db` files.
- **Remediation:**
  1. Added `RESTRICTED_SYSTEM_ROOTS` (`/`, `/etc`, `/private/etc`, `/var`, `/System`, `/Library`, `/bin`, `/sbin`, `/usr`) and `RESTRICTED_CREDENTIAL_DIRNAMES` (`.ssh`, `.aws`, `.gnupg`, `.kube`, `.docker`) entry validation via `_check_restricted_path()` in [`backend/services/workspace_scanner.py`](../backend/services/workspace_scanner.py).
  2. Hardened `write_workspace_file()` to reject writes targeting `.env`, `.env.*`, `*.pem`, `*.key`, `*.sqlite3`, or `*.db` with an HTTP `400 Bad Request`.

### 3.3. `[FIXED]` Direct Schema Parity for `/api/workspace/scan` and `/api/telemetry`
- **Issue:** The frontend TypeScript interfaces (`WorkspaceScanResult`, `ScannedFileItem`, `TelemetryData`, `AgentThoughtStep`) expected fields such as `project_name`, `is_unity_project`, `included_files`, `total_tokens`, `size_bytes`, `tokens`, `remaining_credits`, `total_usage`, and `status_message`. Although `frontend/src/lib/api.ts` included client-side fallback normalizers, the raw FastAPI Pydantic schemas only emitted backend-named equivalents (`total_estimated_tokens`, `size`, `remaining_usd`, `key_status`).
- **Remediation:** Extended [`backend/models/schemas.py`](../backend/models/schemas.py), [`backend/services/workspace_scanner.py`](../backend/services/workspace_scanner.py), and [`backend/routers/telemetry.py`](../backend/routers/telemetry.py) to emit both the canonical backend fields and exact frontend contract fields directly in the serialized JSON payload.

### 3.4. `[FIXED]` Mode Catalog Alignment (`raw:claude-sonnet`) & Session Workspace Persistence
- **Issue:**
  1. `WorkflowModeId` in `frontend/src/lib/types.ts` and `AVAILABLE_MODES` in `backend/config.py` included `"raw:claude-sonnet"`, but `WORKFLOW_MODES` in `frontend/src/lib/constants.ts` omitted the entry from the dropdown array.
  2. Assigning or unlinking a workspace in `WorkspaceModal` updated React state in `page.tsx` but did not immediately persist `workspace_path` to the active session via `PATCH /api/sessions/{id}`.
- **Remediation:** Added `raw:claude-sonnet` to [`frontend/src/lib/constants.ts`](../frontend/src/lib/constants.ts), added `updateSessionById()` to [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts), and wired `onAssignWorkspace` in [`frontend/src/app/page.tsx`](../frontend/src/app/page.tsx) to persist workspace path changes to SQLite.

### 3.5. `[FIXED]` Preserving Client-Side Image Attachment Previews Post-Send
- **Issue:** To prevent SQLite bloat, `backend/routers/chat.py` stores attachment metadata (`filename`, `content_type`, `size`) without the raw base64 payload in the `messages` table. When `page.tsx` replaced the optimistic user message with `result.userMessage`, attached image thumbnails (`previewUrl`) were lost in the active view.
- **Remediation:** Updated `sendChatMessage()` in [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) to retain the rich client-side attachment objects (including `previewUrl`) on the returned `userMessage`.

---

## 4. Security & Performance Audit Checklist

| Security / Performance Control | Implementation Location | Verification Method & Result |
| :--- | :--- | :--- |
| **Path Traversal Prevention (`..`)** | `workspace_scanner.py::write_workspace_file` | Verified via `TestClient`: `relative_path="../../etc/passwd"` rejected with `HTTP 400` (`Path traversal detected`). |
| **Canonical Root Escapes (`is_relative_to`)** | `workspace_scanner.py::write_workspace_file` | Target path resolved via `.resolve()` and verified strictly inside `base_dir` via `target_path.is_relative_to(base_dir)`. |
| **System Root & Credential Denylist** | `workspace_scanner.py::_check_restricted_path` | Verified via `TestClient`: scanning `/etc` returns `valid=False` with security policy rejection. |
| **Secret & `.env` Isolation** | `workspace_scanner.py` & `.gitignore` | Dotfiles (`.env`, `.git`) excluded from workspace scans; writing to `.env` via `/api/workspace/apply` rejected with `HTTP 400`. |
| **API Key Masking in Telemetry/Logs** | `config.py::RuntimeSettings.get_masked_key` | API keys are masked (`sk-or-v1...xxxx`) on all `GET /api/settings` and `GET /api/telemetry` responses. |
| **Unity Artifact Subtree Pruning** | `workspace_scanner.py::PRUNED_DIRECTORIES` | `os.walk` mutates `dirs[:]` in-place ($O(1)$ skip) for `Library/`, `Temp/`, `Obj/`, `Builds/`, `node_modules/`, `.git/`, `.venv/`. |
| **45,000-Token Context Ceiling** | `workspace_scanner.py::build_workspace_context` | Enforces `WORKSPACE_TOKEN_BUDGET = 45000` and `MAX_SINGLE_FILE_BYTES = 512 KB`, prioritizing `.cs` and `.shader` files before config files. |
| **SQLite Concurrency & Foreign Keys** | `database.py::get_connection` | Connections enable `PRAGMA journal_mode = WAL;` and `PRAGMA foreign_keys = ON;`. |

---

## 5. Build & Automated Verification Log

1. **Frontend Production Build (`next build`):**
   - Compiled cleanly with zero TypeScript or ESLint errors (`Route /` static bundle `24.8 kB`, First Load JS `112 kB`).
2. **Backend Contract & Security Test Suite (`TestClient`):**
   - Verified `/api/health`, `/api/sessions` CRUD, `/api/workspace/scan` contract parity, `/api/workspace/apply` traversal/secret guards, and `/api/telemetry` schema alignment.
