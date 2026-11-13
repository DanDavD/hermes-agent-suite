"""Career Intelligence Squad (`team:career-hunter`) workflow with live DuckDuckGo search."""

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional
from duckduckgo_search import DDGS

from backend.config import DEFAULT_ROLE_MODELS, ROOT_DIR, get_mode_badge
from backend.services.openrouter_client import acall_llm

StepCallback = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


def _sync_ddg_search(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Executes synchronous DuckDuckGo text search safely."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": str(r.get("title", "")),
                    "body": str(r.get("body", "")),
                    "href": str(r.get("href", "")),
                }
                for r in results
            ]
    except Exception as exc:
        return [{"title": "Live Search Notice", "body": f"DuckDuckGo query note: {exc}", "href": ""}]


async def search_web_async(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Runs DuckDuckGo web search in a background thread to keep FastAPI async non-blocking."""
    return await asyncio.to_thread(_sync_ddg_search, query, max_results)


def detect_career_intent(prompt: str, sub_mode: Optional[str] = None) -> List[str]:
    """
    Detects which Career Intelligence sub-agents to invoke based on sub_mode or prompt keywords.
    Returns one or more of: 'jobs', 'intel', 'resume', 'interview'.
    """
    if sub_mode:
        sm = sub_mode.strip().lower()
        if sm in ("jobs", "intel", "resume", "interview"):
            return [sm]
        if sm == "all" or sm == "combined":
            return ["jobs", "intel"]

    text = prompt.lower()
    intents: List[str] = []

    # Check Mock Interview intent
    interview_triggers = [
        "mock interview",
        "interview me",
        "quiz me",
        "ask me a question",
        "my answer is",
        "next question",
        "practice interview",
    ]
    if any(k in text for k in interview_triggers):
        return ["interview"]

    # Check Resume Tailor intent
    resume_triggers = [
        "tailor",
        "resume",
        "cv",
        "ats",
        "bullet point",
        "rewrite my profile",
        "cover letter",
    ]
    if any(k in text for k in resume_triggers):
        intents.append("resume")

    # Check Reddit / Interview Intel intent
    intel_triggers = [
        "reddit",
        "interview intel",
        "interview question",
        "what do they ask",
        "technical test",
        "take-home",
        "glassdoor",
        "candidate experience",
    ]
    if any(k in text for k in intel_triggers):
        intents.append("intel")

    # Check Live Job Search intent
    job_triggers = [
        "find job",
        "job opening",
        "openings",
        "hiring",
        "remote job",
        "internship",
        "junior",
        "entry level",
        "entry-level",
        "search job",
        "roles for",
        "vacancies",
    ]
    if any(k in text for k in job_triggers):
        intents.append("jobs")

    # Default to combined Live Job Search + Reddit Interview Intel if general career query
    if not intents:
        intents = ["jobs", "intel"]

    return intents


def _load_fallback_master_resume() -> str:
    """Loads master_resume_example.md from project root if available."""
    resume_path = ROOT_DIR / "master_resume_example.md"
    if resume_path.is_file():
        try:
            return resume_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return ""


async def run_career_hunter_workflow(
    prompt: str,
    workspace_context: str = "",
    attachments_block: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    sub_mode: Optional[str] = None,
    on_step: StepCallback = None,
) -> Dict[str, Any]:
    """
    Executes the Career Intelligence Team workflow:
    - Live Remote Job Search (DuckDuckGo + Talent Scout Agent)
    - Reddit & Forum Interview Intel (DuckDuckGo + Intel Analyst Agent)
    - ATS Resume Tailor (Google XYZ Framework Strategist Agent)
    - Interactive Mock Technical Interview (Principal Engineer Interviewer Agent)
    """
    model = DEFAULT_ROLE_MODELS["job_hunter"]
    intents = detect_career_intent(prompt, sub_mode=sub_mode)
    steps: List[Dict[str, Any]] = []
    sections: List[str] = []
    total_tokens = 0
    step_num = 0

    context_section = ""
    if attachments_block:
        context_section += f"\n\n{attachments_block}"
    if workspace_context:
        context_section += f"\n\n### Active Workspace Context\n{workspace_context}"

    # =========================================================================
    # PIPELINE A: Live Remote Job Search
    # =========================================================================
    if "jobs" in intents:
        step_num += 1
        search_query = (
            f'({prompt[:120]}) ("remote worldwide" OR "remote anywhere" OR "remote") '
            f'("entry level" OR "junior" OR "internship" OR "developer" OR "engineer") job'
        )
        if on_step:
            await on_step(
                {
                    "step": step_num,
                    "agent": "Talent Scout (Live Web Search)",
                    "model": model,
                    "status": f"Searching live job openings via DuckDuckGo...",
                }
            )

        raw_jobs = await search_web_async(search_query, max_results=8)

        scout_sys = (
            "You are a Senior Technical Talent Scout in the Career Team.\n"
            "Analyze the live DuckDuckGo web search results and extract high-signal job opportunities "
            "and actionable job board targets matching the user's request.\n"
            "Do not use emojis; use clean text formatting only.\n"
            "Format each opportunity cleanly in Markdown:\n"
            "### [Job Title / Program] - [Company or Source]\n"
            "- **Location / Policy**: [Remote Worldwide / Region / Hybrid]\n"
            "- **Level**: [Junior / Entry Level / Internship / Mid]\n"
            "- **Core Tech Stack**: [e.g., Unity, C#, Shaders, Python, Git]\n"
            "- **Why It Matches**: [1-2 concise sentences]\n"
            "- **Direct Link**: [Exact URL from search data]\n\n"
            "Also include a **Boolean Search Playbook** section with 3 custom search queries the candidate can click/use on LinkedIn, Wellfound, and WorkWithIndies."
        )
        scout_user = (
            f"CANDIDATE TARGET / REQUEST:\n{prompt}\n\n"
            f"LIVE DUCKDUCKGO WEB RESULTS:\n{json.dumps(raw_jobs, indent=2)}"
            f"{context_section}"
        )
        jobs_out, t_jobs = await acall_llm(
            model=model,
            system_prompt=scout_sys,
            user_prompt=scout_user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        total_tokens += t_jobs
        s_obj = {
            "step": step_num,
            "agent": "Talent Scout (Live Web Search)",
            "model": model,
            "status": "Complete",
            "output": jobs_out,
            "tokens_used": t_jobs,
        }
        steps.append(s_obj)
        if on_step:
            await on_step(s_obj)
        sections.append(f"## Live Remote Job Scout\n{jobs_out}")

    # =========================================================================
    # PIPELINE B: Reddit & Forum Interview Intel Miner
    # =========================================================================
    if "intel" in intents:
        step_num += 1
        intel_query = (
            f'site:reddit.com ({prompt[:100]}) '
            f'("interview questions" OR "technical test" OR "coding challenge" OR "hiring process")'
        )
        if on_step:
            await on_step(
                {
                    "step": step_num,
                    "agent": "Reddit Intel Analyst",
                    "model": model,
                    "status": "Mining firsthand candidate reports & interview questions from Reddit...",
                }
            )

        raw_intel = await search_web_async(intel_query, max_results=7)

        intel_sys = (
            "You are an Elite Career Intelligence Analyst.\n"
            "Synthesize the live Reddit/community search results and your deep domain knowledge of game/software studio hiring into:\n"
            "1. **Actual Technical Questions Asked** (Unity lifecycle, C# memory/GC, `.shader`/HLSL, algorithms, system design)\n"
            "2. **Take-Home & Live Coding Test Formats** (typical constraints, evaluation rubric, common pitfalls)\n"
            "3. **What Successful Candidates Did Right** (portfolio demos, GitHub structure, profiler literacy)\n"
            "4. **Red Flags & Negotiation Intel**\n"
            "Cite relevant community threads where available."
        )
        intel_user = (
            f"TARGET ROLE / COMPANY:\n{prompt}\n\n"
            f"COMMUNITY & REDDIT DATA:\n{json.dumps(raw_intel, indent=2)}"
            f"{context_section}"
        )
        intel_out, t_intel = await acall_llm(
            model=model,
            system_prompt=intel_sys,
            user_prompt=intel_user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        total_tokens += t_intel
        s_obj = {
            "step": step_num,
            "agent": "Reddit Intel Analyst",
            "model": model,
            "status": "Complete",
            "output": intel_out,
            "tokens_used": t_intel,
        }
        steps.append(s_obj)
        if on_step:
            await on_step(s_obj)
        sections.append(f"## Reddit & Community Interview Intelligence\n{intel_out}")

    # =========================================================================
    # PIPELINE C: ATS Resume Strategist
    # =========================================================================
    if "resume" in intents:
        step_num += 1
        if on_step:
            await on_step(
                {
                    "step": step_num,
                    "agent": "ATS Resume Strategist",
                    "model": model,
                    "status": "Optimizing resume bullets with Google XYZ framework & ATS keyword alignment...",
                }
            )

        fallback_resume = _load_fallback_master_resume()
        resume_context = context_section
        if not attachments_block and fallback_resume:
            resume_context += f"\n\n### Reference Master Resume (`master_resume_example.md`)\n{fallback_resume}"

        resume_sys = (
            "You are an Elite Technical Resume Strategist & Former Lead Game/Software Recruiter.\n"
            "Re-engineer the candidate's resume/profile to achieve a 95%+ ATS match against the target role:\n"
            "1. **NEVER invent fictional jobs, degrees, or tools** not grounded in the candidate's profile.\n"
            "2. Rewrite experience & project bullets using the Google XYZ formula: "
            "*'Accomplished [X] as measured by [Y], by doing [Z]'*.\n"
            "3. Front-load high-signal keywords (e.g., Unity, C#, Object Pooling, ShaderLab, Profiling, CI/CD, Python).\n"
            "4. Include an **ATS Keyword Gap Analysis Table** (Matched Keywords vs Recommended Additions) "
            "followed by the complete, copy-pasteable **Tailored Markdown Resume**."
        )
        resume_user = f"USER REQUEST & TARGET JOB DESCRIPTION:\n{prompt}{resume_context}"
        resume_out, t_res = await acall_llm(
            model=model,
            system_prompt=resume_sys,
            user_prompt=resume_user,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        total_tokens += t_res
        s_obj = {
            "step": step_num,
            "agent": "ATS Resume Strategist",
            "model": model,
            "status": "Complete",
            "output": resume_out,
            "tokens_used": t_res,
        }
        steps.append(s_obj)
        if on_step:
            await on_step(s_obj)
        sections.append(f"## ATS Resume & Profile Optimization\n{resume_out}")

    # =========================================================================
    # PIPELINE D: Interactive Mock Technical Interview
    # =========================================================================
    if "interview" in intents:
        step_num += 1
        if on_step:
            await on_step(
                {
                    "step": step_num,
                    "agent": "Principal Mock Interviewer",
                    "model": model,
                    "status": "Evaluating technical response and preparing next interview question...",
                }
            )

        interview_sys = (
            "You are a Principal Game & Software Systems Engineer conducting a live technical interview.\n"
            "Structure your response as follows:\n"
            "- **If the user just answered a previous question**:\n"
            "  1. **Score & Technical Critique (out of 10)**: Evaluate accuracy, memory/GC awareness, edge cases, and architectural clarity.\n"
            "  2. **Ideal Senior-Level Answer**: Briefly show the gold-standard answer or code snippet.\n"
            "  3. **Next Interview Question**: Ask ONE focused, realistic technical question.\n"
            "- **If the user is starting a new mock interview**:\n"
            "  Set the stage briefly and ask **Question #1** (focusing on Unity C# internals, memory management, gameplay math, or software architecture)."
        )
        interview_user = f"{prompt}{context_section}"
        interview_out, t_int = await acall_llm(
            model=model,
            system_prompt=interview_sys,
            user_prompt=interview_user,
            conversation_history=conversation_history,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        total_tokens += t_int
        s_obj = {
            "step": step_num,
            "agent": "Principal Mock Interviewer",
            "model": model,
            "status": "Complete",
            "output": interview_out,
            "tokens_used": t_int,
        }
        steps.append(s_obj)
        if on_step:
            await on_step(s_obj)
        sections.append(f"## Interactive Mock Technical Interview\n{interview_out}")

    final_report = "\n\n---\n\n".join(sections)
    return {
        "response": final_report,
        "agent_badge": get_mode_badge("team:career-hunter"),
        "agent_steps": steps,
        "tokens_used": total_tokens,
    }
