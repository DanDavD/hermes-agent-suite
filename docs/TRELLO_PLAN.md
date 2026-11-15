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

## PR #6: docs/system-architecture-case-study
**Label:** `Documentation` | **Target Date:** `2026-11-14 (Afternoon)` | **Branch:** `docs/system-architecture-case-study`

### 🎯 Objective
Publish formal Architecture Decision Records (ADRs), system design diagrams, cost benchmark analysis, and a comprehensive portfolio README for recruiters.

### 💡 Why this matters for Colonist
Exemplifies Colonist values: 'Dependability', 'Clear Communication' (async written clarity), and 'Continuous Learning'. Shows engineering maturity beyond just hacking code.

### 📦 Deliverables & Files
- `docs/ARCHITECTURE.md`: C4 container topology and threat model specifications
- `docs/adr/001-nextjs-fastapi-decoupled-architecture.md`
- `docs/adr/002-local-unity-workspace-scanner-and-token-budgeting.md`
- `docs/adr/003-hybrid-openrouter-multi-agent-orchestration.md`
- `docs/CODE_REVIEW_LOG.md`: Manual architectural and security review logs
- `README.md`: High-impact project case study and live demo walkthrough


### Acceptance Checklist
- [ ] Document ADR-001: Next.js + FastAPI decoupling rationale
- [ ] Document ADR-002: Local workspace token budgeting & scanner architecture
- [ ] Document ADR-003: Hybrid OpenRouter multi-agent model economics
- [ ] Create C4 architecture diagram and 5-agent sequence flowcharts in Mermaid
- [ ] Author comprehensive README.md tailored to the Colonist Product Developer role
- [ ] Add cost comparison analysis ($20/mo Claude vs $0.80/mo Hermes OpenRouter)
- [ ] Review and merge PR #6 into main branch for release v2.0.0

---

