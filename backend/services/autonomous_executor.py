"""Autonomous Tool Execution Service for Hermes Studio v2.

Handles:
1. Dynamic prompt intent classification (token conservation).
2. Autonomous code file extraction and direct disk modification.
3. Automated test runner execution (e.g., dotnet test / pytest) inside the workspace.
4. Smart bilingual session title generation (Spanish/English).
"""

import difflib
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
    Transforms raw queries and Prompt Enhancer templates into clean titles.
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

    # Skip generic Prompt Enhancer markdown headers (e.g. "### Role & Objective:", "**Role & Objective**:")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    meaningful_line = lines[0] if lines else ""
    header_skip_re = re.compile(
        r"^(?:[#\*\-\s🎯📋🛠️⚠️📤]*)(?:role\s*&\s*objective|objective|role|technical\s+context|step-by-step|constraints|expected\s+deliverables|context)\s*:?\s*$",
        re.IGNORECASE,
    )
    inline_header_prefix_re = re.compile(
        r"^(?:[#\*\-\s🎯📋🛠️⚠️📤]*)(?:role\s*&\s*objective|objective|role|task)\s*[\*:\-]+\s*",
        re.IGNORECASE,
    )

    for ln in lines:
        if header_skip_re.match(ln):
            continue
        stripped_ln = inline_header_prefix_re.sub("", ln).strip()
        if stripped_ln:
            meaningful_line = stripped_ln
            break

    # Clean out common AI persona / Prompt Enhancer lead-in boilerplate
    cleaned = re.sub(r"^[¿\?¡\!#\-\*\s🎯📋🛠️⚠️📤]+", "", meaningful_line)
    cleaned = re.sub(
        r"^(?:you\s+are\s+(?:an?\s+)?(?:elite\s+|senior\s+|principal\s+)?[a-zA-Z0-9_/\-\s]+?(?:tasked\s+with|who\s+|to\s+)|"
        r"act\s+as\s+(?:an?\s+)?[a-zA-Z0-9_/\-\s]+?\s+to\s+|"
        r"explicitly\s+(?:define\s+the\s+role\s+as\s+.*?and\s+the\s+objective\s+to\s+|analyze\s+(?:the\s+parts\s+of\s+(?:the\s+)?)?)|"
        r"por\s+favor|can\s+you\s+please|could\s+you|ayudame\s+a|ayuda\s+con|dime|quiero|necesito\s+que)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Take first sentence or clause
    first_clause = re.split(r"[\.\;\n]", cleaned)[0].strip()
    words = (first_clause or cleaned).split()
    if len(words) > 6:
        candidate = " ".join(words[:6])
    else:
        candidate = " ".join(words)

    # Capitalize words cleanly while preserving project identifiers with underscores
    candidate = " ".join(
        w if ("_" in w or any(c.isupper() for c in w[1:])) else (w.capitalize() if len(w) > 2 else w.lower())
        for w in candidate.split()
    )
    if candidate:
        candidate = candidate[0].upper() + candidate[1:]
    if len(candidate) > 46:
        candidate = candidate[:44].rstrip()

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
    "js/",
    "css/",
    "src/",
    "components/",
    ".js",
    ".ts",
    ".tsx",
    ".py",
    ".cs",
    ".html",
    ".css",
    ".vue",
    "index.html",
    "app.js",
    "store.js",
    "matchcontroller",
    "musicmanager",
    "hudview",
    "boardview",
    "gamejam",
    "godboard",
    "mobirent",
    "prototipo",
    "csproj",
    "corre los tests",
    "run tests",
    "crea un script",
    "write a script",
    "modifica",
    "refactor",
    "implement",
    "implementa",
    "arregla",
    "fix",
    "bug",
    "error",
    "en mi folder",
    "en mi unity",
    "en mi proyecto",
    "project",
    "workspace",
    "component",
    "navbar",
    "login",
    "modal",
    "ui",
    "ux",
    "design",
    "style",
    "layout",
    "cambia",
    "change",
    "update",
    "actualiza",
    "apply",
    "aplica",
    "code",
    "codigo",
    "código",
    "archivo",
    "file",
)


