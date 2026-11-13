"""Autonomous Tool Execution Service for Hermes Studio v2.

Handles:
1. Dynamic prompt intent classification (token conservation).
2. Autonomous code file extraction and direct disk modification.
3. Automated test runner execution (e.g., dotnet test / pytest) inside the workspace.
4. Smart bilingual session title generation (Spanish/English).
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.services.workspace_scanner import write_workspace_file


# ==============================================================================
# 1. SMART SESSION TITLE GENERATOR
# ==============================================================================

SPANISH_TOPIC_MAP = [
    (r"(?:ayudame\s+(?:a\s+)?entender|aprender|ensename)\s+python", "Help with Python Learning"),
    (r"(?:ayudame\s+(?:a\s+)?entender|aprender|ensename)\s+c#", "Help with C# Learning"),
    (r"(?:ayudame\s+(?:a\s+)?entender|aprender|ensename)\s+unity", "Unity Engine Guide"),
    (r"(?:500\s*mil\s*tokens|tokens|costo|caro|quem(?:e|ar))", "Token Usage & Cost Optimization"),
    (r"(?:musica|audio|sfx|cancion|sonido).*(?:witcher|epica|tetrica|godboard)", "Game Music & Audio Design"),
    (r"(?:cual|qué|que)\s+(?:seria|es)\s+el\s+mejor\s+modelo.*(?:musica|audio|sfx)", "Game Music & SFX Model Selection"),
    (r"(?:cual|qué|que)\s+(?:seria|es)\s+el\s+mejor\s+modelo", "Best AI Model Selection"),
    (r"(?:corre|ejecuta|correr)\s+(?:los\s+)?tests", "Project Unit Tests"),
    (r"(?:crea|agrega|escribe).*(?:script|controlador|controller|manager)", "Game Script Implementation"),
]

ENGLISH_TOPIC_MAP = [
    (r"(?:help\s+(?:me\s+)?(?:understand|learn))\s+python", "Help with Python Learning"),
    (r"(?:help\s+(?:me\s+)?(?:understand|learn))\s+c#", "Help with C# Learning"),
    (r"(?:help\s+(?:me\s+)?(?:understand|learn))\s+unity", "Unity Engine Guide"),
    (r"(?:what\s+would\s+be\s+the\s+best\s+model|which\s+model\s+is\s+best).*(?:music|sfx|audio)", "Game Music & SFX Model Selection"),
    (r"(?:what\s+would\s+be\s+the\s+best\s+model|which\s+model\s+is\s+best)", "Best AI Model Selection"),
    (r"(?:run|execute)\s+(?:the\s+)?tests", "Project Unit Tests"),
    (r"(?:create|write|add).*(?:script|controller|manager)", "Game Script Implementation"),
]


def generate_smart_session_title(prompt: str) -> str:
    """
    Generates a concise, professional Title Case title for the conversation based on the user's prompt.
    Transforms raw queries into clean titles (e.g. 'ayudame a entender python' -> 'Help with Python Learning').
    """
    raw = (prompt or "").strip()
    if not raw:
        return "New Engineering Session"

    # Match against known common technical patterns
    for pattern, title in SPANISH_TOPIC_MAP:
        if re.search(pattern, raw, re.IGNORECASE):
            return title

    for pattern, title in ENGLISH_TOPIC_MAP:
        if re.search(pattern, raw, re.IGNORECASE):
            return title

    # Fallback heuristic: clean out punctuation, prefixes, and format cleanly
    first_line = raw.splitlines()[0].strip()
    cleaned = re.sub(r"^[¿\?¡\!#\-\*\s]+", "", first_line)
    cleaned = re.sub(r"^(?:por favor|can you please|could you|ayudame a|ayuda con|dime|quiero)\s+", "", cleaned, flags=re.IGNORECASE)

    words = cleaned.split()
    if len(words) > 6:
        candidate = " ".join(words[:6])
    else:
        candidate = " ".join(words)

    # Capitalize words cleanly
    candidate = " ".join(w.capitalize() if len(w) > 2 else w.lower() for w in candidate.split())
    if len(candidate) > 42:
        candidate = candidate[:40].rstrip()

    return candidate or "Engineering Session"


# ==============================================================================
# 2. PROMPT INTENT & TOKEN CONSERVATION
# ==============================================================================

ADVISORY_PATTERNS = (
    "what would be the best model",
    "which model",
    "best model",
    "what model",
    "que modelo",
    "qué modelo",
    "cual es el mejor",
    "cuál es el mejor",
    "recomiendas",
    "recommend",
    "ayudame a entender",
    "help me understand",
    "how does",
    "what is ",
    "que es ",
    "qué es ",
    "difference between",
    "diferencia entre",
    "500mil tokens",
    "cuanto cuesta",
    "how much",
)

EXPLICIT_WORKSPACE_KEYWORDS = (
    "assets/",
    "scripts/",
    "matchcontroller",
    "musicmanager",
    "hudview",
    "boardview",
    "gamejam",
    "godboard",
    "csproj",
    "corre los tests",
    "run tests",
    "crea un script",
    "write a script",
    "modifica el archivo",
    "refactor",
    "implementa",
    "arregla el bug",
    "fix the bug",
    "en mi folder",
    "en mi unity",
    "en mi proyecto",
)


def prompt_needs_workspace_injection(prompt: str) -> bool:
    """
    Returns True ONLY if the prompt explicitly requires inspecting or editing local workspace code.
    Purely advisory, conceptual, or model comparison queries return False, conserving 10k-50k tokens.
    """
    q = (prompt or "").lower()
    if not q:
        return False

    # If the user explicitly asks an advisory/model question without asking for script creation
    if any(pat in q for pat in ADVISORY_PATTERNS) and not any(kw in q for kw in ("crea", "escribe", "write", "implement", "modify")):
        return False

    return any(kw in q for kw in EXPLICIT_WORKSPACE_KEYWORDS)


# ==============================================================================
# 3. AUTONOMOUS CODE EXTRACTION & DISK APPLICATOR
# ==============================================================================

# Regex to detect code blocks with explicit target filepaths
# Matches:
# ```csharp // File: Assets/_Project/Scripts/Audio/MusicManager.cs ... ```
# ```csharp filepath="Assets/..." ... ```
# // File: Assets/... inside a code block
CODE_BLOCK_PATTERN = re.compile(
    r"```(?:[a-zA-Z0-9_\+#\-]+)?(?:\s+(?:filepath=|file=)?[\"']?([a-zA-Z0-9_\./\\-]+)[\"']?)?\n(.*?)```",
    re.DOTALL,
)

INLINE_FILE_HEADER_PATTERN = re.compile(
    r"^(?://|#|/\*|<!--)\s*(?:File|Path|Target|Archivo):\s*([a-zA-Z0-9_\./\\-]+)",
    re.IGNORECASE | re.MULTILINE,
)


def extract_files_from_markdown(content: str) -> List[Tuple[str, str]]:
    """
    Extracts all files and code bodies that have a designated file path target.
    Returns list of (relative_path, file_content).
    """
    results: List[Tuple[str, str]] = []

    # 1. Search markdown code blocks
    for match in CODE_BLOCK_PATTERN.finditer(content):
        header_attr_path = match.group(1)
        block_body = match.group(2)

        target_path: Optional[str] = None
        if header_attr_path:
            target_path = header_attr_path.strip().strip("\"'")
        else:
            # Check the first 3 lines of block body for // File: <relpath>
            header_match = INLINE_FILE_HEADER_PATTERN.search(block_body[:300])
            if header_match:
                target_path = header_match.group(1).strip()

        if target_path and block_body.strip():
            # Clean leading/trailing quotes or brackets
            clean_path = target_path.strip("`'\"[]")
            if any(clean_path.endswith(ext) for ext in (".cs", ".py", ".ts", ".tsx", ".js", ".json", ".md", ".shader", ".uss", ".uxml", ".sh")):
                results.append((clean_path, block_body))

    return results


def apply_autonomous_files(folder_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Parses the generated response for file blocks and writes them directly to the active workspace on disk.
    Returns a list of executed actions.
    """
    if not folder_path or not os.path.isdir(folder_path):
        return []

    extracted = extract_files_from_markdown(content)
    actions: List[Dict[str, Any]] = []

    for rel_path, code in extracted:
        try:
            write_res = write_workspace_file(folder_path=folder_path, relative_path=rel_path, content=code)
            actions.append({
                "type": "file_written",
                "path": write_res["relative_path"],
                "full_path": write_res["full_path"],
                "bytes": write_res["bytes_written"],
                "status": "created" if not os.path.exists(write_res["full_path"]) else "modified",
                "details": f"Auto-applied {write_res['relative_path']} ({write_res['bytes_written']:,} bytes)",
            })
        except Exception as exc:
            actions.append({
                "type": "file_error",
                "path": rel_path,
                "status": "failed",
                "details": str(exc),
            })

    return actions


