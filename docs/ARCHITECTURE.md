# Hermes Studio v2 — System Architecture & Engineering Specification

> **Document Status:** Accepted (v2.0 Production Specification)  
> **Principal Domain:** Local-First AI Engineering Workbench, Autonomous 5-Agent Software/Game Development Pipeline & Career Intelligence Engine  
> **Stack:** Next.js 15+ (App Router, TypeScript, Tailwind CSS, Shadcn/UI) · Python 3.11+ FastAPI (Async SSE, Pydantic v2) · OpenRouter Multi-Model Routing (`Hermes 3 70B`, `Qwen 2.5 Coder 32B`, `Hermes 3 8B`)

---

## 1. Executive Summary & Design Philosophy

**Hermes Studio v2** is a local-first, Claude-Code-grade AI IDE and autonomous multi-agent engineering suite purpose-built for **Unity C# Game Engineering**, **Full-Stack Software Development**, and **Technical Career Intelligence**.

Originally prototyped as a monolithic synchronous Streamlit script (`/legacy-streamlit`), v2 re-architects the system into a decoupled **Reactive Frontend + Asynchronous FastAPI Micro-Kernel** capable of:
1. **Real-Time Server-Sent Events (SSE) Telemetry:** Streaming multi-stage agent reasoning, code generation, and review passes with zero UI thread blocking and sub-millisecond state transitions.
2. **Local Unity & Software Workspace Indexing:** Mounting local macOS/POSIX project directories directly into the agent pipeline while pruning multi-gigabyte engine artifacts (`Library/`, `Temp/`, `obj/`, `.git/`) and enforcing a deterministic **45,000-token context budget**.
3. **Heterogeneous Multi-Agent Model Routing:** Matching cognitive complexity to model capability across `Nous Hermes 3 70B`, `Qwen 2.5 Coder 32B`, and `Nous Hermes 3 8B`, reducing monthly inference expenditure by **80–85%** (~$3.50/month for 150 full 5-agent pipelines) compared to flat-rate frontier subscriptions.

---

## 2. High-Level System Architecture

The system is partitioned into four strict architectural boundaries: the **Presentation Layer (Next.js App Router)**, the **Application Gateway & Orchestration Layer (FastAPI)**, the **Local Filesystem Sandbox (Workspace Scanner)**, and **External Inference & Search Providers (OpenRouter + DuckDuckGo)**.

```mermaid
flowchart TB
    subgraph Client["Presentation Layer — Next.js (TypeScript + Tailwind + Shadcn/UI)"]
        UI_Shell["IDE Shell & Command Palette"]
        Squad_View["5-Agent Dev Squad Console (SSE Consumer)"]
        Workspace_Drawer["Local Unity/Code Workspace Inspector"]
        Career_Suite["Career Intelligence & ATS Studio"]
        Interview_Sim["Interactive Mock Technical Interviewer"]
    end

    subgraph Backend["Application & Orchestration Layer — Python FastAPI"]
        API_Router["FastAPI REST & SSE Router (/api/v1/*)"]
        Pydantic_Guard["Pydantic v2 Schema & Security Validator"]
        Orchestrator["Async 5-Agent DevSquad State Machine"]
        Context_Engine["Unity/Software Context Indexer & Token Budgeter"]
        Career_Engine["Career Intelligence & DuckDuckGo Scraper"]
    end

    subgraph LocalFS["Host OS Sandbox (macOS / POSIX)"]
        Unity_Proj["Local Unity / C# / Software Repository"]
        Pruned_Dirs["Ignored Artifacts (Library/, Temp/, obj/, node_modules/)"]
        DotEnv[".env & Local Session Persistence"]
    end

    subgraph External["External Inference & Search Gateways"]
        OpenRouter["OpenRouter API Gateway (HTTPS / TLS 1.3)"]
        Hermes70B["Nous Hermes 3 70B (Leader / Code Reviewer / UI Maker)"]
        Qwen32B["Qwen 2.5 Coder 32B (Specialist Code Maker)"]
        Hermes8B["Nous Hermes 3 8B (High-Speed UI Reviewer)"]
        DDG["DuckDuckGo Live Search API (Jobs & Reddit Intel)"]
    end

    UI_Shell --> Squad_View
    UI_Shell --> Workspace_Drawer
    UI_Shell --> Career_Suite
    UI_Shell --> Interview_Sim

    Squad_View -- "POST /api/squad/stream (SSE)" --> API_Router
    Workspace_Drawer -- "POST /api/workspace/scan" --> API_Router
    Career_Suite -- "POST /api/jobs/* & /api/resume/*" --> API_Router
    Interview_Sim -- "POST /api/interview/chat" --> API_Router

    API_Router --> Pydantic_Guard
    Pydantic_Guard --> Orchestrator
    Pydantic_Guard --> Context_Engine
    Pydantic_Guard --> Career_Engine

    Context_Engine -- "Read-Only Canonical Path Walk" --> Unity_Proj
    Context_Engine -. "Prunes & Blocks" .-> Pruned_Dirs
    Orchestrator -- "Injects 45k Token Context" --> Context_Engine

    Orchestrator --> OpenRouter
    Career_Engine --> OpenRouter
    Career_Engine --> DDG

    OpenRouter --> Hermes70B
    OpenRouter --> Qwen32B
    OpenRouter --> Hermes8B
```

