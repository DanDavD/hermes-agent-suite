# Hermes Studio v2

Autonomous AI Engineering Workbench & Local Workspace Context Engine

Author: Daniel (DanDavD)  
Stack: Next.js 14 (TypeScript, Tailwind CSS) · FastAPI (Python 3.11, Pydantic v2) · SQLite (WAL mode) · OpenRouter Multi-Model Routing  
Status: Production v2.0 (Local-First)

---

## Why I Built This

I developed Hermes Studio v2 to solve real bottlenecks in my daily software and game development workflow:

1. **Eliminating SaaS Subscription Lockouts and High Costs:**  
   Flat-rate $20/month subscriptions (such as Claude Pro) enforce aggressive usage caps that lock developers out after a few multi-file refactoring runs. By routing specialized frontier and open-weights models through OpenRouter (DeepSeek V3, Qwen 2.5 Coder 32B, Gemini 2.5 Flash, and Nous Hermes 4 70B), monthly API expenditures dropped by over 80% (averaging ~$3.50/month across hundreds of tasks) with zero downtime or tier lockouts.

2. **In-Composer Prompt Enhancement & Multimodal Clipboard Vision (Zero Context-Switching):**  
   Constantly switching browser tabs to draft, translate, or refine prompts—or to paste error screenshots—interrupted my development flow. I built an integrated, zero-cost ($0.00) Prompt Enhancer and native clipboard image pasting (`Cmd+V`) directly into the composer. Pasting a screenshot extracts UI context, error logs, and situational details via vision models and synthesizes them with your prompt in one step.

3. **Autonomous Local Disk Application vs. Copy-Paste Chores:**  
   Standard AI assistants output isolated code blocks that require tedious manual copying, file creation, and syntax sanity checks. Hermes Studio intercepts structured directives (`// File:`, `// Append:`, `// Prepend:`, and surgical `SEARCH/REPLACE` diff blocks) and patches local files directly on disk, showing clean diff telemetry and reflecting immediately in GitHub Desktop.

4. **Context Window Optimization:**  
   Ingesting entire game or web codebases easily causes 20k-to-30k token blowouts. I engineered a deterministic workspace scanner with O(1) subtree pruning (`Library/`, `Temp/`, `node_modules/`, `.git/`), relevance-ranked file filtering, and conversation history compaction, cutting input token consumption by 63% to 98% per turn.

---

## System Architecture

```text
+-----------------------------------------------------------------------------------+
|                            Presentation Layer (Next.js 14)                        |
|   Dark IDE Shell · Real-Time SSE Stream Consumer · Collapsible Diff Summary Bar   |
|   In-Composer $0 Prompt Enhancer · Workspace Tree Inspector · Cost Telemetry       |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST & Server-Sent Events (SSE)
+------------------------------------------v----------------------------------------+
|                            Application Kernel (FastAPI)                           |
|   Asynchronous Pipeline Router · Pydantic v2 Contract Validation · SQLite WAL Engine|
+---------------------+-------------------------------+-----------------------------+
                      |                               |
+---------------------v---------------+ +-------------v-----------------------------+
|    Local Filesystem Context Engine  | |      Autonomous Execution Engine          |
|  Deterministic Subtree Pruner       | |  Surgical SEARCH/REPLACE Patch Applicator |
|  Relevance-Ranked File Filtering    | |  Batch Append/Prepend Directives          |
|  Path Traversal Security Guardrails | |  Line-Level Diff Telemetry (difflib)      |
+---------------------+---------------+ +-------------+-----------------------------+
                      |                               |
                      +---------------+---------------+
                                      |
                      +---------------v---------------+
                      |   Local Project on Disk       |
                      |   (Unity C#, Web, Python)     |
                      |   Direct GitHub Desktop Sync  |
                      +-------------------------------+
```

---

## Core Capabilities

