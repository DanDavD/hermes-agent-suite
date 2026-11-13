"""Chat & Multi-Agent Execution Router (/api/chat and /api/chat/stream)."""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import get_mode_badge, resolve_mode
from backend.database import (
    add_message,
    create_session,
    get_session,
    update_session,
)
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.autonomous_executor import (
    apply_autonomous_files,
    generate_smart_session_title,
    prompt_needs_workspace_injection,
    run_automated_workspace_tests,
)
from backend.services.openrouter_client import format_attachments_block
from backend.services.workflows import dispatch_workflow
from backend.services.workspace_scanner import build_workspace_context

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _prepare_session_and_context(payload: ChatRequest) -> Dict[str, Any]:
    """
    Ensures session exists in SQLite, extracts conversation history,
    builds workspace context (only if prompt requires it), and saves the incoming user message.
    """
    resolved_mode = resolve_mode(payload.mode)
    session = get_session(payload.session_id) if payload.session_id else None
    smart_title = generate_smart_session_title(payload.prompt)

    if not session:
        session = create_session(
            title=smart_title,
            mode=resolved_mode,
            workspace_path=payload.workspace_path or "",
            project_id=payload.project_id or "",
            session_id=payload.session_id,
        )
    else:
        # Auto-update title if it was a default placeholder, truncated slice, or turn 1
        curr_title = session.get("title", "")
        new_title = None
        is_generic_title = (
            curr_title in ("New Session", "Untitled Session", "New Engineering Session", "New Chat", "Engineering Session")
            or curr_title.endswith("...")
            or len(session.get("messages", [])) <= 1
        )
        if is_generic_title and payload.prompt.strip():
            new_title = smart_title

        new_ws = (
            payload.workspace_path
            if payload.workspace_path is not None and payload.workspace_path != ""
            else session.get("workspace_path", "")
        )
        new_pid = (
            payload.project_id
            if payload.project_id is not None and payload.project_id != ""
            else session.get("project_id", "")
        )
        session = update_session(
            session_id=session["id"],
            title=new_title,
            mode=resolved_mode,
            workspace_path=new_ws,
            project_id=new_pid,
        ) or session

    session_id = session["id"]
    active_workspace = (
        payload.workspace_path
        if payload.workspace_path is not None and payload.workspace_path != ""
        else session.get("workspace_path", "")
    )

    # Extract prior conversation history (capped to last 12 turns)
    prior_messages: List[Dict[str, str]] = []
    for msg in session.get("messages", [])[-12:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            prior_messages.append({"role": msg["role"], "content": msg["content"]})

    # DYNAMIC TOKEN CONSERVATION:
    # Only scan and inject local workspace files if the user's prompt actually requires code context!
    workspace_context = ""
    injected_files: List[str] = []
    injected_tokens = 0
    if active_workspace and active_workspace.strip() and prompt_needs_workspace_injection(payload.prompt):
        workspace_context, injected_files, injected_tokens = build_workspace_context(
            folder_path=active_workspace,
            selected_files=payload.selected_files,
            user_prompt=payload.prompt,
        )

    # Format attachments metadata for storage and XML block for prompt injection
    raw_attachments = [a.model_dump() for a in (payload.attachments or [])]
    attachments_meta = [
        {
            "filename": a["filename"],
            "content_type": a.get("content_type", "text/plain"),
            "size": a.get("size") or len(a.get("content", "")),
        }
        for a in raw_attachments
    ]
    attachments_block = format_attachments_block(raw_attachments)

    # Save user message to SQLite
    user_msg = add_message(
        session_id=session_id,
        role="user",
        content=payload.prompt,
        agent_badge="User",
        attachments=attachments_meta,
        tokens_used=0,
    )

    return {
        "session_id": session_id,
        "session_title": session.get("title") or smart_title,
        "active_workspace": active_workspace,
        "resolved_mode": resolved_mode,
        "prior_messages": prior_messages,
        "workspace_context": workspace_context,
        "injected_files": injected_files,
        "injected_tokens": injected_tokens,
        "attachments_block": attachments_block,
        "user_msg": user_msg,
    }


def _execute_autonomous_post_processing(
    active_workspace: str,
    prompt: str,
    assistant_content: str,
) -> List[Dict[str, Any]]:
    """
    Scans the assistant output for file blocks, writes them safely to disk,
    and runs test suites if requested or if code was modified.
    """
    actions_executed: List[Dict[str, Any]] = []
    if not active_workspace:
        return actions_executed

    # 1. Autonomous file disk writes
    file_actions = apply_autonomous_files(active_workspace, assistant_content)
    actions_executed.extend(file_actions)

    # 2. Automated test execution
    q = (prompt or "").lower()
    test_keywords = ("test", "tests", "corre", "run", "ejecuta", "verifica")
    should_test = any(kw in q for kw in test_keywords) or bool(file_actions)

    if should_test:
        test_res = run_automated_workspace_tests(active_workspace)
        if test_res:
            actions_executed.append({
                "type": "test_run",
                "runner": test_res["runner"],
                "status": "passed" if test_res["passed"] else "failed",
                "summary": test_res["summary"],
                "details": f"{test_res['runner']}: {test_res['summary']}",
            })

    return actions_executed


@router.post("", response_model=ChatResponse)
async def execute_chat(payload: ChatRequest) -> Any:
    """
    Executes the selected agent squad or raw model with active workspace context
    and file attachments, persists messages to SQLite, auto-writes files, and returns the result.
    """
    if not payload.prompt or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    if payload.stream:
        return await stream_chat(payload)

    prep = _prepare_session_and_context(payload)
    session_id = prep["session_id"]
    resolved_mode = prep["resolved_mode"]

    try:
        result = await dispatch_workflow(
            mode=resolved_mode,
            prompt=payload.prompt,
            workspace_context=prep["workspace_context"],
            attachments_block=prep["attachments_block"],
            conversation_history=prep["prior_messages"],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            sub_mode=payload.sub_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter / Workflow execution error: {exc}",
        ) from exc

    assistant_content = result["response"]
    agent_badge = result.get("agent_badge") or get_mode_badge(resolved_mode)
    agent_steps = result.get("agent_steps", [])
    tokens_used = int(result.get("tokens_used", 0))

    # Autonomous execution: direct disk writing & automated test runner
    actions_executed = _execute_autonomous_post_processing(
        active_workspace=prep["active_workspace"],
        prompt=payload.prompt,
        assistant_content=assistant_content,
    )

    assistant_msg = add_message(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        agent_badge=agent_badge,
        attachments=[],
        tokens_used=tokens_used,
        agent_steps=agent_steps,
    )

    return {
        "session_id": session_id,
        "session_title": prep["session_title"],
        "project_id": payload.project_id or "",
        "mode": resolved_mode,
        "agent_badge": agent_badge,
        "response": assistant_content,
        "content": assistant_content,
        "user_message": prep["user_msg"],
        "assistant_message": assistant_msg,
        "agent_steps": agent_steps,
        "actions_executed": actions_executed,
        "tokens_used": tokens_used,
        "workspace_files_injected": prep["injected_files"],
        "workspace_tokens_injected": prep["injected_tokens"],
    }


@router.post("/stream")
async def stream_chat(payload: ChatRequest) -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint that streams real-time multi-agent step progress,
    executes autonomous file writes, and delivers final completion payload.
    """
    if not payload.prompt or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    prep = _prepare_session_and_context(payload)
    session_id = prep["session_id"]
    resolved_mode = prep["resolved_mode"]

    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    async def on_step_callback(step_data: Dict[str, Any]) -> None:
        await queue.put({"type": "step", "data": step_data})

    async def run_pipeline() -> None:
        try:
            result = await dispatch_workflow(
                mode=resolved_mode,
                prompt=payload.prompt,
                workspace_context=prep["workspace_context"],
                attachments_block=prep["attachments_block"],
                conversation_history=prep["prior_messages"],
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
                sub_mode=payload.sub_mode,
                on_step=on_step_callback,
            )
            assistant_content = result["response"]
            agent_badge = result.get("agent_badge") or get_mode_badge(resolved_mode)
            agent_steps = result.get("agent_steps", [])
            tokens_used = int(result.get("tokens_used", 0))

            # Autonomous execution: direct disk writing & automated test runner
            actions_executed = _execute_autonomous_post_processing(
                active_workspace=prep["active_workspace"],
                prompt=payload.prompt,
                assistant_content=assistant_content,
            )

            assistant_msg = add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                agent_badge=agent_badge,
                attachments=[],
                tokens_used=tokens_used,
                agent_steps=agent_steps,
            )

            final_payload = {
                "session_id": session_id,
                "session_title": prep["session_title"],
                "project_id": payload.project_id or "",
                "mode": resolved_mode,
                "agent_badge": agent_badge,
                "response": assistant_content,
                "content": assistant_content,
                "user_message": prep["user_msg"],
                "assistant_message": assistant_msg,
                "agent_steps": agent_steps,
                "actions_executed": actions_executed,
                "tokens_used": tokens_used,
                "workspace_files_injected": prep["injected_files"],
                "workspace_tokens_injected": prep["injected_tokens"],
            }
            await queue.put({"type": "complete", "data": final_payload})
        except Exception as exc:
            await queue.put({"type": "error", "data": {"detail": str(exc)}})
        finally:
            await queue.put({"type": "done", "data": {}})

    async def event_generator() -> AsyncGenerator[str, None]:
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                event = await queue.get()
                ev_type = event["type"]
                if ev_type == "done":
                    yield "event: done\ndata: [DONE]\n\n"
                    break
                payload_json = json.dumps(event["data"])
                yield f"event: {ev_type}\ndata: {payload_json}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
