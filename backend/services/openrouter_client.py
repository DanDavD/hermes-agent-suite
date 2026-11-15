"""OpenRouter API client, telemetry fetcher, and workflow dispatcher."""

import asyncio
import base64
import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI, OpenAI

from backend.config import (
    OPENROUTER_AUTH_KEY_URL,
    OPENROUTER_BASE_URL,
    OPENROUTER_CREDITS_URL,
    RAW_MODELS,
    get_mode_badge,
    resolve_mode,
    runtime_settings,
)
from backend.services.workspace_scanner import estimate_tokens_from_text

DEFAULT_HEADERS = {
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "Hermes Studio v2",
}


def get_api_key(override_key: Optional[str] = None) -> str:
    """Resolves the active OpenRouter API key or raises a descriptive ValueError."""
    key = (override_key or runtime_settings.get_api_key() or "").strip()
    if not key or key == "your_openrouter_api_key_here":
        raise ValueError(
            "OpenRouter API key is missing or unconfigured. "
            "Please set OPENROUTER_API_KEY in .env or update it via Settings in the UI."
        )
    return key


def get_sync_client(api_key: Optional[str] = None) -> OpenAI:
    """Returns a synchronous OpenAI client pointed at OpenRouter."""
    key = get_api_key(api_key)
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
        default_headers=DEFAULT_HEADERS,
    )


def get_async_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    """Returns an asynchronous AsyncOpenAI client pointed at OpenRouter."""
    key = get_api_key(api_key)
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
        default_headers=DEFAULT_HEADERS,
    )


def format_attachments_block(attachments: Optional[List[Any]]) -> str:
    """Formats attached files (plain text or base64 encoded text) into XML context blocks."""
    if not attachments:
        return ""

    blocks: List[str] = []
    for item in attachments:
        if isinstance(item, dict):
            fname = item.get("filename") or item.get("name") or "attachment.txt"
            raw_content = item.get("content") or item.get("text") or ""
            ctype = item.get("content_type") or "text/plain"
        else:
            fname = getattr(item, "filename", "attachment.txt")
            raw_content = getattr(item, "content", "")
            ctype = getattr(item, "content_type", "text/plain")

        if not raw_content:
            continue

        decoded_text = raw_content
        # Handle data URL or base64-encoded text attachments if applicable
        if raw_content.startswith("data:") and ";base64," in raw_content:
            b64_part = raw_content.split(";base64,", 1)[1]
            try:
                decoded_text = base64.b64decode(b64_part).decode("utf-8", errors="replace")
            except Exception:
                decoded_text = f"[Binary attachment: {fname} ({ctype})]"

        blocks.append(
            f"<attached_file filename=\"{fname}\" content_type=\"{ctype}\">\n"
            f"{decoded_text}\n"
            f"</attached_file>"
        )

    if not blocks:
        return ""
    return "\n\n### Attached Files\n" + "\n\n".join(blocks)


# Remap retired OpenRouter slugs and provide automatic fallback chain
MODEL_REMAP = {
    "nousresearch/hermes-3-llama-3.1-70b": "nousresearch/hermes-4-70b",
    "nousresearch/hermes-3-llama-3.1-8b": "nousresearch/deephermes-3-llama-3-8b-preview",
}

FALLBACK_MODELS = [
    "nousresearch/hermes-4-70b",
    "nousresearch/hermes-3-llama-3.1-405b",
    "qwen/qwen-2.5-coder-32b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
]


_HISTORY_CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+#-]*)\n([\s\S]*?)```")
_HISTORY_FILE_HEADER_RE = re.compile(
    r"^(?://|#|/\*|<!--|--)\s*(?:File|Path|Target|Archivo|Filename):\s*([^\s*]+)",
    re.IGNORECASE | re.MULTILINE,
)


