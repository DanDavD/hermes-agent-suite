"""OpenRouter API client, telemetry fetcher, and workflow dispatcher."""

import asyncio
import base64
import json
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

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

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
        "You are an elite Principal Software & Unity Game Engineer inside Hermes Studio v2.\n"
        "Provide direct, production-ready, deeply technical responses and complete code implementations.\n"
        "When generating source files for the user's workspace, include a comment on the first line of the code block "
        "indicating the relative file path (e.g., `// File: Assets/Scripts/PlayerController.cs` or `# File: scripts/tool.py`) "
        "so the user can one-click Apply it to their workspace."
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