def prompt_needs_workspace_injection(prompt: str) -> bool:
    """
    Returns True whenever the user is giving a task or question related to their active project workspace.
    Only returns False for bare greetings ('hola', 'hi') or purely meta questions about AI model pricing/selection,
    ensuring the agent always works directly inside the active project folder.
    """
    q = (prompt or "").strip().lower()
    if not q:
        return False

    # Bare greetings don't need workspace file dumps
    if q in ("hola", "hi", "hello", "hey", "buenas", "buenos dias", "buenas tardes", "gracias", "thanks", "ok"):
        return False

    # If the user explicitly asks an advisory/model pricing question without asking for code changes
    if any(pat in q for pat in ADVISORY_PATTERNS) and not any(
        kw in q for kw in ("crea", "escribe", "write", "implement", "modify", "refactor", "cambia", "fix", "arregla")
    ):
        return False

    return True


# ==============================================================================
# 3. AUTONOMOUS CODE EXTRACTION, SEARCH/REPLACE PATCHING & DISK APPLICATOR
# ==============================================================================

SUPPORTED_AUTONOMOUS_EXTENSIONS = (
    ".cs",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".vue",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".md",
    ".shader",
    ".compute",
    ".hlsl",
    ".cginc",
    ".uss",
    ".uxml",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".sql",
)

CODE_BLOCK_PATTERN = re.compile(
    r"```(?:[a-zA-Z0-9_\+#\-]+)?(?::|\s+)?(?:\s*(?:filepath=|file=)?[\"']?([a-zA-Z0-9_\./\\-]+)[\"']?)?\n(.*?)```",
    re.DOTALL,
)

UNCLOSED_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:[a-zA-Z0-9_\+#\-]+)?(?::|\s+)?(?:\s*(?:filepath=|file=)?[\"']?([a-zA-Z0-9_\./\\-]+)[\"']?)?\n((?:(?!(?:```)).)*)$",
    re.DOTALL,
)