def _compact_history_content(role: str, content: str) -> str:
    """
    Compacts large code blocks in prior conversation turns so follow-up messages
    do not re-send thousands of tokens of code that was already written to disk.
    """
    if not content or role != "assistant":
        return content

    def _replace_block(match: re.Match) -> str:
        lang = match.group(1) or "code"
        body = match.group(2) or ""
        lines = body.splitlines()
        if len(lines) <= 18 and len(body) <= 700:
            return match.group(0)
        f_match = _HISTORY_FILE_HEADER_RE.search("\n".join(lines[:4]))
        if f_match:
            target_file = f_match.group(1).strip()
            return f"`[Autonomous Disk Write: {target_file} ({len(lines)} lines applied to workspace)]`"
        return f"`[Code block ({lang}, {len(lines)} lines) omitted from history for token efficiency]`"

    compacted = _HISTORY_CODE_BLOCK_RE.sub(_replace_block, content)
    if len(compacted) > 2800:
        compacted = compacted[:2800] + "\n...[prior response summarized for token conservation]..."
    return compacted


async def acall_llm(
    model: str,
    system_prompt: str,
    user_prompt: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Executes an async chat completion against OpenRouter with automatic model fallback
    if a specific provider/model slug returns 404 or is temporarily unavailable.
    """
    client = get_async_client(api_key)
    temp = temperature if temperature is not None else runtime_settings.temperature
    max_tok = max_tokens if max_tokens is not None else runtime_settings.max_tokens

    primary_model = MODEL_REMAP.get(model, model)
    candidate_models = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    # Guard against 32,768-token context overflow on specialist endpoints (e.g., Qwen 2.5 Coder 32B)
    MAX_SAFE_PROMPT_CHARS = 72000  # ~18,000 tokens
    safe_user_prompt = user_prompt
    if len(safe_user_prompt) > MAX_SAFE_PROMPT_CHARS:
        safe_user_prompt = (
            safe_user_prompt[:MAX_SAFE_PROMPT_CHARS]
            + "\n\n[... Context truncated automatically to fit model 32k context window ...]"
        )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        # Keep only recent turns, compact old code dumps, and cap total history characters to ~2,200 tokens
        history_chars = 0
        trimmed_history: List[Dict[str, str]] = []
        for msg in reversed(conversation_history[-6:]):
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            if role in ("user", "assistant") and raw_content:
                content = _compact_history_content(role, raw_content)
                if history_chars + len(content) > 9000:
                    break
                trimmed_history.append({"role": role, "content": content})
                history_chars += len(content)
        messages.extend(reversed(trimmed_history))

    messages.append({"role": "user", "content": safe_user_prompt})

    # Ensure reasoning models (Gemini 2.5 Pro/Flash, DeepSeek R1) have sufficient token headroom
    # so internal thinking tokens never truncate multi-file code output mid-stream
    if any(rm in primary_model for rm in ("gemini-2.5", "deepseek-r1")) and max_tok < 8192:
        max_tok = 8192

    # Ensure max_tok leaves ample room within 32,768 context limit
    estimated_input_tok = sum(estimate_tokens_from_text(m["content"]) for m in messages)
    if estimated_input_tok + max_tok > 28000:
        max_tok = max(1024, min(max_tok, 28000 - estimated_input_tok))

    last_err: Optional[Exception] = None
    response = None
    for candidate in candidate_models:
        try:
            response = await client.chat.completions.create(
                model=candidate,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            )
            break
        except Exception as err:
            last_err = err
            err_str = str(err).lower()
            # If context length exceeded (400), compress user prompt further and retry immediately
            if "maximum context length" in err_str or "context length" in err_str or "400" in err_str:
                try:
                    compressed_prompt = safe_user_prompt[:32000] + "\n\n[... Context compressed ...]"
                    compressed_msgs = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": compressed_prompt},
                    ]
                    response = await client.chat.completions.create(
                        model=candidate,
                        messages=compressed_msgs,
                        temperature=temp,
                        max_tokens=min(max_tok, 2048),
                    )
                    break
                except Exception as retry_err:
                    last_err = retry_err
                    continue
            # Retry next candidate if model is 404 / no provider / unavailable
            if "404" in err_str or "no provider" in err_str or "no longer available" in err_str or "503" in err_str:
                continue
            raise

    if response is None:
        raise last_err or RuntimeError("All candidate models failed on OpenRouter.")

    content_out = (response.choices[0].message.content or "") if response.choices else ""
    tokens_used = 0
    if getattr(response, "usage", None) and getattr(response.usage, "total_tokens", None):
        tokens_used = int(response.usage.total_tokens)
    else:
        prompt_text = system_prompt + user_prompt + "".join(m.get("content", "") for m in (conversation_history or []))
        tokens_used = estimate_tokens_from_text(prompt_text) + estimate_tokens_from_text(content_out)

    return content_out, tokens_used


async def run_raw_model_workflow(
    mode: str,
    prompt: str,
    workspace_context: str = "",
    attachments_block: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calls a raw model (Hermes 70B, Hermes 8B, Qwen Coder 32B, or Claude 3.5 Sonnet)
    with full conversation history, active workspace context, and file attachments.
    """
    resolved_mode = resolve_mode(mode)
    model_id = RAW_MODELS.get(resolved_mode, RAW_MODELS["raw:hermes-70b"])
    badge = get_mode_badge(resolved_mode)

    system_prompt = (
        "You are an elite Autonomous Principal Software & Game Engineer inside Hermes Studio v2.\n"
        "You have direct write access to the user's local project workspace on disk.\n\n"
        "### MANDATORY AUTONOMOUS DISK EDITING & ZERO-WASTE TOKEN POLICY:\n"
        "The Hermes Studio engine intercepts your directive code blocks, applies the changes directly to the local disk (visible immediately in GitHub Desktop), and AUTOMATICALLY HIDES the code blocks from the chat UI so the user only sees your brief summary and the `N file(s) changed` bar.\n"
        "To save tokens and guarantee 100% completion across all requested files, ALWAYS use the most compact directive:\n"
        "1. APPENDING TO AN EXISTING FILE (comments, new methods/exports at EOF) — USE `// Append: <path>`:\n"
        "   Output ONLY the directive header and the new line(s) to append. NEVER rewrite the rest of the file!\n"
        "   You can even batch multiple files inside a single code block:\n"
        "   ```csharp\n"
        "   // Append: Assets/_Project/Scripts/Core/AssemblyInfo.cs\n"
        "   // 67\n"
        "   // Append: Assets/_Project/Scripts/Core/CombatReason.cs\n"
        "   // 67\n"
        "   // Append: README.md\n"
        "   <!-- 67 -->\n"
        "   ```\n"
        "2. PREPENDING TO THE TOP OF A FILE — USE `// Prepend: <path>`:\n"
        "   Output ONLY `// Prepend: <relative_path>` followed by the lines to insert at the top.\n"
        "3. MODIFYING SPECIFIC LINES IN ANY EXISTING FILE — USE `// File: <path>` + `SEARCH/REPLACE`:\n"
        "   Regardless of file size, NEVER rewrite unchanged lines of an existing file. Output only the targeted diff:\n"
        "   ```javascript\n"
        "   // File: js/store.js\n"
        "   <<<<<<< SEARCH\n"
        "   exact existing lines\n"
        "   =======\n"
        "   updated replacement lines\n"
        "   >>>>>>> REPLACE\n"
        "   ```\n"
        "4. CREATING A BRAND-NEW FILE — USE `// File: <path>`:\n"
        "   Output the complete file with `// File: <relative_path>` (or `# File:` / `<!-- File: -->`) on line 1.\n"
        "5. DELETING A FILE — USE `// Delete: <relative_path>`.\n"
        "6. MULTI-FILE COMPLETENESS GUARANTEE:\n"
        "   If the user asks to edit N files (e.g., 10 files), you MUST emit a directive (`// Append:`, `// Prepend:`, or `// File:`) for ALL N files using valid paths from `<workspace_summary>`—never claim you edited a file without emitting its directive!\n"
        "7. CONCISE TEXT SUMMARY:\n"
        "   Keep your visible text message short and direct (state that the changes were applied to disk and list the modified files briefly). Never print 'Before:' code snippets.\n\n"
        "### STRICT AUTONOMY & ZERO-MANUAL-CHORES POLICY:\n"
        "- NEVER tell the user to manually copy-paste code or manually create GameObjects in Unity.\n"
        "- Respect existing project architecture, variable names, and namespaces."
    )
    if workspace_context:
        system_prompt += (
            "\n\n### Active Local Workspace Context\n"
            "The user has linked a local project directory. Use these indexed files for accurate imports, "
            "namespaces, and architectural consistency:\n\n"
            f"{workspace_context}"
        )

    full_user_prompt = prompt
    if attachments_block:
        full_user_prompt += f"\n\n{attachments_block}"

    output, tokens_used = await acall_llm(
        model=model_id,
        system_prompt=system_prompt,
        user_prompt=full_user_prompt,
        conversation_history=conversation_history,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    step = {
        "step": 1,
        "agent": badge,
        "model": model_id,
        "status": "Complete",
        "output": output,
        "tokens_used": tokens_used,
    }

    return {
        "response": output,
        "agent_badge": badge,
        "agent_steps": [step],
        "tokens_used": tokens_used,
    }


def _http_get_json(url: str, headers: Dict[str, str], timeout: float = 8.0) -> Tuple[int, Dict[str, Any]]:
    """Synchronous helper to GET a JSON endpoint using standard library urllib."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            return status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:
        return 0, {}


async def fetch_openrouter_telemetry() -> Dict[str, Any]:
    """
    Queries OpenRouter `/api/v1/auth/key` and `/api/v1/credits` using the active API key
    to return live credit balance, total usage, rate limits, and key validity.
    """
    key = runtime_settings.get_api_key()
    if not key:
        return {
            "api_key_configured": False,
            "api_key_masked": "",
            "key_status": "unconfigured",
            "label": None,
            "usage_usd": 0.0,
            "limit_usd": None,
            "remaining_usd": None,
            "total_credits_usd": None,
            "total_usage_usd": None,
            "is_free_tier": False,
            "rate_limit": None,
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Hermes Studio v2",
        "Accept": "application/json",
    }

    key_status = "active"
    label: Optional[str] = None
    usage_usd: float = 0.0
    limit_usd: Optional[float] = None
    remaining_usd: Optional[float] = None
    total_credits_usd: Optional[float] = None
    total_usage_usd: Optional[float] = None
    is_free_tier: bool = False
    rate_limit: Optional[Dict[str, Any]] = None

    # 1. Query /api/v1/auth/key
    auth_status, auth_json = await asyncio.to_thread(
        _http_get_json, OPENROUTER_AUTH_KEY_URL, headers, 8.0
    )
    if auth_status == 200:
        payload = auth_json.get("data", {})
        label = payload.get("label")
        usage_usd = float(payload.get("usage") or 0.0)
        if payload.get("limit") is not None:
            limit_usd = float(payload["limit"])
        if payload.get("limit_remaining") is not None:
            remaining_usd = float(payload["limit_remaining"])
        elif limit_usd is not None:
            remaining_usd = max(0.0, limit_usd - usage_usd)
        is_free_tier = bool(payload.get("is_free_tier", False))
        rate_limit = payload.get("rate_limit")
    elif auth_status in (401, 403):
        key_status = "invalid"
    elif auth_status == 0:
        key_status = "error"
    else:
        key_status = f"http_{auth_status}"

    # 2. Query /api/v1/credits for account-wide total credits & usage
    if key_status == "active":
        cred_status, cred_json = await asyncio.to_thread(
            _http_get_json, OPENROUTER_CREDITS_URL, headers, 8.0
        )
        if cred_status == 200:
            cred_data = cred_json.get("data", {})
            if cred_data.get("total_credits") is not None:
                total_credits_usd = float(cred_data["total_credits"])
            if cred_data.get("total_usage") is not None:
                total_usage_usd = float(cred_data["total_usage"])
                if usage_usd == 0.0:
                    usage_usd = total_usage_usd
            if total_credits_usd is not None and total_usage_usd is not None:
                remaining_usd = round(max(0.0, total_credits_usd - total_usage_usd), 4)

    return {
        "api_key_configured": True,
        "api_key_masked": runtime_settings.get_masked_key(),
        "key_status": key_status,
        "label": label,
        "usage_usd": round(usage_usd, 4),
        "limit_usd": round(limit_usd, 4) if limit_usd is not None else None,
        "remaining_usd": round(remaining_usd, 4) if remaining_usd is not None else None,
        "total_credits_usd": round(total_credits_usd, 4) if total_credits_usd is not None else None,
        "total_usage_usd": round(total_usage_usd, 4) if total_usage_usd is not None else None,
        "is_free_tier": is_free_tier,
        "rate_limit": rate_limit,
    }
