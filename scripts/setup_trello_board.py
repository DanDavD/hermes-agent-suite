#!/usr/bin/env python3
"""
Hermes Studio v2 — Trello Board Automation Script
Creates and populates the complete Agile Kanban Board for the Hermes Studio project
tailored for the Colonist Product Developer Intern application portfolio.

Usage:
  python3 scripts/setup_trello_board.py --api-key YOUR_KEY --token YOUR_TOKEN
  python3 scripts/setup_trello_board.py (will prompt or read from TRELLO_API_KEY / TRELLO_TOKEN)
  python3 scripts/setup_trello_board.py --dry-run (previews cards & tasks without calling API)
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Any, Optional

BOARD_NAME = "Hermes Studio v2 — Product Dev & AI Engineering (Nov 12-14)"
BOARD_DESC = (
    "Production delivery roadmap for Hermes Studio v2: Autonomous Multi-Agent AI IDE & "
    "Local Workspace Context Engine. Built to solve high Claude subscription costs, "
    "showcasing AI fluency, async ownership, and polished product design for the "
    "Colonist Product Developer Intern role."
)

LISTS = [
    {"name": "📋 Backlog (Road to Nov 14)", "pos": "1"},
    {"name": "🏗️ In Progress", "pos": "2"},
    {"name": "🔍 In Review / PR Open", "pos": "3"},
    {"name": "🚀 Shipped & Merged to Main", "pos": "4"},
]

LABELS = [
    {"name": "Backend / API", "color": "orange"},
    {"name": "Frontend / UX", "color": "blue"},
    {"name": "AI / Multi-Agent", "color": "purple"},
    {"name": "Architecture & ADR", "color": "green"},
    {"name": "macOS Native", "color": "yellow"},
    {"name": "Documentation", "color": "sky"},
]

CARDS_DATA = [
    {
        "title": "PR #1: feat/backend-core-sqlite-fastapi",
        "label": "Backend / API",
        "delivery_date": "2026-11-12 (Morning)",
        "branch": "feat/backend-core-sqlite-fastapi",
        "desc": (
            "### 🎯 Objective\n"
            "Build the foundational asynchronous backend using FastAPI, SQLite persistence with WAL mode, "
            "OpenRouter streaming client, and token cost tracking.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Demonstrates full-stack ownership, clean decoupled architecture, and financial mindfulness "
            "by tracking exact USD micro-costs per LLM generation.\n\n"
            "### 📦 Deliverables & Files\n"
            "- `backend/main.py`: FastAPI server with CORS & lifespan DB initialization\n"
            "- `backend/config.py`: Environment configuration and model tier definitions\n"
            "- `backend/database.py`: SQLite engine with WAL mode and schema definitions\n"
            "- `backend/models/schemas.py`: Pydantic v2 schemas for sessions, messages, projects\n"
            "- `backend/services/openrouter_client.py`: OpenRouter API client with streaming\n"
            "- `legacy-streamlit/`: Archival of monolithic v1 prototype\n"
        ),
        "checklists": [
            "Archive legacy Streamlit monolithic scripts to /legacy-streamlit",
            "Implement FastAPI application entrypoint with lifespan event handlers",
            "Create SQLite schema: sessions, messages, projects, and telemetry",
            "Implement OpenRouter client with token usage calculation ($0.024/run)",
            "Add Pydantic v2 validation models for all request/response contracts",
            "Verify backend boots on port 8765 and passes health checks",
            "Commit and submit PR #1 to GitHub with structured markdown description",
        ],
    },
    {
        "title": "PR #2: feat/local-workspace-scanner",
        "label": "Architecture & ADR",
        "delivery_date": "2026-11-12 (Afternoon)",
        "branch": "feat/local-workspace-scanner",
        "desc": (
            "### 🎯 Objective\n"
            "Implement the Local Workspace Context Engine featuring a strict 45,000-token ceiling, "
            "smart subtree pruning, and native macOS Finder folder picking.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Solves the real-world problem of context window blowout and massive API bills. "
            "Prunes noise (node_modules, Library, .git) so AI only reads high-signal game and product code.\n\n"
            "### 📦 Deliverables & Files\n"
            "- `backend/services/workspace_scanner.py`: Recursive tree walker with file pruning\n"
            "- `backend/routers/workspace.py`: Workspace scanning and Finder selection endpoints\n"
            "- Security guardrails against path traversal outside the approved workspace\n"
        ),
        "checklists": [
            "Build recursive directory scanner with O(1) subtree pruning for node_modules/.git/Library",
            "Implement 45k token context budget ceiling with file prioritization",
            "Add native macOS AppleScript folder picker endpoint (/api/workspace/pick-finder)",
            "Implement security checks blocking path traversal and sensitive files (.env, .ssh)",
            "Test scanner with large Unity/React repositories to confirm sub-100ms response",
            "Commit and submit PR #2 to GitHub with context budget verification logs",
        ],
    },
    {
        "title": "PR #3: feat/multi-agent-orchestrator",
        "label": "AI / Multi-Agent",
        "delivery_date": "2026-11-13 (Morning)",
        "branch": "feat/multi-agent-orchestrator",
        "desc": (
            "### 🎯 Objective\n"
            "Implement the 5-Agent Autonomous Dev Squad pipeline and Career Intelligence workflows.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Direct proof of 'AI-first mindset' and treating AI fluency as a multiplier. "
            "Orchestrates specialized models (Hermes 70B for architecture + Qwen 2.5 Coder 32B for code gen + "
            "Hermes 8B for UX audit) with structured handoffs.\n\n"
            "### 📦 Deliverables & Files\n"
            "- `backend/services/workflows/dev_squad.py`: 5-agent sequential orchestration\n"
            "- `backend/services/workflows/career_hunter.py`: ATS resume & live job matcher\n"
            "- `backend/services/workflows/content_video.py`: Script generation pipeline\n"
            "- `backend/routers/chat.py`: Multi-agent streaming execution router\n"
        ),
        "checklists": [
            "Define 5-agent pipeline: Leader -> Coder -> Code Reviewer -> UI Maker -> UI Reviewer",
            "Implement agent-to-agent prompt handoff passing previous thoughts and diffs",
            "Configure hybrid model routing (Hermes 70B + Qwen Coder 32B + Hermes 8B)",
            "Implement real-time agent execution telemetry (tokens, latency, USD spend)",
            "Build ATS resume optimization and live interview coach agent workflows",
            "Test multi-agent code generation with Unity C# scripts and Next.js components",
            "Commit and submit PR #3 to GitHub with agent trace screenshots",
        ],
    },
    {
        "title": "PR #4: feat/nextjs-workstation-ui",
        "label": "Frontend / UX",
        "delivery_date": "2026-11-13 (Afternoon)",
        "branch": "feat/nextjs-workstation-ui",
        "desc": (
            "### 🎯 Objective\n"
            "Deliver a Claude-grade dark UI workstation using Next.js 14, TypeScript, and Tailwind CSS.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Direct alignment with Colonist's core need: 'Build and improve game UI and UX, with a strong focus "
            "on clarity, polish, and fun. You care about user experience, not just the code.'\n\n"
            "### 📦 Deliverables & Files\n"
            "- `frontend/src/app/page.tsx`: Core workstation view with responsive layout\n"
            "- `frontend/src/components/Sidebar.tsx`: Collapsible project tree with Cmd+B shortcut\n"
            "- `frontend/src/components/BottomComposer.tsx`: Auto-resizing composer & inline send pill\n"
            "- `frontend/src/components/AgentStepsAccordion.tsx`: Live step-by-step reasoning view\n"
            "- `frontend/src/components/MarkdownRenderer.tsx`: Code highlighter with copy button\n"
        ),
        "checklists": [
            "Initialize Next.js App Router with dark theme and Tailwind CSS palette",
            "Implement collapsible project/chat sidebar with keyboard shortcut (Cmd+B)",
            "Build centered composer with auto-expand, inline send circle, and folder picker",
            "Create AgentStepsAccordion showing real-time agent thoughts, tokens, and latency",
            "Integrate syntax-highlighted code blocks with 1-click clipboard copy",
            "Add live API credit balance indicator in the sidebar footer",
            "Verify responsive layout and zero layout shift when opening/closing sidebars",
            "Commit and submit PR #4 to GitHub with UI before/after screenshots",
        ],
    },
    {
        "title": "PR #5: feat/macos-native-cocoa-wrapper",
        "label": "macOS Native",
        "delivery_date": "2026-11-14 (Morning)",
        "branch": "feat/macos-native-cocoa-wrapper",
        "desc": (
            "### 🎯 Objective\n"
            "Transform the web application into a native macOS desktop experience using Swift/Cocoa and WKWebView.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Shows extreme attention to detail and platform craftsmanship: custom window chrome, "
            "seamless traffic light semaphores inside the dark sidebar, window dragging, and menu shortcuts.\n\n"
            "### 📦 Deliverables & Files\n"
            "- `macos/`: Swift native application source code and Xcode project\n"
            "- `/Applications/Hermes Studio.app`: Compiled native macOS bundle\n"
            "- `start-studio.sh`: Dual daemon orchestrator launching backend + frontend\n"
        ),
        "checklists": [
            "Configure NSWindow with fullSizeContentView and titlebarAppearsTransparent",
            "Position macOS traffic light buttons natively inside the dark sidebar top area",
            "Enable native window dragging across sidebar and top header areas",
            "Inject WKUserScript for native keyboard hotkeys (Cmd+B sidebar, Cmd+N new chat)",
            "Implement dual-process background orchestrator script (start-studio.sh)",
            "Compile and install standalone Hermes Studio.app into /Applications",
            "Commit and submit PR #5 to GitHub with native macOS desktop demo GIF",
        ],
    },
    {
        "title": "PR #6: docs/system-architecture-case-study",
        "label": "Documentation",
        "delivery_date": "2026-11-14 (Afternoon)",
        "branch": "docs/system-architecture-case-study",
        "desc": (
            "### 🎯 Objective\n"
            "Publish formal Architecture Decision Records (ADRs), system design diagrams, "
            "cost benchmark analysis, and a comprehensive portfolio README for recruiters.\n\n"
            "### 💡 Why this matters for Colonist\n"
            "Exemplifies Colonist values: 'Dependability', 'Clear Communication' (async written clarity), "
            "and 'Continuous Learning'. Shows engineering maturity beyond just hacking code.\n\n"
            "### 📦 Deliverables & Files\n"
            "- `docs/ARCHITECTURE.md`: C4 container topology and threat model specifications\n"
            "- `docs/adr/001-nextjs-fastapi-decoupled-architecture.md`\n"
            "- `docs/adr/002-local-unity-workspace-scanner-and-token-budgeting.md`\n"
            "- `docs/adr/003-hybrid-openrouter-multi-agent-orchestration.md`\n"
            "- `docs/CODE_REVIEW_LOG.md`: Manual architectural and security review logs\n"
            "- `README.md`: High-impact project case study and live demo walkthrough\n"
        ),
        "checklists": [
            "Document ADR-001: Next.js + FastAPI decoupling rationale",
            "Document ADR-002: Local workspace token budgeting & scanner architecture",
            "Document ADR-003: Hybrid OpenRouter multi-agent model economics",
            "Create C4 architecture diagram and 5-agent sequence flowcharts in Mermaid",
            "Author comprehensive README.md tailored to the Colonist Product Developer role",
            "Add cost comparison analysis ($20/mo Claude vs $0.80/mo Hermes OpenRouter)",
            "Review and merge PR #6 into main branch for release v2.0.0",
        ],
    },
]


class TrelloClient:
    def __init__(self, api_key: str, token: str):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Any:
        query_params = {"key": self.api_key, "token": self.token}
        if params:
            query_params.update(params)

        url = f"{self.base_url}{path}?" + urllib.parse.urlencode(query_params)
        data = None
        headers = {"Accept": "application/json"}

        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            print(f"\n❌ Trello API Error [{e.code}]: {err_msg}", file=sys.stderr)
            raise

    def create_board(self, name: str, desc: str) -> Dict[str, Any]:
        params = {
            "name": name,
            "desc": desc,
            "defaultLists": "false",
            "prefs_permissionLevel": "private",
            "prefs_background": "charcoal",
        }
        return self._request("POST", "/boards", params=params)

    def create_list(self, board_id: str, name: str, pos: str) -> Dict[str, Any]:
        params = {"name": name, "pos": pos}
        return self._request("POST", f"/boards/{board_id}/lists", params=params)

    def create_label(self, board_id: str, name: str, color: str) -> Dict[str, Any]:
        params = {"name": name, "color": color}
        return self._request("POST", f"/boards/{board_id}/labels", params=params)

    def create_card(self, list_id: str, name: str, desc: str, label_ids: List[str]) -> Dict[str, Any]:
        params = {
            "idList": list_id,
            "name": name,
            "desc": desc,
            "idLabels": ",".join(label_ids),
        }
        return self._request("POST", "/cards", params=params)

    def create_checklist(self, card_id: str, name: str = "Acceptance Checklist") -> Dict[str, Any]:
        params = {"idCard": card_id, "name": name}
        return self._request("POST", "/checklists", params=params)

    def add_checklist_item(self, checklist_id: str, name: str) -> Dict[str, Any]:
        params = {"name": name, "checked": "false"}
        return self._request("POST", f"/checklists/{checklist_id}/checkItems", params=params)


def print_dry_run():
    print("\n🔍 --- DRY RUN: Trello Board Structure Preview ---\n")
    print(f"Board Name: {BOARD_NAME}")
    print(f"Description: {BOARD_DESC}\n")
    print("Lists to create:")
    for l in LISTS:
        print(f"  • {l['name']}")
    print("\nLabels to create:")
    for lb in LABELS:
        print(f"  • {lb['name']} ({lb['color']})")
    print("\nCards & Checklists:")
    for card in CARDS_DATA:
        print(f"\n📌 [{card['label']}] {card['title']}")
        print(f"   Target: {card['delivery_date']} | Branch: {card['branch']}")
        print("   Checklist items:")
        for item in card["checklists"]:
            print(f"     [ ] {item}")
    print("\n✅ Dry run complete. Run without --dry-run with your Trello credentials to deploy.\n")


def print_trello_instructions():
    print("\n" + "=" * 70)
    print("🔑 HOW TO GET YOUR FREE TRELLO API KEY & TOKEN (Takes 30 seconds):")
    print("=" * 70)
    print("1. Log in to Trello in your browser.")
    print("2. Open: https://trello.com/power-ups/admin")
    print("3. Click 'New' or select an existing Power-Up workspace.")
    print("4. Click 'Generate a new API key'.")
    print("5. Copy your 'API Key'.")
    print("6. Right next to the API Key, click the 'Token' hyperlink to generate your user Token.")
    print("7. Run this script:")
    print("   python3 scripts/setup_trello_board.py --api-key YOUR_KEY --token YOUR_TOKEN")
    print("   (Or export TRELLO_API_KEY and TRELLO_TOKEN in your terminal)")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Create Trello Kanban board for Hermes Studio v2")
    parser.add_argument("--api-key", help="Trello API Key (or env TRELLO_API_KEY)")
    parser.add_argument("--token", help="Trello User Token (or env TRELLO_TOKEN)")
    parser.add_argument("--dry-run", action="store_true", help="Preview board layout without contacting Trello")
    parser.add_argument("--export-markdown", help="Save layout as markdown file (e.g. docs/TRELLO_PLAN.md)")

    args = parser.parse_args()

    if args.dry_run:
        print_dry_run()
        return

    if args.export_markdown:
        # Write markdown summary
        with open(args.export_markdown, "w", encoding="utf-8") as f:
            f.write(f"# {BOARD_NAME}\n\n{BOARD_DESC}\n\n")
            for c in CARDS_DATA:
                f.write(f"## {c['title']}\n")
                f.write(f"**Label:** `{c['label']}` | **Target Date:** `{c['delivery_date']}` | **Branch:** `{c['branch']}`\n\n")
                f.write(f"{c['desc']}\n\n")
                f.write("### Acceptance Checklist\n")
                for item in c["checklists"]:
                    f.write(f"- [ ] {item}\n")
                f.write("\n---\n\n")
        print(f"✅ Exported board plan to {args.export_markdown}")
        return

    api_key = args.api_key or os.getenv("TRELLO_API_KEY")
    token = args.token or os.getenv("TRELLO_TOKEN")

    if not api_key or not token:
        print_trello_instructions()
        try:
            api_key = input("Enter your Trello API Key (or press Ctrl+C to cancel): ").strip()
            token = input("Enter your Trello User Token: ").strip()
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            sys.exit(0)

        if not api_key or not token:
            print("❌ Both API Key and Token are required to create the Trello board.")
            sys.exit(1)

    print("\n🚀 Connecting to Trello API...")
    client = TrelloClient(api_key, token)

    # 1. Create Board
    print(f"📋 Creating board: '{BOARD_NAME}'...")
    board = client.create_board(BOARD_NAME, BOARD_DESC)
    board_id = board["id"]
    board_url = board["url"]
    print(f"   ✓ Board created! ID: {board_id}")
    print(f"   ✓ URL: {board_url}")

    # 2. Create Labels
    print("\n🏷️  Configuring labels...")
    label_map = {}
    for lb in LABELS:
        created_label = client.create_label(board_id, lb["name"], lb["color"])
        label_map[lb["name"]] = created_label["id"]
        print(f"   ✓ Label '{lb['name']}' ({lb['color']}) added")

    # 3. Create Lists
    print("\n📑 Creating workflow lists...")
    list_map = {}
    for lst in LISTS:
        created_list = client.create_list(board_id, lst["name"], lst["pos"])
        list_map[lst["name"]] = created_list["id"]
        print(f"   ✓ List '{lst['name']}' created")

    # Place PR #1 into "In Progress" and the rest into "Backlog"
    in_progress_list_id = list_map["🏗️ In Progress"]
    backlog_list_id = list_map["📋 Backlog (Road to Nov 14)"]

    print("\n📌 Creating cards and acceptance checklists...")
    for i, card_info in enumerate(CARDS_DATA):
        # First card starts in In Progress, rest in Backlog
        target_list_id = in_progress_list_id if i == 0 else backlog_list_id
        assigned_label_id = label_map.get(card_info["label"])
        label_ids = [assigned_label_id] if assigned_label_id else []

        card = client.create_card(
            list_id=target_list_id,
            name=card_info["title"],
            desc=card_info["desc"],
            label_ids=label_ids,
        )
        card_id = card["id"]
        print(f"   ✓ Card created: {card_info['title']}")

        # Create checklist on card
        checklist = client.create_checklist(card_id, "Acceptance Criteria & Git Tasks")
        checklist_id = checklist["id"]

        for item in card_info["checklists"]:
            client.add_checklist_item(checklist_id, item)

    print("\n" + "=" * 70)
    print("🎉 SUCCESS! Your Trello Board is fully initialized and populated:")
    print(f"👉 {board_url}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