### 1. Autonomous Directives & Surgical Patching
- **SEARCH/REPLACE Diff Blocks:** Modifies only affected lines rather than re-emitting entire 400-line files, saving thousands of output tokens per edit.
- **Batch Directives:** Supports `// Append:`, `// Prepend:`, and `// Delete:` directives to update multiple project files in a single concise pass (~100 tokens).
- **Clean Diffs:** Automatically strips synthetic routing comments across all file formats (`.cs`, `.py`, `.js`, `.shader`, `.html`, `.css`, `.md`) before writing to disk.
- **Collapsible Summary Bar:** Renders an inline `N file(s) changed +X -Y` bar directly below responses with an expandable per-file diff breakdown.

### 2. Multi-Agent Development Pipeline & Specialist Modes
- **Dev Squad Pipeline:** Decomposes engineering requests across five dedicated personas: Lead Architect, Code Maker, Performance Auditor, UI Maker, and UX Reviewer.
- **Specialist Raw Models:** Instant toggle between DeepSeek V3 (general systems), Qwen 2.5 Coder 32B (Unity C# and shaders), Gemini 2.5 Flash (sub-second queries), and Claude 3.5 Sonnet.
- **Career Intelligence Suite:** Integrated tools for live remote job discovery, technical interview intel extraction, and ATS-tailored resume generation.

### 3. Sandboxed Local Workspace Context Engine
- Scans repositories safely using canonical path checks and strict system directory denylists (`/etc`, `/System`, `~/.ssh`).
- Prunes noisy cache directories (`Library/`, `Temp/`, `obj/`, `node_modules/`, `.git/`).
- Prioritizes source code files within a configurable token budget ceiling.

---

## Economics & Cost Efficiency

| Execution Mode | Typical Input Tokens | Typical Output Tokens | Estimated Cost / Turn |
| :--- | :--- | :--- | :--- |
| **In-Composer Prompt Enhancer** | ~1,200 tokens | ~350 tokens | **$0.0000** (Free Tier) |
| **Targeted Code Refactor (Surgical Patch)** | ~2,400 tokens | ~80 tokens | **~$0.0008** |
| **Project-Wide Multi-File Update (10 files)** | ~2,800 tokens | ~120 tokens | **~$0.0012** |
| **5-Agent Autonomous Pipeline (Full Spec)** | ~6,500 tokens | ~2,200 tokens | **~$0.0240** |

---

## Quickstart

### Prerequisites
- macOS or POSIX environment
- Python 3.11+ with `.venv` installed
- Node.js 18+ and npm
- An [OpenRouter](https://openrouter.ai/) API key

### One-Command Launch
```bash
./start-studio.sh
```
This script automatically:
1. Verifies the local Python virtual environment and installs missing dependencies.
2. Initializes the SQLite database and executes pending schema migrations.
3. Starts the FastAPI backend with hot reloading enabled on `http://127.0.0.1:8765`.
4. Launches the Next.js dark-mode IDE on `http://localhost:3000`.

### Running Automated Tests
```bash
# Backend unit & integration test suite (17 tests)
source .venv/bin/activate
python -m unittest discover -s tests -v

# Frontend production typecheck & build
cd frontend && npm run build
```

---

## Repository Documentation

Comprehensive architectural design records, security models, and problem logs are maintained in `docs/`:
- `docs/ENGINEERING_PROBLEM_LOG.md`: Detailed root-cause analyses and verification benchmarks for all six engineering challenges solved.
- `docs/ARCHITECTURE.md`: Complete C4 diagrams, sequence flows, and filesystem threat models.
- `docs/CODE_REVIEW_LOG.md`: Cross-stack contract verification and security checklists.
- `docs/KANBAN_BOARD.md`: Agile sprint breakdown, velocity metrics, and ticket completion statuses.
- `docs/TRELLO_PLAN.md`: Production delivery roadmap and PR specifications.
- `docs/adr/`: Formal Architecture Decision Records (ADR-001 through ADR-003).
