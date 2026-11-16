# Hermes Studio v2 — Product Dev & AI Engineering (Nov 12-14)

Production delivery roadmap for Hermes Studio v2: Autonomous Multi-Agent AI IDE & Local Workspace Context Engine. Built to solve high Claude subscription costs, showcasing AI fluency, async ownership, and polished product design for the Colonist Product Developer Intern role.

## PR #1: feat/backend-core-sqlite-fastapi
**Label:** `Backend / API` | **Target Date:** `2026-11-12 (Morning)` | **Branch:** `feat/backend-core-sqlite-fastapi`

### 🎯 Objective
Build the foundational asynchronous backend using FastAPI, SQLite persistence with WAL mode, OpenRouter streaming client, and token cost tracking.

### 💡 Why this matters for Colonist
Demonstrates full-stack ownership, clean decoupled architecture, and financial mindfulness by tracking exact USD micro-costs per LLM generation.

### 📦 Deliverables & Files
- `backend/main.py`: FastAPI server with CORS & lifespan DB initialization
- `backend/config.py`: Environment configuration and model tier definitions
- `backend/database.py`: SQLite engine with WAL mode and schema definitions
- `backend/models/schemas.py`: Pydantic v2 schemas for sessions, messages, projects
- `backend/services/openrouter_client.py`: OpenRouter API client with streaming
- `legacy-streamlit/`: Archival of monolithic v1 prototype


### Acceptance Checklist
- [ ] Archive legacy Streamlit monolithic scripts to /legacy-streamlit
- [ ] Implement FastAPI application entrypoint with lifespan event handlers
- [ ] Create SQLite schema: sessions, messages, projects, and telemetry
- [ ] Implement OpenRouter client with token usage calculation ($0.024/run)
- [ ] Add Pydantic v2 validation models for all request/response contracts
- [ ] Verify backend boots on port 8765 and passes health checks
- [ ] Commit and submit PR #1 to GitHub with structured markdown description

---

## PR #2: feat/local-workspace-scanner
**Label:** `Architecture & ADR` | **Target Date:** `2026-11-12 (Afternoon)` | **Branch:** `feat/local-workspace-scanner`

### 🎯 Objective
Implement the Local Workspace Context Engine featuring a strict 45,000-token ceiling, smart subtree pruning, and native macOS Finder folder picking.

### 💡 Why this matters for Colonist
Solves the real-world problem of context window blowout and massive API bills. Prunes noise (node_modules, Library, .git) so AI only reads high-signal game and product code.

### 📦 Deliverables & Files
- `backend/services/workspace_scanner.py`: Recursive tree walker with file pruning
- `backend/routers/workspace.py`: Workspace scanning and Finder selection endpoints
- Security guardrails against path traversal outside the approved workspace


### Acceptance Checklist
- [ ] Build recursive directory scanner with O(1) subtree pruning for node_modules/.git/Library
- [ ] Implement 45k token context budget ceiling with file prioritization
- [ ] Add native macOS AppleScript folder picker endpoint (/api/workspace/pick-finder)
- [ ] Implement security checks blocking path traversal and sensitive files (.env, .ssh)
- [ ] Test scanner with large Unity/React repositories to confirm sub-100ms response
- [ ] Commit and submit PR #2 to GitHub with context budget verification logs

---

## PR #3: feat/multi-agent-orchestrator
**Label:** `AI / Multi-Agent` | **Target Date:** `2026-11-13 (Morning)` | **Branch:** `feat/multi-agent-orchestrator`

### 🎯 Objective
Implement the 5-Agent Autonomous Dev Squad pipeline and Career Intelligence workflows.

### 💡 Why this matters for Colonist
Direct proof of 'AI-first mindset' and treating AI fluency as a multiplier. Orchestrates specialized models (Hermes 70B for architecture + Qwen 2.5 Coder 32B for code gen + Hermes 8B for UX audit) with structured handoffs.

### 📦 Deliverables & Files
- `backend/services/workflows/dev_squad.py`: 5-agent sequential orchestration
- `backend/services/workflows/career_hunter.py`: ATS resume & live job matcher
- `backend/services/workflows/content_video.py`: Script generation pipeline
- `backend/routers/chat.py`: Multi-agent streaming execution router


