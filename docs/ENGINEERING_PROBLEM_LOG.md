# Hermes Studio v2 — Engineering Problem & Resolution Log

**Author:** Daniel (`DanDavD`)  
**Repository:** `hermes-agent-suite`  
**Purpose:** Living technical journal documenting real-world engineering bottlenecks, forensic root-cause analyses, architectural solutions, and measurable before/after benchmarks across Hermes Studio v2.

---

## Problem #1: Excessive Token Consumption (29,043 Tokens in 2 Turns) & Failed Autonomous Local Disk Application

**Date:** November 2026  
**Affected Mode:** `raw:gemini-flash` (and all raw/squad execution pipelines)  
**Target Test Project:** `Prototipo_MobiRent` (`/Users/Damid/Documents/GitHub/Prototipo_MobiRent`)  
**Components Involved:**
- `backend/routers/chat.py`
- `backend/services/autonomous_executor.py`
- `backend/services/workspace_scanner.py`
- `backend/services/openrouter_client.py`
- `backend/routers/prompt_enhancer.py`
- `backend/database.py`
- `frontend/src/lib/api.ts` & `frontend/src/components/MarkdownRenderer.tsx`

---

### 1. Symptoms Observed
When running an enhanced prompt in `raw:gemini-flash` mode to analyze and refactor AI-generated UI/UX patterns in the local project `Prototipo_MobiRent`:
1. **Local Files Were Not Reliably Updated on Disk (GitHub Desktop Empty / Incomplete):**
   - Even when the assistant stated *"Yes, I have applied those changes and will now output the complete, refactored files directly to your disk"*, files were either skipped, partially overwritten with their old `"Before"` code, or cut off mid-file.
2. **Massive Token Drain (`20,149` tokens on Turn 1 + `8,894` tokens on Turn 2 = `29,043` tokens):**
   - A single refactoring request consumed over 20k tokens, and a 7-word follow-up question (*"did you apply those changes to the code?"*) consumed nearly 9k additional tokens.
3. **Chat UI Flooded with Raw Code Blocks:**
   - Instead of operating as an autonomous IDE agent that edits local files directly on disk and presents a concise summary of changes, the chat stream dumped hundreds of lines of raw code blocks requiring manual `"Apply to Workspace"` clicks.
4. **Generic Session Title (`"Role & Objective:"`):**
   - Prompts structured by the `$0` Prompt Enhancer began with `### Role & Objective:`, causing the session title generator to name every enhanced chat `"Role & Objective:"`.

---

### 2. Forensic Root-Cause Analysis

Inspecting the SQLite database (`backend/hermes_studio.db`, session `a28c1ba9-82e5-4c9d-87ae-da30b26a53e7`) revealed four compounding root causes:

#### Root Cause A: Empty `workspace_path` on Project-Scoped Sessions
In `backend/hermes_studio.db`, the session row recorded:
```json
{
  "id": "a28c1ba9-82e5-4c9d-87ae-da30b26a53e7",
  "title": "Role & Objective:",
  "mode": "raw:gemini-flash",
  "workspace_path": "",
  "project_id": "proj-ecb29a5b"
}
```
While the parent project `proj-ecb29a5b` (`Prototipo_MobiRent`) had `workspace_path = "/Users/Damid/Documents/GitHub/Prototipo_MobiRent"`, `_prepare_session_and_context()` in `backend/routers/chat.py` only checked `payload.workspace_path` and `session.get("workspace_path")`. It never fell back to `get_project(project_id)["workspace_path"]`. When `active_workspace` evaluated to `""`, `_execute_autonomous_post_processing()` exited immediately at `if not active_workspace: return []`.

#### Root Cause B: Full-File Rewrites + `"Before:" / "After:"` Duplication Hitting the `4,096` Output Token Cap
1. The system prompt in `backend/services/openrouter_client.py` instructed the model: *"NEVER output isolated code snippets... Always output complete, compilable files."*
2. Meanwhile, the Prompt Enhancer added *"Provide before-and-after screenshots demonstrating the changes."*
3. Consequently, `raw:gemini-flash` printed the **entire** original file under `**Before:**` (with `// File: js/components/LoginView.js`) and then printed the **entire** refactored file under `**After:**`.
4. Printing both `Before` and `After` across `js/app.js`, `js/store.js`, and `js/components/LoginView.js` generated `> 14,000` characters and hit the `max_tokens = 4096` output ceiling right in the middle of `LoginView.js`:
   ```html
   <!-- Campo: Contraseña -->
   <div>
     <
   ```
