"""Content & Gameplay Automation Squad (`team:content-video`) workflow."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.config import DEFAULT_ROLE_MODELS, get_mode_badge
from backend.services.openrouter_client import acall_llm

StepCallback = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


async def run_content_video_workflow(
    prompt: str,
    workspace_context: str = "",
    attachments_block: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    on_step: StepCallback = None,
) -> Dict[str, Any]:
    """
    Executes the 3-Agent Content & Gameplay Automation Squad:
    1. Capture Engineer: Unity Recorder C# automation & macOS FFmpeg (avfoundation / VideoToolbox) capture scripts
    2. Video Pipeline Scripter: MoviePy / FFmpeg Python automated editing, silence removal & 9:16 Shorts conversion
    3. YouTube & Growth SEO Strategist: High-CTR titles, devlog script hooks, timestamps, descriptions & tags
    """
    coder_model = DEFAULT_ROLE_MODELS["content_coder"]
    seo_model = DEFAULT_ROLE_MODELS["content_seo"]
    steps: List[Dict[str, Any]] = []
    total_tokens = 0

    context_section = ""
    if workspace_context:
        context_section += f"\n\n### Active Local Workspace Context\n{workspace_context}"
    if attachments_block:
        context_section += f"\n\n{attachments_block}"

    # =========================================================================
    # AGENT 1: Capture Engineer (Unity Recorder C# & macOS FFmpeg Capture)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 1,
                "agent": "Capture Engineer (Unity/FFmpeg)",
                "model": coder_model,
                "status": "Generating Unity Recorder C# automation & macOS FFmpeg hardware capture commands...",
            }
        )

    capture_sys = (
        "You are a Principal Game Capture & Graphics Automation Engineer (Agent 1 of 3 in Content Team).\n"
        "Generate production-ready gameplay capture tooling tailored to the user's request:\n"
        "1. **Unity Recorder C# Automation Script** (`// File: Assets/Editor/GameplayCaptureAutomation.cs`): "
        "Programmatic `RecorderController` setup for 60fps 1080p/4K MP4 or ProRes capture triggered by hotkeys or gameplay events.\n"
        "2. **macOS FFmpeg Hardware-Accelerated Capture Script** (`# File: scripts/capture_macos.sh`): "
        "Ready-to-run `ffmpeg -f avfoundation` commands utilizing Apple Silicon `h264_videotoolbox` / `hevc_videotoolbox` "
        "for zero-lag screen + system audio recording and high-bitrate remuxing.\n"
        "Always include the `// File: ...` or `# File: ...` comment on line 1 of every code block. Do not use emojis."
    )
    capture_user = f"CONTENT / CAPTURE TASK:\n{prompt}{context_section}"
    capture_out, t1 = await acall_llm(
        model=coder_model,
        system_prompt=capture_sys,
        user_prompt=capture_user,
        conversation_history=conversation_history,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t1
    step1 = {
        "step": 1,
        "agent": "Capture Engineer (Unity/FFmpeg)",
        "model": coder_model,
        "status": "Complete",
        "output": capture_out,
        "tokens_used": t1,
    }
    steps.append(step1)
    if on_step:
        await on_step(step1)

    # =========================================================================
    # AGENT 2: Video Pipeline Scripter (MoviePy & FFmpeg Auto-Editor)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 2,
                "agent": "Video Pipeline Scripter (MoviePy)",
                "model": coder_model,
                "status": "Building automated MoviePy / FFmpeg editing & 9:16 Shorts rendering pipeline...",
            }
        )

    pipeline_sys = (
        "You are a Senior Python Video Automation Engineer (Agent 2 of 3 in Content Squad).\n"
        "Write a complete, runnable Python video automation script (`# File: scripts/auto_edit_pipeline.py`) "
        "using `moviepy` and/or `subprocess` (`ffmpeg`) that accomplishes:\n"
        "1. **Automated Highlight Stitching & Dead-Air / Silence Trimming**.\n"
        "2. **16:9 Desktop Gameplay to 9:16 Vertical (YouTube Shorts / TikTok / Reels) Converter** "
        "with a blurred 9:16 background canvas and centered sharp gameplay foreground.\n"
        "3. **Dynamic Caption / Audio Normalization & Fast MP4 Export**.\n"
        "Ensure clean CLI arguments (`argparse`) and zero placeholder functions."
    )
    pipeline_user = (
        f"USER TASK:\n{prompt}\n\n"
        f"CAPTURE ENGINEER OUTPUT:\n{capture_out}"
        f"{context_section}"
    )
    pipeline_out, t2 = await acall_llm(
        model=coder_model,
        system_prompt=pipeline_sys,
        user_prompt=pipeline_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t2
    step2 = {
        "step": 2,
        "agent": "Video Pipeline Scripter (MoviePy)",
        "model": coder_model,
        "status": "Complete",
        "output": pipeline_out,
        "tokens_used": t2,
    }
    steps.append(step2)
    if on_step:
        await on_step(step2)

    # =========================================================================
    # AGENT 3: YouTube & Growth SEO Strategist
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 3,
                "agent": "YouTube & Growth SEO Strategist",
                "model": seo_model,
                "status": "Crafting high-CTR titles, devlog narrative hook, chapter timestamps, and SEO tags...",
            }
        )

    seo_sys = (
        "You are an Elite Game Dev YouTube Producer & Growth Strategist (Agent 3 of 3 in Content Squad).\n"
        "Generate a complete publishing package for the user's gameplay/devlog video:\n"
        "1. **5 High-CTR Title Variations** (Curiosity Gap, Technical Challenge, Transformation, Speedrun/Experiment)\n"
        "2. **Thumbnail Visual Blueprint** (Foreground focal point, 3-word text overlay, contrast palette)\n"
        "3. **First 30-Second Retention Hook Script** (Word-for-word intro + visual B-roll cues)\n"
        "4. **SEO-Optimized YouTube Description & Chapter Timestamps** (`00:00` format)\n"
        "5. **Copy-Paste Comma-Separated Tags & Shorts Hashtags**"
    )
    seo_user = f"VIDEO TOPIC & CONTEXT:\n{prompt}{context_section}"
    seo_out, t3 = await acall_llm(
        model=seo_model,
        system_prompt=seo_sys,
        user_prompt=seo_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t3
    step3 = {
        "step": 3,
        "agent": "YouTube & Growth SEO Strategist",
        "model": seo_model,
        "status": "Complete",
        "output": seo_out,
        "tokens_used": t3,
    }
    steps.append(step3)
    if on_step:
        await on_step(step3)

    formatted_report = (
        "## 1. Capture Engineer (Unity Recorder & macOS FFmpeg)\n"
        f"*Model: `{coder_model}`*\n\n"
        f"{capture_out}\n\n"
        "---\n\n"
        "## 2. Video Pipeline Scripter (MoviePy & Auto-Edit Automation)\n"
        f"*Model: `{coder_model}`*\n\n"
        f"{pipeline_out}\n\n"
        "---\n\n"
        "## 3. YouTube & Growth SEO Package\n"
        f"*Model: `{seo_model}`*\n\n"
        f"{seo_out}"
    )

    return {
        "response": formatted_report,
        "agent_badge": get_mode_badge("team:content-video"),
        "agent_steps": steps,
        "tokens_used": total_tokens,
    }