### Acceptance Checklist
- [ ] Define 5-agent pipeline: Leader -> Coder -> Code Reviewer -> UI Maker -> UI Reviewer
- [ ] Implement agent-to-agent prompt handoff passing previous thoughts and diffs
- [ ] Configure hybrid model routing (Hermes 70B + Qwen Coder 32B + Hermes 8B)
- [ ] Implement real-time agent execution telemetry (tokens, latency, USD spend)
- [ ] Build ATS resume optimization and live interview coach agent workflows
- [ ] Test multi-agent code generation with Unity C# scripts and Next.js components
- [ ] Commit and submit PR #3 to GitHub with agent trace screenshots

---

## PR #4: feat/nextjs-workstation-ui
**Label:** `Frontend / UX` | **Target Date:** `2026-11-13 (Afternoon)` | **Branch:** `feat/nextjs-workstation-ui`

### 🎯 Objective
Deliver a Claude-grade dark UI workstation using Next.js 14, TypeScript, and Tailwind CSS.

### 💡 Why this matters for Colonist
Direct alignment with Colonist's core need: 'Build and improve game UI and UX, with a strong focus on clarity, polish, and fun. You care about user experience, not just the code.'

### 📦 Deliverables & Files
- `frontend/src/app/page.tsx`: Core workstation view with responsive layout
- `frontend/src/components/Sidebar.tsx`: Collapsible project tree with Cmd+B shortcut
- `frontend/src/components/BottomComposer.tsx`: Auto-resizing composer & inline send pill
- `frontend/src/components/AgentStepsAccordion.tsx`: Live step-by-step reasoning view
- `frontend/src/components/MarkdownRenderer.tsx`: Code highlighter with copy button


### Acceptance Checklist
- [ ] Initialize Next.js App Router with dark theme and Tailwind CSS palette
- [ ] Implement collapsible project/chat sidebar with keyboard shortcut (Cmd+B)
- [ ] Build centered composer with auto-expand, inline send circle, and folder picker
- [ ] Create AgentStepsAccordion showing real-time agent thoughts, tokens, and latency
- [ ] Integrate syntax-highlighted code blocks with 1-click clipboard copy
- [ ] Add live API credit balance indicator in the sidebar footer
- [ ] Verify responsive layout and zero layout shift when opening/closing sidebars
- [ ] Commit and submit PR #4 to GitHub with UI before/after screenshots

---

## PR #5: feat/macos-native-cocoa-wrapper
**Label:** `macOS Native` | **Target Date:** `2026-11-14 (Morning)` | **Branch:** `feat/macos-native-cocoa-wrapper`

### 🎯 Objective
Transform the web application into a native macOS desktop experience using Swift/Cocoa and WKWebView.

### 💡 Why this matters for Colonist
Shows extreme attention to detail and platform craftsmanship: custom window chrome, seamless traffic light semaphores inside the dark sidebar, window dragging, and menu shortcuts.

### 📦 Deliverables & Files
- `macos/`: Swift native application source code and Xcode project
- `/Applications/Hermes Studio.app`: Compiled native macOS bundle
- `start-studio.sh`: Dual daemon orchestrator launching backend + frontend


### Acceptance Checklist
- [ ] Configure NSWindow with fullSizeContentView and titlebarAppearsTransparent
- [ ] Position macOS traffic light buttons natively inside the dark sidebar top area
- [ ] Enable native window dragging across sidebar and top header areas
- [ ] Inject WKUserScript for native keyboard hotkeys (Cmd+B sidebar, Cmd+N new chat)
- [ ] Implement dual-process background orchestrator script (start-studio.sh)
- [ ] Compile and install standalone Hermes Studio.app into /Applications
- [ ] Commit and submit PR #5 to GitHub with native macOS desktop demo GIF

---

## PR #6: feat/macos-background-service-daemon
**Label:** `macOS Native` | **Status:** `Shipped & Merged to Main (28fd651)` | **Branch:** `feat/macos-background-service-daemon`

### Objective
Enable `Hermes Studio.app` to autonomously detect, launch, and manage background FastAPI (`8765`) and Next.js (`3000`) services on cold start and terminate them cleanly on quit (`Cmd+Q`).

### Deliverables & Files
- `macos/Sources/main.swift`: `ensureServicesAndLoad()` health polling and detached `Process` group launcher
- `start-studio.sh`: Non-interactive background service orchestration logging to `/tmp/hermes-studio.log`

### Acceptance Checklist
- [x] Poll localhost:3000 and 127.0.0.1:8765 on native macOS app launch
- [x] Spawn start-studio.sh automatically in background when ports are offline
- [x] Stream startup progress inside native WKWebView loading screen
- [x] Transition automatically into the workstation UI once services respond HTTP 200
- [x] Terminate child process group cleanly inside applicationWillTerminate (Cmd+Q)
- [x] Merge PR #6 into main branch (28fd651)

