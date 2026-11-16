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

---

## Problem #4: Collapsible `N file(s) changed +X -Y` Summary Bar & Per-File Line Diff Submenu

### 1. Symptom & User Experience Goal
When Hermes Studio creates, modifies, or deletes multiple local files (e.g., 10 files in a single task), the user needs an immediate, compact visual summary directly below the assistant's message showing:
- **Top-level pill:** `<N> file(s) changed  +<created_or_modified_files> (green)  -<deleted_files> (red)  >` on the left and a `[Review]` button on the right.
- **Expandable submenu on click:** A clean list of all affected files by their **basename only** (`app.js`, `store.js`, `LoginView.js`, etc.), colored **green** if created/modified or **red** if deleted, alongside the exact number of **lines added (`+X` in green)** and **lines removed (`-Y` in red)** for each file.

### 2. Engineering Solution Implemented
1. **Line-Level Diff Telemetry & File Deletion in `backend/services/autonomous_executor.py`:**
   - Added `_compute_line_diff_stats(old_text, new_text)` powered by `difflib.SequenceMatcher` to compute exact `(lines_added, lines_removed)` whenever a file is created, overwritten, or surgically patched via `SEARCH/REPLACE`.
   - Added `INLINE_DELETE_HEADER_PATTERN` (`// Delete: <relative_path>` or `# Delete: <relative_path>`) so the autonomous executor can also remove obsolete workspace files on disk and record `type: "file_deleted"`, `status: "deleted"`, `lines_added: 0`, and `lines_removed: <previous_line_count>`.
   - Enriched every item in `actions_executed` with `filename` (basename), `lines_added`, and `lines_removed`.
2. **Collapsible Summary Component (`frontend/src/components/FilesChangedSummaryBar.tsx`):**
   - Rendered directly beneath `<MarkdownRenderer />` inside `frontend/src/app/page.tsx`.
   - Displays the top summary bar with `<N> file(s) changed`, green `+X` count for created/modified files, red `-Y` count for deleted files, chevron indicator (`>`), and `Review` button.
   - Clicking anywhere on the bar or `Review` button expands the submenu showing each file's basename (`text-emerald-300` for created/modified, `text-rose-400 line-through` for deleted) and its per-file `+linesAdded` (green) and `-linesRemoved` (red) counts.
   - Includes a fallback parser (`parseFallbackFilesFromContent`) so historical messages in SQLite without `actions_executed` metadata also display the collapsible summary bar automatically.

---

## Problem #5: Multi-File Truncation (2 of 10 Files Applied), `// File:` Header Pollution in `.cs` Files, and Silent Zero-Code-Dump Chat UI

### 1. Symptoms Observed (`UnityGameJam` 10-File Edit Task)
When the user prompted Hermes Studio to edit 10 random files in `UnityGameJam` by adding `// 67`:
1. **Only 2 of 10 files were modified on disk (`AssemblyInfo.cs` and `CombatReason.cs`), and the 3rd file (`BuildScript.cs`) was cut off mid-stream:**
   - The LLM attempted to output the **entire file contents** of each file instead of a 2-line surgical append, and `google/gemini-2.5-pro` consumed ~3,300 of its 4,096 `max_tokens` budget on internal thinking tokens, cutting off the visible output on the 3rd file.
   - Additionally, `INLINE_FILE_HEADER_PATTERN` did not match file paths containing spaces (such as `Assets/TextMesh Pro/Shaders/TMP_SDF-Mobile SSD.shader`).
2. **Synthetic `+ // File: Assets/...` header line polluted `.cs` files in GitHub Desktop:**
   - `_strip_file_header_comment()` was previously only called for `(.json, .html, .css, .vue, .md)`, leaving `// File: Assets/_Project/Scripts/Core/CombatReason.cs` on line 1 of `.cs` files on disk.
3. **Code cards and truncated code snippets cluttered the chat message:**
   - The user requested that when editing workspace files, the chat should **never** display code blocks or file cards—only the assistant's concise confirmation message and the `10 file(s) changed +10 -0` collapsible bar below it.
4. **Backend Uvicorn process was running without `--reload`:**
   - `start-studio.sh` launched `uvicorn` without `--reload`, keeping older Python modules cached in memory until restarted.

### 2. Engineering Solutions Implemented
1. **Ultra-Compact Surgical Directives (`// Append: <path>` & `// Prepend: <path>`) & Multi-Directive Batching (`backend/services/autonomous_executor.py`):**
   - Added `INLINE_DIRECTIVE_PATTERN` and `_split_multi_directive_block()` supporting `// Append: <path>`, `// Prepend: <path>`, `// File: <path>`, and `// Delete: <path>` (including file paths with spaces), allowing the LLM to modify 10+ files inside a single 20-line block (~120 tokens total instead of thousands).
   - Updated `apply_autonomous_files()` to **always** call `_strip_file_header_comment()` across all file extensions so synthetic `// File:` or `// Append:` headers never contaminate source files in GitHub Desktop.