---

## 3. Core Subsystem Specifications

### 3.1. Presentation Layer (`/frontend`)
- **Framework:** Next.js (App Router) with strict TypeScript (`strict: true`).
- **Styling & Design System:** Dark-mode native engineering workbench built with Tailwind CSS and Shadcn/UI primitives (`zinc-950` surface hierarchy, `indigo-500` active agent indicators, `emerald-500` pass badges, `amber-500` token budget warnings).
- **Streaming State Management:** Custom `fetch` + `ReadableStream` SSE parser decoding chunked `data: {...}\n\n` events into an immutable per-agent execution timeline without blocking React rendering or losing scroll lock.
- **Zero-Trust Secret Handling:** OpenRouter API keys can be configured server-side via root `.env` or passed transiently over localhost headers without persisting plaintext secrets in third-party telemetry.

### 3.2. Orchestration & API Layer (`/backend`)
- **Framework:** Python FastAPI running on Uvicorn with asynchronous request handlers and generator-backed `StreamingResponse` endpoints.
- **Contract-First Typing:** Every request payload and SSE event frame is strictly validated via Pydantic v2 models before execution.
- **Fault Isolation:** Upstream OpenRouter rate limits, network timeouts, or DuckDuckGo scraping anomalies are caught at the service boundary and emitted as structured error frames rather than crashing the Uvicorn worker process.

---

## 4. Multi-Agent Dev Squad Pipeline (Sequence & State Flow)