---

## PR #7: feat/prompt-enhancer-composer
**Label:** `Frontend / UX` | **Status:** `Shipped & Merged to Main (9d47949)` | **Branch:** `feat/prompt-enhancer-composer`

### Objective
Build an inline `$0` Prompt Enhancer inside the chat composer that transforms rough drafts in any language into structured English engineering prompts with a strict zero-emoji invariant.

### Deliverables & Files
- `backend/routers/prompt_enhancer.py`: `/api/prompt-enhancer/chat` free-tier OpenRouter pipeline and `strip_emojis()` guard
- `frontend/src/components/BottomComposer.tsx`: Inline upgrade button with dual emerald progress fill and `Prompt Enhancer` hover tooltip
- `frontend/src/components/PromptEnhancerDrawer.tsx`: Interactive Prompt Architect side drawer
- `tests/test_prompt_enhancer.py`: Unit tests for emoji stripping and payload validation

### Acceptance Checklist
- [x] Implement POST /api/prompt-enhancer/chat using $0 free-tier OpenRouter models
- [x] Enforce strict zero-emoji invariant in system prompt and regex post-processor
- [x] Add inline Prompt Enhancer button next to Send button in BottomComposer
- [x] Implement dual emerald progress fill animation and checkmark completion state
- [x] Add subtle 'Prompt Enhancer' hover tooltip below the composer action bar
- [x] Add unit tests in tests/test_prompt_enhancer.py
- [x] Merge PR #7 into main branch (9d47949)

---

## PR #10: perf/autonomous-patch-token-optimization
**Label:** `AI / Multi-Agent` | **Status:** `Shipped & Merged to Main (cd63d23)` | **Branch:** `perf/autonomous-patch-token-optimization`

### Objective
Eliminate 20k+ token blowouts and guarantee 100% reliable local disk modifications across all project types using surgical `SEARCH/REPLACE` diff blocks, 4-tier workspace path resolution, and smart relevance context filtering.

### Deliverables & Files
- `backend/services/autonomous_executor.py`: `apply_search_replace_blocks()`, `Before:` block guard, `.html`/`.css`/`.vue` support, and `node --check` runner
- `backend/services/workspace_scanner.py`: Relevance-ranked context injection (-63% to -98% token reduction)
- `backend/services/openrouter_client.py`: Conversation history code-block compaction (`_compact_history_content`)
- `backend/routers/chat.py` & `backend/database.py`: 4-tier `workspace_path` fallback and `actions_executed_json` persistence
- `frontend/src/components/MarkdownRenderer.tsx`: Collapsible `Applied to Disk` file action cards
- `tests/test_autonomous_executor.py`: 11 unit and benchmark tests

### Acceptance Checklist
- [x] Implement 4-tier workspace_path fallback (payload -> session -> project -> prompt match)
- [x] Add surgical SEARCH/REPLACE diff patching engine and Before-block protection
- [x] Expand autonomous file support to HTML, CSS, SCSS, Vue, JSX, SQL, TOML, XML
- [x] Implement smart relevance context filtering reducing input tokens by 63%-98%
- [x] Compact prior assistant code blocks in conversation_history by >85%
- [x] Render collapsible 'Applied to Disk' file cards in chat UI and pass 11/11 unit tests
- [x] Submit and merge PR #10 into main branch (commit cd63d23)

---

## PR #11: feat/files-changed-diff-summary
**Label:** `Frontend / UX` | **Status:** `Shipped & Merged to Main (4bf4b9a)` | **Branch:** `feat/files-changed-diff-summary`

### Objective
Deliver an interactive collapsible diff summary bar below assistant responses, ultra-compact surgical `// Append:` & `// Prepend:` directives for batch multi-file modifications, and silent zero-code-dump chat rendering.

### Deliverables & Files
- `frontend/src/components/FilesChangedSummaryBar.tsx`: Collapsible bar with total files changed, additions/deletions, and per-file diff submenu
- `backend/services/autonomous_executor.py`: Multi-file surgical Append/Prepend parser, line diff telemetry (`_compute_line_diff_stats`), and universal header stripping
- `frontend/src/components/MarkdownRenderer.tsx` & `backend/routers/chat.py`: Automatic code block suppression when applied directly to workspace
- `start-studio.sh`: Backend hot reloading enabled via `uvicorn --reload`
- `tests/test_autonomous_executor.py`: 13 automated unit tests