5. Because the `**After:**` block for `LoginView.js` was truncated before its closing ```` ``` ```` fence, the regex extractor only matched the completed `**Before:**` block—overwriting `LoginView.js` with its own unrefactored code.

#### Root Cause C: Unfiltered Workspace Context Injection (`32,953` Raw Workspace Tokens)
1. `build_workspace_context()` in `backend/services/workspace_scanner.py` injected every file in the workspace up to the global budget, including large untargeted files (`Modals.js` [28 KB], `AdminView.js` [22 KB], `data.js` [15 KB], `OwnerView.js` [14 KB], `Navbar.js` [14 KB]) even when only `app.js` and `LoginView.js` were being refactored.
2. Additionally, `.html` (`index.html`) and `.css` (`css/styles.css`) were missing from `EXTENSION_LANGUAGE_MAP` and `extract_files_from_markdown()`, making web entry/style files invisible to both the scanner and the disk writer.

#### Root Cause D: Uncompacted Code Dumps in `conversation_history`
In `backend/services/openrouter_client.py`, `acall_llm()` included up to `24,000` characters of prior assistant messages verbatim in `conversation_history`. On Turn 2, the 14,069-character code dump from Turn 1 was re-sent in full as input context, burning thousands of redundant tokens.

---

### 3. How I Solved It (Architectural & Code Fixes)

#### Fix 1: 4-Tier Workspace Path Resolution & SQLite Auto-Sync (`backend/routers/chat.py`, `backend/database.py`, `frontend/src/lib/api.ts`)
- **Backend Fallback Chain:** Updated `_prepare_session_and_context()` in `backend/routers/chat.py` to resolve `active_workspace` across four levels:
  1. `payload.workspace_path` (from request payload)
  2. `session.get("workspace_path")` (stored on session)
  3. `get_project(active_project_id)["workspace_path"]` (inherited from linked project)
  4. Automatic project-name matching in the prompt against `list_projects()`
- **Database Migration & Persistence:**
  - Added a startup query in `init_db()` (`backend/database.py`) that automatically populates any empty `sessions.workspace_path` from its parent `projects.workspace_path`.
  - Added `actions_executed_json` to the `messages` table so autonomous disk writes (`file_written`, `test_run`) persist across session reloads.
- **Frontend Payload Guarantee:** Updated `sendChatMessage()` (`frontend/src/lib/api.ts`) and `handleSend()` (`frontend/src/app/page.tsx`) to always pass `project_id` and `effectiveWorkspacePath`.

#### Fix 2: Surgical `SEARCH/REPLACE` Diff Engine & `"Before:"` Block Guard (`backend/services/autonomous_executor.py`)
- **Surgical Diff Patching (`apply_search_replace_blocks`):** Implemented support for structured `SEARCH/REPLACE` diff blocks:
  ```javascript
  // File: js/store.js
  <<<<<<< SEARCH
    currentUser: null,
    showPassword: false,
    activeRole: 'renter',
  =======
    currentUser: null,
    activeRole: 'renter',
  >>>>>>> REPLACE
  ```
  Instead of rewriting a 350-line file (`~3,500` output tokens) to change 5 lines, the model now emits a 12-line diff patch (`~45` output tokens) that `apply_autonomous_files()` applies directly to the local file on disk (with exact match, CRLF-normalized match, and indentation-tolerant line matching).
- **`Before:` Comparison Guard (`BEFORE_LABEL_PATTERN`):** `extract_files_from_markdown()` now inspects the markdown heading immediately preceding each code block and skips any block labeled `**Before:**` or `### Before`, ensuring old comparison snippets never overwrite refactored code.
- **Expanded File Extensions & JS Syntax Verification:**
  - Added `.html`, `.css`, `.scss`, `.vue`, `.jsx`, `.sql`, `.toml`, and `.xml` support across `workspace_scanner.py` and `autonomous_executor.py`.
  - Added automatic `node --check <file.js>` syntax verification in `run_automated_workspace_tests()` so JavaScript syntax errors are caught immediately on disk write.

#### Fix 3: Smart Relevance Context Filtering (`backend/services/workspace_scanner.py`)
- Implemented `_is_file_directly_targeted()` in `build_workspace_context()` (filtering out generic suffixes like `View`, `Component`, `Controller`, `Manager` so `LoginView.js` does not false-match `AdminView.js` or `OwnerView.js`).
- **Tiered Context Injection:**
  1. Always injects the lightweight `<workspace_summary>` file tree (`~190` tokens).
  2. Injects **100% full source** for files explicitly targeted in the prompt.
  3. Injects a **20-line structural header** (`summary="true"`) for core entry/store files (`app.js`, `store.js`, `index.html`) and skips unrelated large sibling files (`Modals.js`, `AdminView.js`).
  4. Caps per-turn dynamic workspace injection to `6,500` tokens.

#### Fix 4: Conversation History Code-Block Compaction (`backend/services/openrouter_client.py`)
- Added `_compact_history_content()` in `acall_llm()`. When assembling `conversation_history` from prior turns, any assistant code block longer than 18 lines is replaced with a 1-line token-saving marker:
  ```text
  `[Autonomous Disk Write: js/store.js (150 lines applied to workspace)]`
  ```
- Reduced the history character ceiling from `24,000` chars to `9,000` chars across the last 6 messages.