# ==============================================================================
# 4. AUTOMATED TEST RUNNER
# ==============================================================================

def run_automated_workspace_tests(folder_path: str) -> Optional[Dict[str, Any]]:
    """
    Executes automated test suite in the workspace if supported test runners exist.
    Supports .NET / Unity (dotnet test) and Python (pytest).
    """
    if not folder_path or not os.path.isdir(folder_path):
        return None

    p = Path(folder_path)

    # Check for .NET / Unity test project (e.g. GameJam.Tests.csproj)
    test_csproj = None
    for f in p.glob("*.csproj"):
        if "test" in f.name.lower():
            test_csproj = f.name
            break

    if test_csproj:
        try:
            cmd = ["dotnet", "test", test_csproj, "--no-restore", "-v", "quiet"]
            res = subprocess.run(
                cmd,
                cwd=folder_path,
                capture_output=True,
                text=True,
                timeout=12,
            )
            stdout = res.stdout or ""
            stderr = res.stderr or ""
            full_out = (stdout + "\n" + stderr).strip()

            passed = res.returncode == 0
            summary = "Tests passed successfully" if passed else "Test suite completed"
            match = re.search(r"Passed:\s*(\d+).*Failed:\s*(\d+)", full_out, re.IGNORECASE)
            if match:
                summary = f"Passed: {match.group(1)}, Failed: {match.group(2)}"

            return {
                "runner": f"dotnet test {test_csproj}",
                "passed": passed,
                "summary": summary,
                "output": full_out[:800],
            }
        except subprocess.TimeoutExpired:
            return {
                "runner": "dotnet test",
                "passed": False,
                "summary": "Test execution timed out after 12s",
                "output": "",
            }
        except FileNotFoundError:
            # dotnet CLI not available in PATH
            return None
        except Exception as exc:
            return {
                "runner": "dotnet test",
                "passed": False,
                "summary": f"Error running tests: {exc}",
                "output": "",
            }

    # Check for Python pytest
    if (p / "tests").is_dir() or any(p.glob("test_*.py")):
        try:
            cmd = ["pytest", "-q"]
            res = subprocess.run(cmd, cwd=folder_path, capture_output=True, text=True, timeout=10)
            passed = res.returncode == 0
            return {
                "runner": "pytest",
                "passed": passed,
                "summary": res.stdout.strip().splitlines()[-1] if res.stdout else "Passed",
                "output": res.stdout[:500],
            }
        except Exception:
            return None

    return None
