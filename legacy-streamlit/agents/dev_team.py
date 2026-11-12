import os
from typing import Dict, Any, Generator, Optional
from openai import OpenAI
from config import OPENROUTER_BASE_URL, OPENROUTER_API_KEY, DEFAULT_ROLES

def get_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key or OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise ValueError("OpenRouter API key is missing. Please set OPENROUTER_API_KEY in your .env file or input it in the UI.")
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
    )

def call_llm(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2
) -> str:
    """Invokes a model via OpenRouter API with neutral, direct formatting."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""

class DevSquad:
    def __init__(self, api_key: Optional[str] = None, role_models: Optional[Dict[str, str]] = None):
        self.client = get_client(api_key)
        self.models = role_models or DEFAULT_ROLES

    def run_squad(self, task_description: str, project_context: str = "") -> Generator[Dict[str, Any], None, None]:
        """
        Executes the 5-agent pipeline sequentially, yielding intermediate results
        so the user/GUI can track each agent's thoughts and outputs in real-time.
        """
        context_block = f"\n\nProject Context:\n{project_context}" if project_context else ""

        # =====================================================================
        # AGENT 1: The Team Leader / Architect
        # =====================================================================
        yield {
            "step": 1,
            "agent": "Leader (Orchestrator)",
            "model": self.models["leader"],
            "status": "Planning architecture and technical requirements...",
        }
        leader_sys = (
            "You are the Lead Software & Game Architect. Your goal is to analyze the user's task and provide:\n"
            "1. Architectural Overview & System Breakdown\n"
            "2. Technical Requirements for the Code Maker (Data structures, design patterns, Unity/C# specifics)\n"
            "3. Visual & Component Requirements for the UI Maker\n"
            "Be direct, modular, and technically precise."
        )
        leader_prompt = f"TASK:\n{task_description}{context_block}"
        leader_output = call_llm(self.client, self.models["leader"], leader_sys, leader_prompt)
        yield {
            "step": 1,
            "agent": "Leader (Orchestrator)",
            "model": self.models["leader"],
            "status": "Complete",
            "output": leader_output,
        }

        # =====================================================================
        # AGENT 2: Code Maker
        # =====================================================================
        yield {
            "step": 2,
            "agent": "Code Maker",
            "model": self.models["code_maker"],
            "status": "Implementing clean, production-ready code...",
        }
        code_sys = (
            "You are an Elite Game & Software Developer. Your job is to implement the exact code requested "
            "based on the Leader's architecture. Write full, clean, performant code (C#/Unity, Python, or target language). "
            "Include necessary namespaces, memory-safe patterns, and avoid placeholder comments like '// implement here'."
        )
        code_prompt = (
            f"ORIGINAL TASK:\n{task_description}\n\n"
            f"LEADER'S ARCHITECTURAL SPECIFICATION:\n{leader_output}"
        )
        code_output = call_llm(self.client, self.models["code_maker"], code_sys, code_prompt)
        yield {
            "step": 2,
            "agent": "Code Maker",
            "model": self.models["code_maker"],
            "status": "Complete",
            "output": code_output,
        }

        # =====================================================================
        # AGENT 3: Code Reviewer
        # =====================================================================
        yield {
            "step": 3,
            "agent": "Code Reviewer",
            "model": self.models["code_reviewer"],
            "status": "Reviewing code for bugs, memory leaks, and performance bottlenecks...",
        }
        review_sys = (
            "You are a Senior Principal Code Reviewer and Performance Engineer. Review the code written by the Code Maker.\n"
            "Critique:\n"
            "1. Logical correctness & edge cases\n"
            "2. Performance & Garbage Collection (crucial for games: Avoid allocations in Update loops, cache references)\n"
            "3. Cleanliness & SOLID adherence\n"
            "If bugs exist, provide the corrected snippet. If the code is solid, approve it with a concise summary."
        )
        review_prompt = (
            f"TASK:\n{task_description}\n\n"
            f"CODE SUBMITTED:\n{code_output}"
        )
        review_output = call_llm(self.client, self.models["code_reviewer"], review_sys, review_prompt)
        yield {
            "step": 3,
            "agent": "Code Reviewer",
            "model": self.models["code_reviewer"],
            "status": "Complete",
            "output": review_output,
        }

        # =====================================================================
        # AGENT 4: UI Maker
        # =====================================================================
        yield {
            "step": 4,
            "agent": "UI Maker",
            "model": self.models["ui_maker"],
            "status": "Creating UI layouts and interaction controllers...",
        }
        ui_sys = (
            "You are a Specialist Game & Software UI Developer. Design the UI elements, hierarchy, and UI controller "
            "code (e.g. Unity UI Toolkit / uGUI, or Web UI) required for this feature, following the Leader's specs."
        )
        ui_prompt = (
            f"TASK:\n{task_description}\n\n"
            f"LEADER'S UI SPECIFICATION:\n{leader_output}\n\n"
            f"CORE CODE:\n{code_output}"
        )
        ui_output = call_llm(self.client, self.models["ui_maker"], ui_sys, ui_prompt)
        yield {
            "step": 4,
            "agent": "UI Maker",
            "model": self.models["ui_maker"],
            "status": "Complete",
            "output": ui_output,
        }

        # =====================================================================
        # AGENT 5: UI Reviewer
        # =====================================================================
        yield {
            "step": 5,
            "agent": "UI Reviewer",
            "model": self.models["ui_reviewer"],
            "status": "Validating UX layout, responsiveness, and component hierarchy...",
        }
        ui_review_sys = (
            "You are a UX & UI Reviewer. Validate the UI solution created by UI Maker. Check:\n"
            "1. Layout hierarchy & responsiveness across aspect ratios\n"
            "2. Feedback states (hover, click, disable)\n"
            "3. Usability and visual clarity\n"
            "Provide short actionable feedback or approval."
        )
        ui_review_prompt = (
            f"TASK:\n{task_description}\n\n"
            f"UI IMPLEMENTATION:\n{ui_output}"
        )
        ui_review_output = call_llm(self.client, self.models["ui_reviewer"], ui_review_sys, ui_review_prompt)
        yield {
            "step": 5,
            "agent": "UI Reviewer",
            "model": self.models["ui_reviewer"],
            "status": "Complete",
            "output": ui_review_output,
        }
