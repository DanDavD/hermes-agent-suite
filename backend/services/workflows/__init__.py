"""Unified workflow dispatcher for Hermes Studio v2."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.config import resolve_mode
from backend.services.openrouter_client import run_raw_model_workflow
from backend.services.workflows.career_hunter import run_career_hunter_workflow
from backend.services.workflows.content_video import run_content_video_workflow
from backend.services.workflows.dev_squad import run_dev_squad_workflow

StepCallback = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


async def dispatch_workflow(
    mode: str,
    prompt: str,
    workspace_context: str = "",
    attachments_block: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    sub_mode: Optional[str] = None,
    on_step: StepCallback = None,
) -> Dict[str, Any]:
    """Routes a chat request to the selected multi-agent squad or raw model."""
    resolved = resolve_mode(mode)

    if resolved == "team:dev-squad":
        return await run_dev_squad_workflow(
            prompt=prompt,
            workspace_context=workspace_context,
            attachments_block=attachments_block,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
            on_step=on_step,
        )

    if resolved == "team:career-hunter":
        return await run_career_hunter_workflow(
            prompt=prompt,
            workspace_context=workspace_context,
            attachments_block=attachments_block,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
            sub_mode=sub_mode,
            on_step=on_step,
        )

    if resolved == "team:content-video":
        return await run_content_video_workflow(
            prompt=prompt,
            workspace_context=workspace_context,
            attachments_block=attachments_block,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
            on_step=on_step,
        )

    # Otherwise execute raw:* model
    return await run_raw_model_workflow(
        mode=resolved,
        prompt=prompt,
        workspace_context=workspace_context,
        attachments_block=attachments_block,
        conversation_history=conversation_history,
        temperature=temperature,
        max_tokens=max_tokens,
    )