### Acceptance Checklist
- [x] Implement FilesChangedSummaryBar with expandable per-file basename and line counts
- [x] Add multi-file surgical Append and Prepend autonomous directives
- [x] Sanitize synthetic routing headers across all file types (.cs, .py, .js, .shader)
- [x] Suppress raw workspace code snippets from chat view when changes apply to disk
- [x] Cap untargeted workspace context injection to 2,800 tokens and ensure model headroom
- [x] Enable backend module reloading in start-studio.sh
- [x] Verify 13/13 unit tests pass and Next.js production build succeeds
- [x] Submit and merge PR #11 into main branch (commit 4bf4b9a)

---

## PR #12: docs/architecture-and-engineering-logs
**Label:** `Documentation` | **Status:** `Shipped & Merged to Main (ec6e9fb)` | **Branch:** `docs/architecture-and-engineering-logs`

### Objective
Publish formal Architecture Decision Records (ADRs), C4 system design diagrams, code review logs, and the living Engineering Problem & Resolution Log (`docs/ENGINEERING_PROBLEM_LOG.md`).

### Deliverables & Files
- `docs/ENGINEERING_PROBLEM_LOG.md`: Forensic root-cause analyses, architectural fixes, and token reduction benchmarks
- `docs/ARCHITECTURE.md`: C4 container topology and threat model specifications
- `docs/CODE_REVIEW_LOG.md`: Manual architectural and security review logs
- `docs/KANBAN_BOARD.md` & `docs/TRELLO_PLAN.md`: Sprint delivery roadmap and PR tracking

### Acceptance Checklist
- [x] Document Problem #1 root-cause analysis and token benchmarks in ENGINEERING_PROBLEM_LOG.md
- [x] Document Problem #2 (macOS autonomous daemon) and Problem #3 ($0 Prompt Enhancer)
- [x] Document ADR-001, ADR-002, and ADR-003 architectural decisions
- [x] Create C4 architecture diagram and 5-agent sequence flowcharts in ARCHITECTURE.md
- [x] Author CODE_REVIEW_LOG.md and KANBAN_BOARD.md
- [x] Update TRELLO_PLAN.md with PR #6 through PR #12 specifications
- [x] Submit and merge PR #12 into main branch (commit ec6e9fb)

---

## PR #13: feat/multimodal-clipboard-vision
**Label:** `AI / Multi-Agent` | **Status:** `Shipped & Merged to Main` | **Branch:** `feat/multimodal-clipboard-vision`

### Objective
Integrate native clipboard image pasting (`Cmd+V`) and multimodal vision context analysis across both the chat execution pipeline and the in-composer `$0` Prompt Enhancer, extracting visual context, UI state, and error messages while eliminating binary-to-UTF8 token corruption.

### Deliverables & Files
- `backend/services/image_analyzer.py`: Binary image header parser (`extract_image_metadata`), attachment splitter (`split_attachments`), and OpenRouter multimodal vision analyzer (`analyze_images_with_vision`)
- `backend/services/openrouter_client.py`: Binary UTF-8 corruption guard in `format_attachments_block()`, `build_multimodal_attachments_block()`, and native `image_url` routing in `acall_llm()`
- `backend/routers/chat.py` & `backend/routers/prompt_enhancer.py`: Multimodal context injection for chat workflows (`team:dev-squad` and raw models) and vision-aware prompt enhancement
- `frontend/src/components/BottomComposer.tsx`, `frontend/src/app/page.tsx`, & `frontend/src/lib/api.ts`: `Cmd+V` clipboard image capture (`handlePaste`), drag-and-drop image support, and thumbnail preview cards
- `tests/test_image_analyzer.py`: Unit tests for PNG dimension extraction, binary corruption prevention, and multimodal context synthesis

### Acceptance Checklist
- [x] Implement clipboard image paste (Cmd+V) and drag-and-drop capture in BottomComposer.tsx
- [x] Prevent binary base64 images from being decoded as UTF-8 replacement characters in format_attachments_block()
- [x] Build image_analyzer.py to extract pixel dimensions, UI context, situation, and visible error messages via vision models
- [x] Route native image_url payloads to vision-capable models and inject <image_context_analysis> blocks for text-only coding models
- [x] Integrate pasted image analysis into the inline $0 Prompt Enhancer (/api/prompt-enhancer/chat)
- [x] Add automated unit tests in tests/test_image_analyzer.py and document Problem #6 in ENGINEERING_PROBLEM_LOG.md
- [x] Submit and merge PR #13 into main branch