2. **Silent Zero-Code-Dump Chat Experience (`backend/services/autonomous_executor.py`, `backend/routers/chat.py`, `frontend/src/components/MarkdownRenderer.tsx`):**
   - Added `strip_workspace_code_blocks()` in the backend and updated `MarkdownRenderer.tsx` to return `null` for any workspace-applied code block and strip any unclosed trailing code fence, ensuring the user sees only the assistant's text summary and the `N file(s) changed +X -Y` bar.
3. **Reasoning Model Token Headroom & Untargeted Context Cap (`backend/services/openrouter_client.py`, `backend/services/workspace_scanner.py`):**
   - Automatically ensured `max_tok >= 8192` for reasoning models (`gemini-2.5-*`, `deepseek-r1`) so internal thinking tokens never truncate multi-file edits.
   - Capped untargeted workspace context to `2,800` tokens with 14-line head + 6-line tail previews for files `> 700` chars.
4. **Hot Reload Enabled in `start-studio.sh`:**
   - Added `--reload --reload-dir backend` to `uvicorn` in `start-studio.sh` and restarted the live service.

---

## Problem #6: Clipboard Image Paste (`Cmd+V`), Binary-to-UTF8 Token Corruption, and Multimodal Vision Context Integration

### 1. Symptoms Observed
1. **No Clipboard Paste (`Cmd+V`) Support in Composer:**
   - Pasting a screenshot from the macOS clipboard (`Cmd+V`) into `BottomComposer.tsx` had no effect because the `<textarea>` lacked an `onPaste` handler inspecting `e.clipboardData.items` for `image/*` blobs.
2. **Binary Image-to-UTF8 Token Corruption in `format_attachments_block()`:**
   - When an image (`data:image/png;base64,...`) was attached, `format_attachments_block()` in `backend/services/openrouter_client.py` called `base64.b64decode(b64_part).decode("utf-8", errors="replace")`. Because `errors="replace"` never raises an exception, a 200 KB PNG binary was converted into ~200,000 characters of `\ufffdPNG...` replacement characters inside `<attached_file>`, exhausting the token budget with unreadable binary noise and providing zero visual understanding.
3. **Prompt Enhancer Ignored Attached Images & Hallucinated Generic Filenames:**
   - Clicking the inline Prompt Enhancer button (`✦`) did not forward attached images to `/api/prompt-enhancer/chat`, and when no workspace was linked, the Prompt Enhancer invented placeholder filenames (`image_analysis.py`, `prompt_processor.py`, `main_app.py`).

### 2. Engineering Solutions Implemented
1. **Dedicated Multimodal Vision & Metadata Service (`backend/services/image_analyzer.py`):**
   - Implemented `is_image_attachment()`, `extract_image_metadata()` (pure-Python binary header inspection for PNG, JPEG, GIF, and WebP pixel dimensions and byte size), `split_attachments()`, and `analyze_images_with_vision()`.
   - `analyze_images_with_vision()` dispatches pasted/attached images to vision-capable models (`google/gemini-2.0-flash-exp:free`, `google/gemini-2.5-flash`, `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`) to extract a structured `<image_context_analysis>` block containing:
     1. **Context & Situation** (UI state, active app, or scene shown).
     2. **Extracted Text, Messages & Errors** (verbatim transcription of error logs, stack traces, chat messages, or code).
     3. **Key Visual Details & Diagnosis** combined with the user's prompt.
2. **Binary Corruption Guard & Native Multimodal Routing (`backend/services/openrouter_client.py` & `backend/routers/chat.py`):**
   - Updated `format_attachments_block()` to detect image attachments and binary files (`\ufffd` ratio check) so binary image bytes are never decoded as UTF-8 text.
   - Added `build_multimodal_attachments_block()` and updated `acall_llm()` to pass native OpenRouter `image_url` content parts to vision-capable models while injecting the structured `<image_context_analysis>` block for all text-only coding models (`deepseek-v3`, `deepseek-r1`, `qwen-coder-32b`) and multi-agent squads (`team:dev-squad`).
3. **Clipboard Paste (`Cmd+V`) & Vision-Aware Prompt Enhancer (`frontend/src/components/BottomComposer.tsx`, `frontend/src/app/page.tsx`, `backend/routers/prompt_enhancer.py`):**
   - Added `onPaste={handlePaste}` and drag-and-drop (`onDrop={handleDrop}`) in `BottomComposer.tsx` so `Cmd+V` immediately attaches clipboard screenshots with a thumbnail preview (`Vision Image · KB`).
   - Updated `/api/prompt-enhancer/chat` and `enhancePromptApi()` to accept `attachments`, synthesize `<image_context_analysis>` into the enhanced English prompt, and strictly forbid inventing placeholder filenames when no workspace files are linked.