The flagship **5-Agent Dev Squad** decomposes complex engineering tasks into five specialized, sequential cognitive stages. Unlike single-shot LLM prompts that suffer from instruction dilution when asked to simultaneously architect, code, optimize memory, and design UI, Hermes Studio v2 isolates each concern into a dedicated system persona and specialized model weight class.

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Software / Game Engineer
    participant UI as Next.js IDE Client
    participant API as FastAPI SSE Endpoint
    participant Scanner as Workspace Context Scanner
    participant Leader as Agent 1: Leader (Hermes 3 70B)
    participant Coder as Agent 2: Code Maker (Qwen 2.5 Coder 32B)
    participant Reviewer as Agent 3: Code Reviewer (Hermes 3 70B)
    participant UIMaker as Agent 4: UI Maker (Hermes 3 70B)
    participant UIRev as Agent 5: UI Reviewer (Hermes 3 8B)

    Engineer->>UI: Input Task + Local Unity/Code Workspace Path
    UI->>API: POST /api/squad/stream (task, workspace_path, role_models)
    
    opt Workspace Path Provided
        API->>Scanner: scan_workspace(workspace_path, max_tokens=45000)
        Scanner-->>API: Structured File Tree + Prioritized Source Context (.cs, .shader, .ts, .py)
        API-->>UI: SSE Event [workspace_indexed: files_count, token_estimate]
    end

    API-->>UI: SSE Event [step=1, agent="Leader", status="running"]
    API->>Leader: Prompt(Task + Indexed Workspace Context)
    Leader-->>API: System Architecture, Data Contracts & Component Specs
    API-->>UI: SSE Event [step=1, agent="Leader", status="complete", output=Spec]

    API-->>UI: SSE Event [step=2, agent="Code Maker", status="running"]
    API->>Coder: Prompt(Task + Leader Spec + Workspace Context)
    Coder-->>API: Production Code (Zero-Placeholder C# / TypeScript / Python)
    API-->>UI: SSE Event [step=2, agent="Code Maker", status="complete", output=Code]

    API-->>UI: SSE Event [step=3, agent="Code Reviewer", status="running"]
    API->>Reviewer: Prompt(Task + Code Maker Output)
    Reviewer-->>API: Memory/GC Audit (Update() Allocations), Edge Cases & Patched Code
    API-->>UI: SSE Event [step=3, agent="Code Reviewer", status="complete", output=Audit]

    API-->>UI: SSE Event [step=4, agent="UI Maker", status="running"]
    API->>UIMaker: Prompt(Task + Leader Spec + Core Code)
    UIMaker-->>API: UI Toolkit / uGUI / React Hierarchy & Controller Bindings
    API-->>UI: SSE Event [step=4, agent="UI Maker", status="complete", output=UICode]

    API-->>UI: SSE Event [step=5, agent="UI Reviewer", status="running"]
    API->>UIRev: Prompt(Task + UI Maker Output)
    UIRev-->>API: Aspect-Ratio Responsiveness, Interaction States & Accessibility Sign-Off
    API-->>UI: SSE Event [step=5, agent="UI Reviewer", status="complete", output=UXAudit]

    API-->>UI: SSE Event [pipeline_complete: total_duration_ms, token_summary]
```

### Agent Responsibilities & Verification Criteria
| Step | Agent Persona | Default Model | Primary Engineering Focus | Domain Verification Targets |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Leader (Architect)** | `Hermes 3 70B` | System decomposition, data flow, interface contracts | ScriptableObject schemas, decoupled event buses, SOLID boundaries |
| **2** | **Code Maker** | `Qwen 2.5 Coder 32B` | High-density syntax synthesis, complete implementation | Complete namespaces, strict typing, zero `// TODO` placeholders |
| **3** | **Code Reviewer** | `Hermes 3 70B` | Performance profiling, static logic analysis, bug patching | Zero heap allocations in Unity `Update()`/`FixedUpdate()`, null safety, race conditions |
| **4** | **UI Maker** | `Hermes 3 70B` | View hierarchy, reactive state binding, controller logic | Unity UI Toolkit (`.uxml`/`.uss`), uGUI Canvas scaling, or React/Tailwind components |
| **5** | **UI Reviewer** | `Hermes 3 8B` | Ergonomics, visual hierarchy, interaction state completeness | 16:9 / 21:9 / Ultrawide anchor behavior, hover/disabled/focus states |

---

## 5. Local Unity & Software Workspace Context Indexing

A core innovation in Hermes Studio v2 (detailed in [ADR-002](./adr/002-local-unity-workspace-scanner-and-token-budgeting.md)) is the **Deterministic Workspace Context Scanner**. Game engines like Unity generate tens of thousands of cache, metadata, and binary files (`Library/`, `Temp/`, `Logs/`) that will immediately exhaust an LLM's context window and bankrupt token budgets if naively ingested.

```mermaid
flowchart LR
    InputPath["User Input Path"] --> Canonicalize["Path.resolve() & Symlink Canonicalization"]
    Canonicalize --> Guard{"Security Boundary Check\n(Exists, Directory, Non-System Root)"}
    Guard -- "Violation" --> Reject["Raise HTTP 400 / 403 SecurityException"]
    Guard -- "Valid" --> Walk["os.walk() Top-Down Traversal"]

    Walk --> PruneDirs{"Directory in Deny-List?\n(Library, Temp, obj, .git, node_modules)"}
    PruneDirs -- "Yes" --> SkipSubtree["In-Place Dir List Pruning (O(1) Skip)"]
    PruneDirs -- "No" --> FilterExt{"Allowed Source Extension?\n(.cs, .shader, .hlsl, .uxml, .uss, .ts, .py, .json)"}

    FilterExt -- "No (.meta, .png, .fbx, .dll)" --> IgnoreFile["Skip Binary / Asset File"]
    FilterExt -- "Yes" --> SizeCheck{"File Size <= Max Per-File Cap\n& Token Budget <= 45,000?"}

    SizeCheck -- "Budget Full" --> TruncateNotice["Append Tree Manifest Only (Omit Body)"]
    SizeCheck -- "Within Budget" --> AppendContext["Read UTF-8 Safe Content & Increment Token Counter (chars / 4)"]
    AppendContext --> OutputPayload["Structured Workspace Context Payload"]
    TruncateNotice --> OutputPayload
```

---

## 6. Security Boundaries & Threat Model

Because Hermes Studio v2 runs locally with access to the host filesystem and external LLM APIs, strict defense-in-depth controls are enforced at the FastAPI boundary:

```mermaid
flowchart TD
    subgraph Untrusted["Untrusted / Semi-Trusted Inputs"]
        ReqPath["Workspace Directory Path Request"]
        WebSearch["DuckDuckGo Scraped HTML/Snippets"]
        EnvKey["OpenRouter API Key Input"]
    end

    subgraph Controls["FastAPI Security Enforcement Layer"]
        C1["1. Canonical Path Resolution & System Root Denylist\nBlocks /, /etc, /System, /Users root, ~/.ssh, ~/.aws"]
        C2["2. Read-Only Filesystem Operations\nScanner never executes, mutates, or deletes host files"]
        C3["3. Binary & Dotfile Exclusion\nBlocks .env, *.pem, *.key, *.sqlite3 from LLM context ingestion"]
        C4["4. Token & Byte Ceiling Circuit Breaker\nHard cap at 45,000 tokens (~180 KB text) prevents DoS / OOM"]
        C5["5. CORS & Localhost Origin Binding\nRestricts API access to local Next.js origin"]
    end

    ReqPath --> C1 --> C2 --> C3 --> C4
    WebSearch --> C4
    EnvKey --> C5
```

1. **Path Traversal & Sensitive Directory Prevention:** All workspace paths undergo `Path(raw_path).expanduser().resolve()`. Traversal attempts (`../../etc/passwd`) or attempts to index sensitive system/credential directories (`/etc`, `/var`, `/System`, `~/.ssh`, `~/.aws`, `~/.gnupg`) are deterministically rejected with HTTP `403 Forbidden`.
2. **Secret Exfiltration Prevention:** Even within a valid project workspace, secret files (`.env`, `.env.*`, `*.pem`, `*.key`, `credentials.json`) and Unity `.meta` GUID noise are strictly excluded from the context payload before any prompt leaves the machine to OpenRouter.
3. **Read-Only Invariant:** The workspace scanner operates exclusively with read-only file descriptors (`open(..., mode="r", encoding="utf-8", errors="replace")`) and never invokes shell sub-processes (`subprocess.Popen(..., shell=True)` is forbidden).

---

## 7. Repository Directory Structure

```text
hermes-agent-suite/
├── backend/                  # FastAPI Async Backend, Workspace Scanner & SSE Orchestrator
├── frontend/                 # Next.js 15+ (App Router), TypeScript, Tailwind & Shadcn/UI IDE
├── docs/                     # Architectural Specifications & Engineering Decision Records
│   ├── ARCHITECTURE.md       # System Architecture & Threat Model (this document)
│   └── adr/                  # Architecture Decision Records (ADRs)
│       ├── 001-nextjs-fastapi-decoupled-architecture.md
│       ├── 002-local-unity-workspace-scanner-and-token-budgeting.md
│       └── 003-hybrid-openrouter-multi-agent-orchestration.md
├── legacy-streamlit/         # Archived v1 Monolithic Streamlit Prototype & CLI
│   ├── agents/               # v1 Synchronous DevSquad & JobAssistant
│   ├── app.py                # v1 Streamlit Dashboard
│   ├── cli.py                # v1 Terminal Runner
│   └── config.py             # v1 Model Role Mappings
├── .env.example              # Environment variable template
├── .gitignore                # Git tracking exclusions
├── master_resume_example.md  # Sample engineering profile for ATS Resume Tailor testing
└── README.md                 # Project overview, benchmarks & quickstart guide
```

---

## 8. Architecture Decision Records (ADR Index)

- **[ADR-001: Migration from Monolithic Streamlit to Decoupled Next.js + FastAPI Architecture](./adr/001-nextjs-fastapi-decoupled-architecture.md)**
- **[ADR-002: Local Unity Workspace Scanner, Directory Pruning, and 45k Token Budgeting](./adr/002-local-unity-workspace-scanner-and-token-budgeting.md)**
- **[ADR-003: Cost-Optimized Hybrid Multi-Agent Orchestration via OpenRouter](./adr/003-hybrid-openrouter-multi-agent-orchestration.md)**
