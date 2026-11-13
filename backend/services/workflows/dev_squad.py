"""5-Agent Game & Software Development Squad (`team:dev-squad`) workflow."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from backend.config import DEFAULT_ROLE_MODELS, get_mode_badge
from backend.services.openrouter_client import acall_llm

StepCallback = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


def _is_code_implementation_task(prompt: str) -> bool:
    """
    Distinguishes between a code implementation/refactoring task (which warrants the full 5-agent squad)
    versus a direct advisory, architectural, or tool/model selection question (which should be answered
    directly by the Lead Architect in 1 fast step without burning 5x tokens).
    """
    q = (prompt or "").strip().lower()
    if not q:
        return False

    # Explicit advisory / question patterns -> Fast 1-Agent Lead Architect response
    advisory_patterns = (
        "what would be the best",
        "which model",
        "best model",
        "what model",
        "que modelo",
        "qué modelo",
        "cual es el mejor",
        "cuál es el mejor",
        "recommend",
        "recomiendas",
        "explain",
        "explica",
        "difference between",
        "should i use",
        "how does",
        "what is ",
    )
    if any(p in q for p in advisory_patterns) and not any(
        w in q for w in ("write a script", "implement", "create a file", "refactor")
    ):
        return False

    # Keywords that warrant running the full multi-agent coding pipeline
    coding_keywords = (
        "write",
        "implement",
        "create",
        "build",
        "refactor",
        "code",
        "script",
        "controller",
        "shader",
        "system",
        "fix",
        "debug",
        "optimize",
        "audit",
        "component",
        "class",
        "ui",
        "hud",
        "menu",
        "crea",
        "programa",
        "escribe",
        "implementa",
        "arregla",
    )
    return any(kw in q for kw in coding_keywords)


async def run_dev_squad_workflow(
    prompt: str,
    workspace_context: str = "",
    attachments_block: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    on_step: StepCallback = None,
) -> Dict[str, Any]:
    """
    Executes the Game/Software Dev Squad:
    - If the prompt is a direct consultation/question, the Lead Architect answers directly in 1 fast step.
    - If the prompt is an engineering implementation task, executes the 5-agent pipeline:
      1. Leader (Architect & Orchestrator)
      2. Code Maker (Implementation Specialist)
      3. Code Reviewer (Performance & QA Auditor)
      4. UI Maker (UI Toolkit / uGUI / Frontend Builder)
      5. UI Reviewer (UX & Responsiveness Auditor)
    """
    models = DEFAULT_ROLE_MODELS
    steps: List[Dict[str, Any]] = []
    total_tokens = 0

    context_section = ""
    if workspace_context:
        context_section += f"\n\n### Active Local Workspace Context\n{workspace_context}"
    if attachments_block:
        context_section += f"\n\n{attachments_block}"

    # Fast-path for advisory/consultation questions (1 step, minimal tokens)
    if not _is_code_implementation_task(prompt):
        if on_step:
            await on_step(
                {
                    "step": 1,
                    "agent": "Leader (Architect)",
                    "model": models["leader"],
                    "status": "Answering engineering consultation...",
                }
            )

        consult_sys = (
            "You are the Lead Software & Game Architect of the Hermes Studio Game/Soft Dev Team.\n"
            "Answer the user's question directly, concisely, and with practical engineering recommendations.\n"
            "AUTONOMOUS AGENT STANDARD:\n"
            "- NEVER say 'as an AI I cannot generate binary files' or tell the user to manually visit external websites or do manual GUI dragging in Unity.\n"
            "- If the user asks to generate music, SFX, or assets, provide the exact automated code to do it: either a procedural audio synthesizer (e.g. Unity AudioClip.Create / OnAudioFilterRead) or an automated Python script using standard library 'wave' to generate the .wav file directly into Assets/.\n"
            "- If they ask about models inside Hermes Studio, recommend the best specialist:\n"
            "  * Qwen 2.5 Coder 32B: Best for Unity C#, procedural audio, and shaders.\n"
            "  * DeepSeek V3: Best daily driver for architecture and game systems.\n"
            "  * DeepSeek R1: Best for physics, algorithms, and deep debugging.\n"
            "  * Gemini 2.5 Flash: Sub-second fast Q&A."
        )
        consult_user = f"{prompt}{context_section}"
        consult_out, t_consult = await acall_llm(
            model=models["leader"],
            system_prompt=consult_sys,
            user_prompt=consult_user,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        step_consult = {
            "step": 1,
            "agent": "Leader (Architect)",
            "model": models["leader"],
            "status": "Complete",
            "output": consult_out,
            "tokens_used": t_consult,
        }
        if on_step:
            await on_step(step_consult)

        return {
            "response": consult_out,
            "agent_badge": get_mode_badge("team:dev-squad"),
            "agent_steps": [step_consult],
            "tokens_used": t_consult,
        }

    # =========================================================================
    # AGENT 1: Leader (Architect & Orchestrator)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 1,
                "agent": "Leader (Architect)",
                "model": models["leader"],
                "status": "Planning system architecture and technical requirements...",
            }
        )

    leader_sys = (
        "You are the Lead Software & Game Architect (Agent 1 of 5 in the Game/Soft Dev Team).\n"
        "Analyze the user's request and active workspace context to produce an automated engineering blueprint:\n"
        "1. Architectural Overview & Module Breakdown (exact relative file paths to create/modify, matching active project namespaces)\n"
        "2. Core Engineering Specifications for Code Maker (data structures, patterns, Unity C# lifecycle, zero GC allocations in hot loops)\n"
        "3. Zero-Manual-Chores Automation: NEVER tell the user to manually create GameObjects, drag components, or visit third-party sites.\n"
        "   If scene setup is needed, specify a Unity Editor script (`Assets/_Project/Editor/...Setup.cs`) to automate it in code.\n"
        "   If music/audio is needed, specify procedural audio synthesis or a Python wave generator to synthesize the .wav asset directly.\n"
        "Be concise, modular, and technically rigorous. Do not use emojis; use clean text labels only."
    )
    leader_user = f"USER TASK:\n{prompt}{context_section}"
    leader_out, t1 = await acall_llm(
        model=models["leader"],
        system_prompt=leader_sys,
        user_prompt=leader_user,
        conversation_history=conversation_history,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t1
    step1 = {
        "step": 1,
        "agent": "Leader (Architect)",
        "model": models["leader"],
        "status": "Complete",
        "output": leader_out,
        "tokens_used": t1,
    }
    steps.append(step1)
    if on_step:
        await on_step(step1)

    # =========================================================================
    # AGENT 2: Code Maker (Implementation Specialist)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 2,
                "agent": "Code Maker",
                "model": models["code_maker"],
                "status": "Implementing production-ready code...",
            }
        )

    code_sys = (
        "You are an Elite Game & Software Developer (Agent 2 of 5: Code Maker).\n"
        "Implement the complete, production-ready source code following the Leader's architecture.\n"
        "Strict Engineering Rules:\n"
        "- Write full, working implementations (Unity C#, ShaderLab, Python, TypeScript, etc.) with zero placeholders like `// TODO`.\n"
        "- Begin EVERY code block with a file path comment on the very first line, e.g.:\n"
        "  `// File: Assets/Scripts/Systems/InventoryManager.cs` or `# File: scripts/processor.py`\n"
        "  so the user can click 'Apply to Workspace' to save the file directly into their project.\n"
        "- In Unity C#, cache component references in `Awake()` and avoid heap allocations inside `Update()`.\n"
        "- Match existing project namespaces (e.g. `GameJam.Gameplay`, `GameJam.Core`, `GameJam.UI` for GodBoard).\n"
        "- AUTONOMY & ZERO-MANUAL-CHORES POLICY:\n"
        "  * NEVER tell the user to manually create GameObjects in the Unity Editor or drag fields in the Inspector.\n"
        "    Instead, provide a Unity Editor script (`Assets/_Project/Editor/...Setup.cs`) with `[MenuItem]` or `[InitializeOnLoadMethod]` that programmatically creates GameObjects, adds components, and links references.\n"
        "  * NEVER say 'as an AI I cannot generate binary files, go to Suno.ai'. If audio, music, or SFX is requested, provide a procedural audio synthesizer (using Unity `OnAudioFilterRead` or `AudioClip.Create`) or generate a runnable Python script using standard library `wave` to write the real `.wav` file directly to disk."
    )
    code_user = (
        f"ORIGINAL TASK:\n{prompt}\n\n"
        f"LEADER'S ARCHITECTURAL SPECIFICATION:\n{leader_out}"
        f"{context_section}"
    )
    code_out, t2 = await acall_llm(
        model=models["code_maker"],
        system_prompt=code_sys,
        user_prompt=code_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t2
    step2 = {
        "step": 2,
        "agent": "Code Maker",
        "model": models["code_maker"],
        "status": "Complete",
        "output": code_out,
        "tokens_used": t2,
    }
    steps.append(step2)
    if on_step:
        await on_step(step2)

    # =========================================================================
    # AGENT 3: Code Reviewer (Performance & QA Auditor)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 3,
                "agent": "Code Reviewer",
                "model": models["code_reviewer"],
                "status": "Auditing logic, memory safety, and frame-time performance...",
            }
        )

    review_sys = (
        "You are a Principal Code Reviewer & Performance Engineer (Agent 3 of 5: Code Reviewer).\n"
        "Audit the Code Maker's implementation across:\n"
        "1. **Logical Correctness & Edge Cases** (null safety, race conditions, serialization)\n"
        "2. **Frame-Time & Memory Performance** (zero GC allocations in hot loops, pooling, struct vs class usage)\n"
        "3. **Architecture & SOLID Compliance**\n"
        "If any defect or optimization is needed, provide the patched code block with the `// File: ...` header."
    )
    review_user = (
        f"TASK:\n{prompt}\n\n"
        f"CODE MAKER IMPLEMENTATION:\n{code_out}"
    )
    review_out, t3 = await acall_llm(
        model=models["code_reviewer"],
        system_prompt=review_sys,
        user_prompt=review_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t3
    step3 = {
        "step": 3,
        "agent": "Code Reviewer",
        "model": models["code_reviewer"],
        "status": "Complete",
        "output": review_out,
        "tokens_used": t3,
    }
    steps.append(step3)
    if on_step:
        await on_step(step3)

    # =========================================================================
    # AGENT 4: UI Maker (UI Toolkit / uGUI / Frontend Specialist)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 4,
                "agent": "UI Maker",
                "model": models["ui_maker"],
                "status": "Building UI controllers, layouts, and visual bindings...",
            }
        )

    ui_sys = (
        "You are a Senior Game & Software UI Engineer (Agent 4 of 5: UI Maker).\n"
        "Design and implement the UI layer (Unity UI Toolkit UXML/USS, uGUI Canvas C# controllers, or Web UI components) "
        "that connects cleanly to the Code Maker's core logic.\n"
        "Include the target relative path on the first line of every code block (e.g., `// File: Assets/Scripts/UI/HUDController.cs`)."
    )
    ui_user = (
        f"TASK:\n{prompt}\n\n"
        f"LEADER'S UI SPECIFICATION:\n{leader_out}\n\n"
        f"CORE CODE IMPLEMENTATION:\n{code_out}"
    )
    ui_out, t4 = await acall_llm(
        model=models["ui_maker"],
        system_prompt=ui_sys,
        user_prompt=ui_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t4
    step4 = {
        "step": 4,
        "agent": "UI Maker",
        "model": models["ui_maker"],
        "status": "Complete",
        "output": ui_out,
        "tokens_used": t4,
    }
    steps.append(step4)
    if on_step:
        await on_step(step4)

    # =========================================================================
    # AGENT 5: UI Reviewer (UX & Responsiveness Auditor)
    # =========================================================================
    if on_step:
        await on_step(
            {
                "step": 5,
                "agent": "UI Reviewer",
                "model": models["ui_reviewer"],
                "status": "Validating UX ergonomics, aspect-ratio scaling, and state feedback...",
            }
        )

    ui_review_sys = (
        "You are a UX Director & UI Reviewer (Agent 5 of 5: UI Reviewer).\n"
        "Evaluate the UI Maker's implementation for:\n"
        "1. **Hierarchy & Responsive Scaling** (16:9, 21:9 ultrawide, 16:10 Steam Deck / macOS Retina)\n"
        "2. **Interactive Feedback** (hover, pressed, disabled, tweening/transitions, audio/visual cues)\n"
        "3. **Usability & Integration Polish**\n"
        "Provide a concise final sign-off checklist and any high-impact UX refinements."
    )
    ui_review_user = (
        f"TASK:\n{prompt}\n\n"
        f"UI IMPLEMENTATION:\n{ui_out}"
    )
    ui_review_out, t5 = await acall_llm(
        model=models["ui_reviewer"],
        system_prompt=ui_review_sys,
        user_prompt=ui_review_user,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    total_tokens += t5
    step5 = {
        "step": 5,
        "agent": "UI Reviewer",
        "model": models["ui_reviewer"],
        "status": "Complete",
        "output": ui_review_out,
        "tokens_used": t5,
    }
    steps.append(step5)
    if on_step:
        await on_step(step5)

    # Assemble structured multi-agent Markdown report
    formatted_report = (
        "## 1. Leader (Architect & Orchestrator)\n"
        f"*Model: `{models['leader']}`*\n\n"
        f"{leader_out}\n\n"
        "---\n\n"
        "## 2. Code Maker (Core Implementation)\n"
        f"*Model: `{models['code_maker']}`*\n\n"
        f"{code_out}\n\n"
        "---\n\n"
        "## 3. Code Reviewer (Performance & QA Audit)\n"
        f"*Model: `{models['code_reviewer']}`*\n\n"
        f"{review_out}\n\n"
        "---\n\n"
        "## 4. UI Maker (Interface & Controllers)\n"
        f"*Model: `{models['ui_maker']}`*\n\n"
        f"{ui_out}\n\n"
        "---\n\n"
        "## 5. UI Reviewer (UX & Responsiveness Sign-Off)\n"
        f"*Model: `{models['ui_reviewer']}`*\n\n"
        f"{ui_review_out}"
    )

    return {
        "response": formatted_report,
        "agent_badge": get_mode_badge("team:dev-squad"),
        "agent_steps": steps,
        "tokens_used": total_tokens,
    }
