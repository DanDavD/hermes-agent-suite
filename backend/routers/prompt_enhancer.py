"""Prompt Enhancer & Architect Router (/api/prompt-enhancer).
Provides a dedicated $0 (Free Tier) AI prompt engineering assistant that transforms
rough drafts, casual thoughts, and multi-language instructions into elite, structured English prompts.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.openrouter_client import acall_llm

logger = logging.getLogger("hermes.prompt_enhancer")

router = APIRouter(prefix="/api/prompt-enhancer", tags=["prompt-enhancer"])

FREE_PROMPT_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
]

PROMPT_ARCHITECT_SYSTEM = """You are the elite "Prompt Architect" for Hermes Studio.
Your purpose is to act as a world-class prompt engineer who takes rough thoughts, casual instructions, or fragmented ideas (written in Spanish, English, or any language) and transforms them into elite, battle-tested, token-efficient prompts in ENGLISH.

The user will run this prompt inside Hermes Studio's autonomous coding engine, which writes and patches files directly on local disk.

Standards for the Enhanced Prompt:
1. ALWAYS output the enhanced prompt in ENGLISH, regardless of the input language.
2. STRICT ZERO-EMOJI INVARIANT: Do NOT use ANY emojis, pictograms, or decorative icons anywhere in the prompt, headers, summary, explanation, or tips (ABSOLUTELY NO 🎯, 📋, 🛠️, ⚠️, 📤, 🚀, ✨, 🎮, etc.). Use pure, professional engineering text only.
3. Structure the prompt concisely with clean, high-signal Markdown headers:
   - ### Role & Objective: Explicit persona, mission, and clear Definition of Done.
   - ### Technical Context & Stack: Reference only the specific files or stack relevant to the task.
   - ### Step-by-Step Requirements: Logical, atomic implementation steps.
   - ### Constraints & Invariants: Token efficiency, strict typing, error boundaries, and zero placeholders.
   - ### Expected Deliverables & Verification: Instruct the coding agent to apply changes directly to disk using `// File: <relative_path>` headers and surgical `SEARCH/REPLACE` blocks for existing files without outputting redundant "Before" code blocks or asking for manual screenshots.
4. Tone: Concise, highly specific, actionable, direct, and optimized for minimal token usage.

Response Format:
You MUST respond with valid JSON enclosed in ```json ... ```:
{
  "summary": "1-sentence summary of the transformation (NO emojis)",
  "enhanced_prompt": "The complete, pristine, ready-to-run English prompt with pure text markdown headers (NO emojis)...",
  "explanation": "Brief breakdown of why this improved prompt prevents hallucinations and elicits production-grade code (NO emojis)",
  "tips": [
    "Short refinement tip 1 (NO emojis)",
    "Short refinement tip 2 (NO emojis)"
  ]
}
"""

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Removes all emojis and pictograms to guarantee clean engineering text."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*-\s*-\s*", "\n- ", cleaned)
    return cleaned.strip()


class PromptEnhanceMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class PromptEnhanceRequest(BaseModel):
    prompt: str = Field(..., description="Draft prompt or user instruction")
    history: Optional[List[PromptEnhanceMessage]] = Field(default=None, description="Previous mini-chat messages")
    workspace_name: Optional[str] = Field(default=None, description="Active project/workspace name")
    workspace_files: Optional[List[str]] = Field(default=None, description="Sample of relevant files in workspace")
    active_mode: Optional[str] = Field(default=None, description="Currently selected workflow mode in Studio")


class PromptEnhanceResponse(BaseModel):
    summary: str
    enhanced_prompt: str
    explanation: str
    tips: List[str]
    model_used: str
    cost_usd: float = 0.0


@router.post("/chat", response_model=PromptEnhanceResponse)
async def enhance_prompt_chat(payload: PromptEnhanceRequest) -> PromptEnhanceResponse:
    """Transforms a user prompt draft into an optimized English prompt using free models ($0)."""
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt draft cannot be empty.")

    # Build context briefing
    context_parts: List[str] = []
    if payload.workspace_name:
        context_parts.append(f"Active Project: {payload.workspace_name}")
    if payload.active_mode:
        context_parts.append(f"Target Mode: {payload.active_mode}")
    if payload.workspace_files:
        sample_files = payload.workspace_files[:12]
        context_parts.append(f"Relevant Workspace Files: {', '.join(sample_files)}")

    context_str = "\n".join(context_parts) if context_parts else "General Software / Game Development"

    user_query = (
        f"Context from active IDE workspace:\n{context_str}\n\n"
        f"User Draft Prompt to transform:\n\"\"\"\n{payload.prompt.strip()}\n\"\"\""
    )

    # Format history if provided
    formatted_history: List[Dict[str, str]] = []
    if payload.history:
        for msg in payload.history[-6:]:
            formatted_history.append({"role": msg.role, "content": msg.content})

    # Call free model chain
    last_error: Optional[Exception] = None
    for model_candidate in FREE_PROMPT_MODELS:
        try:
            raw_res, _tok = await acall_llm(
                model=model_candidate,
                system_prompt=PROMPT_ARCHITECT_SYSTEM,
                user_prompt=user_query,
                conversation_history=formatted_history,
                temperature=0.3,
                max_tokens=1400,
            )

            # Extract JSON block
            clean_res = raw_res.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```", 1)[1].split("```", 1)[0].strip()

            parsed: Dict[str, Any] = {}
            try:
                parsed = json.loads(clean_res)
            except Exception:
                try:
                    # Fix unquoted keys if returned by certain models: { summary: "..." }
                    quoted_keys = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', clean_res)
                    parsed = json.loads(quoted_keys)
                except Exception:
                    parsed = {}

            if parsed and isinstance(parsed, dict) and "enhanced_prompt" in parsed:
                return PromptEnhanceResponse(
                    summary=strip_emojis(parsed.get("summary", "Prompt enhanced into structured English architecture.")),
                    enhanced_prompt=strip_emojis(parsed.get("enhanced_prompt", clean_res)),
                    explanation=strip_emojis(parsed.get("explanation", "Added explicit constraints, stack context, and output format.")),
                    tips=[strip_emojis(t) for t in parsed.get("tips", ["Actionable English structure", "Clear invariants"]) if strip_emojis(t)],
                    model_used=model_candidate,
                    cost_usd=0.0,
                )

            # Fallback if parsed was empty
            return PromptEnhanceResponse(
                summary="Prompt enhanced into structured English architecture.",
                enhanced_prompt=strip_emojis(clean_res or raw_res),
                explanation="Transformed draft into direct instructions for frontier AI models.",
                tips=["English formulation", "Unambiguous requirements"],
                model_used=model_candidate,
                cost_usd=0.0,
            )
        except Exception as err:
            logger.warning("Free model %s failed for prompt enhancer: %s", model_candidate, err)
            last_error = err
            continue

    raise HTTPException(
        status_code=502,
        detail=f"Prompt Enhancer service unavailable across free models: {last_error}",
    )