INLINE_DIRECTIVE_PATTERN = re.compile(
    r"^(?://|#|/\*|<!--|--)\s*(File|Path|Target|Archivo|Filename|Append|Append-File|Prepend|Prepend-File):\s*([^\r\n*<>]+?)(?:\s*(?:\*/|-->))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

INLINE_FILE_HEADER_PATTERN = re.compile(
    r"^(?://|#|/\*|<!--|--)\s*(?:File|Path|Target|Archivo|Filename|Append|Append-File|Prepend|Prepend-File):\s*([^\r\n*<>]+?)(?:\s*(?:\*/|-->))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

INLINE_DELETE_HEADER_PATTERN = re.compile(
    r"^(?://|#|/\*|<!--|--)\s*(?:Delete|Delete-File|File-Delete|Remove-File|Eliminar):\s*([^\r\n*<>]+?)(?:\s*(?:\*/|-->))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _compute_line_diff_stats(old_text: str, new_text: str) -> Tuple[int, int]:
    """Computes exact (lines_added, lines_removed) between old_text and new_text."""
    old_lines = old_text.splitlines() if old_text else []
    new_lines = new_text.splitlines() if new_text else []
    if not old_lines:
        return len(new_lines), 0
    if not new_lines:
        return 0, len(old_lines)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "replace":
            removed += i2 - i1
            added += j2 - j1
    return added, removed

PRECEDING_FILE_LABEL_PATTERN = re.compile(
    r"(?:###+|\*\*|File:|Archivo:|Target:)\s*`?([a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\.\-\s]+)+\.[a-zA-Z0-9]+|[a-zA-Z0-9_\-]+\.(?:html|css|js|ts|tsx|py|cs|json|vue|sh|md|shader))`?\s*(?:\*\*)?:?\s*$",
    re.IGNORECASE,
)

BEFORE_LABEL_PATTERN = re.compile(
    r"(?:\*\*Before\s*(?:\([^\)]*\))?\s*:?\*\*|###+\s*Before\b|^Before\s*:)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

SEARCH_REPLACE_PATTERN = re.compile(
    r"<<<<<<<\s*SEARCH[ \t]*\r?\n(.*?)\r?\n=======[ \t]*\r?\n(.*?)\r?\n>>>>>>>\s*REPLACE",
    re.DOTALL,
)


def _strip_file_header_comment(code: str) -> str:
    """
    Removes the synthetic `// File: ...` / `// Append: ...` / `# File: ...` routing header line
    from the top of a code block so it is NEVER written into the user's actual source files on disk.
    """
    lines = code.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and INLINE_FILE_HEADER_PATTERN.match(lines[0].strip()):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    result = "\n".join(lines)
    if code.endswith("\n") and result and not result.endswith("\n"):
        result += "\n"
    return result


def apply_search_replace_blocks(existing_content: str, patch_body: str) -> Optional[str]:
    """
    Applies one or more `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE` blocks to `existing_content`.
    Returns the updated file string if at least one block matched, or None if no blocks matched.
    """
    matches = list(SEARCH_REPLACE_PATTERN.finditer(patch_body))
    if not matches:
        return None

    updated = existing_content
    applied_any = False

    for m in matches:
        search_chunk = m.group(1)
        replace_chunk = m.group(2)

        # 1. Exact substring match
        if search_chunk in updated:
            updated = updated.replace(search_chunk, replace_chunk, 1)
            applied_any = True
            continue

        # 2. CRLF / LF normalized match
        norm_updated = updated.replace("\r\n", "\n")
        norm_search = search_chunk.replace("\r\n", "\n").strip("\n")
        norm_replace = replace_chunk.replace("\r\n", "\n").strip("\n")
        if norm_search and norm_search in norm_updated:
            updated = norm_updated.replace(norm_search, norm_replace, 1)
            applied_any = True
            continue

        # 3. Line-by-line trimmed match fallback (handles indentation drift)
        search_lines = [ln.strip() for ln in norm_search.splitlines() if ln.strip()]
        if search_lines:
            orig_lines = norm_updated.splitlines()
            n_s = len(search_lines)
            for idx in range(len(orig_lines) - n_s + 1):
                window = [orig_lines[idx + k].strip() for k in range(n_s)]
                if window == search_lines:
                    new_lines = orig_lines[:idx] + norm_replace.splitlines() + orig_lines[idx + n_s :]
                    updated = "\n".join(new_lines)
                    if norm_updated.endswith("\n"):
                        updated += "\n"
                    applied_any = True
                    break

    return updated if applied_any else None


def _split_multi_directive_block(block_body: str) -> List[Tuple[str, str, str]]:
    """
    Splits a single code block into multiple (directive_type, target_path, sub_body) tuples
    if the model grouped several `// Append: ...` or `// File: ...` sections inside one code fence.
    """
    matches = list(INLINE_DIRECTIVE_PATTERN.finditer(block_body))
    if not matches:
        return []

    segments: List[Tuple[str, str, str]] = []
    for idx, m in enumerate(matches):
        raw_verb = m.group(1).strip().lower()
        if raw_verb.startswith("append"):
            verb = "append"
        elif raw_verb.startswith("prepend"):
            verb = "prepend"
        else:
            verb = "file"
        target_path = m.group(2).strip().strip("`'\"[]").lstrip("/")
        start_pos = m.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(block_body)
        sub_body = block_body[start_pos:end_pos].rstrip()
        if target_path and any(target_path.lower().endswith(ext) for ext in SUPPORTED_AUTONOMOUS_EXTENSIONS):
            segments.append((verb, target_path, sub_body))
    return segments


def extract_files_from_markdown(content: str) -> List[Tuple[str, str]]:
    """
    Extracts all files and code bodies (or SEARCH/REPLACE / Append / Prepend patches) that have a designated file path target.
    Supports multiple file directives inside a single code block as well as closed code blocks.
    Skips blocks explicitly labeled as 'Before:' comparisons so old code never overwrites refactored code.
    Returns list of (relative_path, file_content_or_patch).
    """
    results: List[Tuple[str, str]] = []

    for match in CODE_BLOCK_PATTERN.finditer(content):
        header_attr_path = match.group(1)
        block_body = match.group(2)

        # Check the immediate preceding markdown heading/label to see if this block is a "Before:" example
        preceding_text = content[max(0, match.start() - 160) : match.start()].strip()
        last_prec_line = preceding_text.splitlines()[-1].strip() if preceding_text else ""
        if BEFORE_LABEL_PATTERN.search(last_prec_line):
            continue

        # Check if block contains one or more explicit inline directives (// File:, // Append:, // Prepend:)
        multi_segments = _split_multi_directive_block(block_body)
        if multi_segments:
            for _verb, clean_path, sub_body in multi_segments:
                if sub_body.strip():
                    results.append((clean_path, sub_body))
            continue

        target_path: Optional[str] = None
        if header_attr_path and "." in header_attr_path:
            target_path = header_attr_path.strip().strip("\"'`")
        else:
            # Check the markdown line immediately preceding the code block
            prec_match = PRECEDING_FILE_LABEL_PATTERN.search(last_prec_line)
            if prec_match:
                target_path = prec_match.group(1).strip()
            else:
                # Auto-inference fallback for Unity C# / C# if model forgot header
                class_match = re.search(
                    r"(?:public\s+|internal\s+)?(?:partial\s+)?(?:class|struct|interface|enum)\s+([A-Za-z0-9_]+)",
                    block_body[:500],
                )
                if class_match:
                    class_name = class_match.group(1)
                    if any(k in block_body for k in ("using UnityEngine", "MonoBehaviour", "ScriptableObject", "UnityEditor")):
                        if "Editor" in class_name or "using UnityEditor" in block_body:
                            target_path = f"Assets/_Project/Editor/{class_name}.cs"
                        else:
                            target_path = f"Assets/Scripts/{class_name}.cs"
                    else:
                        target_path = f"Scripts/{class_name}.cs"

        if target_path and block_body.strip():
            clean_path = target_path.strip("`'\"[]").lstrip("/")
            if any(clean_path.lower().endswith(ext) for ext in SUPPORTED_AUTONOMOUS_EXTENSIONS):
                results.append((clean_path, block_body))

    # Also check if there is an unclosed trailing code block containing complete Append/Prepend or SEARCH/REPLACE blocks
    cleaned_closed = CODE_BLOCK_PATTERN.sub("", content)
    unclosed_match = UNCLOSED_CODE_BLOCK_PATTERN.search(cleaned_closed)
    if unclosed_match:
        unclosed_body = unclosed_match.group(2) or ""
        for verb, clean_path, sub_body in _split_multi_directive_block(unclosed_body):
            if verb in ("append", "prepend") or ("<<<<<<< SEARCH" in sub_body and ">>>>>>> REPLACE" in sub_body):
                results.append((clean_path, sub_body))

    return results


def strip_workspace_code_blocks(content: str) -> str:
    """
    Removes autonomous file/patch code blocks (and any trailing unclosed code block) from the
    visible assistant message so the user only sees the clean explanation text and the
    collapsible `N file(s) changed +X -Y` bar underneath.
    """
    if not content:
        return content

    def _replace_closed_block(match: re.Match) -> str:
        header_attr = match.group(1) or ""
        body = match.group(2) or ""
        first_lines = "\n".join(body.splitlines()[:5])
        if (
            (header_attr and "." in header_attr)
            or INLINE_FILE_HEADER_PATTERN.search(first_lines)
            or INLINE_DELETE_HEADER_PATTERN.search(first_lines)
            or ("<<<<<<< SEARCH" in body and ">>>>>>> REPLACE" in body)
        ):
            return ""
        return match.group(0)

    cleaned = CODE_BLOCK_PATTERN.sub(_replace_closed_block, content)
    # Strip any trailing unclosed code block at the end of the message
    cleaned = re.sub(r"```[a-zA-Z0-9_\+#\-]*\n(?:(?!(?:```))[\s\S])*$", "", cleaned)
    # Also remove standalone `// Delete: ...` lines outside code blocks
    cleaned = INLINE_DELETE_HEADER_PATTERN.sub("", cleaned)
    # Clean up dangling lead-in phrases like "Here are the complete refactored files:" at the end
    cleaned = re.sub(
        r"\n*(?:Here are the (?:complete |updated |refactored |modified )?files:?|Aquí están los archivos(?: modificados| actualizados)?:?)\s*$",
        "",
        cleaned.strip(),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def apply_autonomous_files(folder_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Parses the generated response for file blocks, Append/Prepend directives, or SEARCH/REPLACE patches
    and writes them directly to the active workspace on disk without leaving synthetic header comments.
    Returns a list of executed actions.
    """
    if not folder_path or not os.path.isdir(folder_path):
        return []

    extracted = extract_files_from_markdown(content)
    actions: List[Dict[str, Any]] = []
    base_dir = Path(folder_path).expanduser().resolve()

    for rel_path, code in extracted:
        try:
            target_full = (base_dir / rel_path.lstrip("/")).resolve()
            existed_before = target_full.is_file()
            existing_text = (
                target_full.read_text(encoding="utf-8", errors="replace")
                if existed_before
                else ""
            )

            # Determine directive mode (append, prepend, or file/patch)
            first_line = code.lstrip().splitlines()[0].strip() if code.strip() else ""
            dir_match = INLINE_DIRECTIVE_PATTERN.match(first_line)
            directive_verb = dir_match.group(1).strip().lower() if dir_match else "file"

            clean_body = _strip_file_header_comment(code)

            if directive_verb.startswith("append"):
                # Surgical Append to end of existing file (or create if missing)
                if existed_before and existing_text:
                    sep = "" if existing_text.endswith("\n") else "\n"
                    final_content = f"{existing_text}{sep}\n{clean_body.strip()}\n"
                    action_mode = "patched"
                else:
                    final_content = f"{clean_body.strip()}\n"
                    action_mode = "created"
            elif directive_verb.startswith("prepend"):
                # Surgical Prepend to top of existing file
                if existed_before and existing_text:
                    final_content = f"{clean_body.strip()}\n\n{existing_text}"
                    action_mode = "patched"
                else:
                    final_content = f"{clean_body.strip()}\n"
                    action_mode = "created"
            elif "<<<<<<< SEARCH" in code and ">>>>>>> REPLACE" in code:
                if existed_before:
                    patched_text = apply_search_replace_blocks(existing_text, code)
                    if patched_text is None:
                        actions.append({
                            "type": "file_error",
                            "path": rel_path,
                            "filename": Path(rel_path).name,
                            "status": "failed",
                            "lines_added": 0,
                            "lines_removed": 0,
                            "details": f"SEARCH block did not match existing content in {rel_path}",
                        })
                        continue
                    final_content = patched_text
                    action_mode = "patched"
                else:
                    # File doesn't exist yet; extract the REPLACE side
                    matches = list(SEARCH_REPLACE_PATTERN.finditer(code))
                    final_content = "\n".join(m.group(2) for m in matches) if matches else clean_body
                    action_mode = "created"
            else:
                # Full file write — ALWAYS strip the synthetic `// File: ...` header line on ALL extensions!
                final_content = clean_body
                if existed_before and existing_text.endswith("\n") and not final_content.endswith("\n"):
                    final_content += "\n"
                action_mode = "modified" if existed_before else "created"

            lines_added, lines_removed = _compute_line_diff_stats(existing_text, final_content)

            write_res = write_workspace_file(
                folder_path=folder_path,
                relative_path=rel_path,
                content=final_content,
            )
            actions.append({
                "type": "file_written",
                "path": write_res["relative_path"],
                "filename": Path(write_res["relative_path"]).name,
                "full_path": write_res["full_path"],
                "bytes": write_res["bytes_written"],
                "status": action_mode,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "details": f"Auto-{action_mode} {write_res['relative_path']} (+{lines_added} -{lines_removed})",
            })
        except Exception as exc:
            actions.append({
                "type": "file_error",
                "path": rel_path,
                "filename": Path(rel_path).name,
                "status": "failed",
                "lines_added": 0,
                "lines_removed": 0,
                "details": str(exc),
            })

    # Also support explicit file deletions (`// Delete: path/to/file.js`)
    for del_match in INLINE_DELETE_HEADER_PATTERN.finditer(content):
        del_rel = del_match.group(1).strip().strip("`'\"[]").lstrip("/")
        if not del_rel or ".." in Path(del_rel).parts:
            continue
        try:
            del_full = (base_dir / del_rel).resolve()
            if del_full.is_relative_to(base_dir) and del_full.is_file():
                old_lines_cnt = len(del_full.read_text(encoding="utf-8", errors="replace").splitlines())
                del_full.unlink()
                actions.append({
                    "type": "file_deleted",
                    "path": del_rel,
                    "filename": Path(del_rel).name,
                    "full_path": str(del_full),
                    "bytes": 0,
                    "status": "deleted",
                    "lines_added": 0,
                    "lines_removed": max(1, old_lines_cnt),
                    "details": f"Deleted {del_rel} (-{max(1, old_lines_cnt)} lines)",
                })
        except Exception:
            pass

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
            pass

    # Check for JavaScript syntax verification (node --check) on JS projects without a heavy test runner
    js_files = list(p.glob("js/**/*.js")) or list(p.glob("*.js"))
    if js_files:
        try:
            checked = 0
            failed_files: List[str] = []
            for jf in js_files[:15]:
                res = subprocess.run(
                    ["node", "--check", str(jf)],
                    cwd=folder_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                checked += 1
                if res.returncode != 0:
                    rel_jf = jf.relative_to(p).as_posix()
                    failed_files.append(f"{rel_jf}: {(res.stderr or '').splitlines()[0] if res.stderr else 'SyntaxError'}")
            passed = len(failed_files) == 0
            summary = (
                f"Verified {checked} JS module(s): 0 syntax errors"
                if passed
                else f"Syntax errors in {len(failed_files)} file(s): {'; '.join(failed_files[:2])}"
            )
            return {
                "runner": "node --check",
                "passed": passed,
                "summary": summary,
                "output": "\n".join(failed_files)[:500] if failed_files else summary,
            }
        except Exception:
            return None

    return None