#### Fix 5: Token-Efficient Prompt Enhancer & Clean File Cards (`backend/routers/prompt_enhancer.py`, `frontend/src/components/MarkdownRenderer.tsx`)
- Updated `PROMPT_ARCHITECT_SYSTEM` so enhanced prompts explicitly instruct the coding agent to apply changes directly to disk using `// File: <path>` and surgical `SEARCH/REPLACE` blocks, forbidding redundant `"Before"` code dumps or manual screenshot requests.
- Updated `generate_smart_session_title()` to skip `### Role & Objective:` headers and extract the real project/task subject.
- Updated `RichCodeBlock` in `MarkdownRenderer.tsx` to display the file path (`js/app.js`), an emerald **`✓ Applied to Disk`** badge, and auto-collapse code blocks longer than 28 lines so the chat UI stays clean.

---

### 4. Verification & Quantitative Benchmarks

Verified via automated unit tests (`tests/test_autonomous_executor.py`, 11/11 passing) and live workspace benchmarks against `/Users/Damid/Documents/GitHub/Prototipo_MobiRent` (`13` files, `32,953` raw tokens):

| Metric / Scenario | Before Fix | After Fix | Improvement |
| :--- | :--- | :--- | :--- |
| **Targeted File Refactor Input Context** (`LoginView.js` & `app.js`) | ~16,500 tokens | **2,377 tokens** | **-85.6% tokens** |
| **General Project Refactor Input Context** (All 13 files) | ~16,500 tokens | **6,125 tokens** | **-62.9% tokens** |
| **Architecture / Advisory Question Input Context** | ~16,500 tokens | **196 tokens** | **-98.8% tokens** |
| **Follow-up Turn History Footprint** (150-line file in prior turn) | ~1,100 tokens | **~25 tokens** | **-97.7% tokens** |
| **Single-File Edit Output Tokens** (`SEARCH/REPLACE` vs Full File) | ~1,800–3,500 tokens | **~45–150 tokens** | **-92.0% tokens** |
| **Local Disk Application when `session.workspace_path == ""`** | Failed (0 files written) | **100% Auto-Applied** | **Fixed (4-tier fallback)** |

---

## Problem #2: Cold-Start Connection Screen (`Connecting to Hermes Studio...`) in Native macOS App

**Date:** November 2026  
**Components Involved:** `macos/Sources/main.swift`, `start-studio.sh`, `backend/main.py`

### 1. Symptoms Observed
1. Opening `/Applications/Hermes Studio.app` directly from macOS Finder/Dock when the terminal servers were not running displayed `Connecting to Hermes Studio (7 retries remaining)...` because the native Swift `WKWebView` wrapper expected `http://localhost:3000` and `http://127.0.0.1:8765` to be started manually.
2. Additionally, `backend/main.py` threw `NameError: name 'chat' is not defined` on startup after `prompt_enhancer` was added to router registrations.

### 2. How I Solved It
1. **Restored Router Import (`backend/main.py`):** Added `chat` back to `from backend.routers import chat, projects, prompt_enhancer, sessions, telemetry, workspace`.
2. **Autonomous Background Daemon Launcher (`macos/Sources/main.swift`):**
   - Implemented `ensureServicesAndLoad()` and `launchBackgroundServices()` inside `HermesApplicationDelegate`.
   - On app launch, `Hermes Studio.app` pings `http://localhost:3000` (`checkServerReachable`). If offline, it automatically spawns `/bin/zsh start-studio.sh` as a detached background process group, logs output to `/tmp/hermes-studio.log`, polls every `600ms` until both FastAPI (`8765`) and Next.js (`3000`) are online, and transitions smoothly into the IDE.
   - On `Cmd + Q` (`applicationWillTerminate`), the app cleanly terminates the background process group so no orphan ports remain open.

---

## Problem #3: `$0` In-Composer Prompt Enhancer with Strict Zero-Emoji Invariant

**Date:** November 2026  
**Components Involved:** `backend/routers/prompt_enhancer.py`, `frontend/src/components/BottomComposer.tsx`, `frontend/src/components/TopBar.tsx`, `tests/test_prompt_enhancer.py`

### 1. Symptoms Observed
1. Switching to an external AI tab to translate and structure Spanish/rough prompts into English engineering prompts interrupted the development workflow.
2. Early iterations of the Prompt Enhancer included decorative emojis (`🎯`, `📋`, `🛠️`) and a redundant top-bar button.

### 2. How I Solved It
1. **`$0` Free-Tier OpenRouter Chain (`backend/routers/prompt_enhancer.py`):**
   - Built `POST /api/prompt-enhancer/chat` cycling through zero-cost OpenRouter models (`google/gemini-2.0-flash-exp:free`, `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-chat:free`, etc.) at `$0.00` cost.
2. **Dual-Layer Zero-Emoji Enforcement:**
   - Added a strict `ZERO-EMOJI INVARIANT` rule in `PROMPT_ARCHITECT_SYSTEM` and a deterministic regex post-processor `strip_emojis()` that strips all Unicode pictograms/emojis from `summary`, `enhanced_prompt`, `explanation`, and `tips` before returning the response.
3. **Inline Composer Upgrade Button (`frontend/src/components/BottomComposer.tsx`):**
   - Placed a circular `✦` upgrade button directly beside the Send button with an animated emerald progress fill, completion checkmark, subtle `Prompt Enhancer` hover tooltip underneath, and automatic in-place replacement of the composer text.
