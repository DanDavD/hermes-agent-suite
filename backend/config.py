"""Configuration and runtime settings management for Hermes Studio v2."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv, set_key

# Root project directory (/Users/Damid/.gemini/antigravity/scratch/hermes-agent-suite)
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
ENV_FILE = ROOT_DIR / ".env"

# Load root .env
load_dotenv(ENV_FILE)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_AUTH_KEY_URL = "https://openrouter.ai/api/v1/auth/key"
OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"

# Raw Model mappings
RAW_MODELS: Dict[str, str] = {
    "raw:deepseek-v3": "deepseek/deepseek-chat",
    "raw:qwen-coder-32b": "qwen/qwen-2.5-coder-32b-instruct",
    "raw:deepseek-r1": "deepseek/deepseek-r1",
    "raw:gemini-pro": "google/gemini-2.5-pro",
    "raw:gemini-flash": "google/gemini-2.5-flash",
    "raw:hermes-70b": "nousresearch/hermes-4-70b",
    "raw:claude-sonnet": "anthropic/claude-3.5-sonnet",
    "raw:free-deepseek": "deepseek/deepseek-chat:free",
}

# Agent Team workflow mappings (Pure text labels, zero emojis)
TEAM_WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "team:dev-squad": {
        "id": "team:dev-squad",
        "name": "Game/Soft Dev Team",
        "badge": "5-Agent Pipeline",
        "category": "team",
        "description": (
            "Specialized 5-agent Unity C# and software engineering pipeline: "
            "Leader (DeepSeek V3) -> Code Maker (Qwen 32B Coder) -> Code Reviewer (DeepSeek R1 Reasoning) -> "
            "UI Maker (Qwen 32B) -> UI Reviewer (Gemini 2.5 Flash)."
        ),
        "agents": [
            {"role": "Leader (Architect)", "model": "deepseek/deepseek-chat"},
            {"role": "Code Maker", "model": "qwen/qwen-2.5-coder-32b-instruct"},
            {"role": "Code Reviewer", "model": "deepseek/deepseek-r1"},
            {"role": "UI Maker", "model": "qwen/qwen-2.5-coder-32b-instruct"},
            {"role": "UI Reviewer", "model": "google/gemini-2.5-flash"},
        ],
    },
    "team:career-hunter": {
        "id": "team:career-hunter",
        "name": "Career Team",
        "badge": "4-Agent Career",
        "category": "team",
        "description": (
            "Live remote job scout (Hermes 4 + DuckDuckGo), Reddit technical interview intel miner (DeepSeek V3), "
            "ATS resume tailor (Hermes 4 Google XYZ framework), and interactive mock technical interviewer (DeepSeek V3)."
        ),
        "agents": [
            {"role": "Talent Scout (Live Web)", "model": "nousresearch/hermes-4-70b"},
            {"role": "Reddit Intel Analyst", "model": "deepseek/deepseek-chat"},
            {"role": "ATS Resume Strategist", "model": "nousresearch/hermes-4-70b"},
            {"role": "Principal Mock Interviewer", "model": "deepseek/deepseek-chat"},
        ],
    },
    "team:content-video": {
        "id": "team:content-video",
        "name": "Content Team",
        "badge": "3-Agent Media",
        "category": "team",
        "description": (
            "Generates Unity Recorder and macOS FFmpeg capture pipelines, MoviePy automated video "
            "editing scripts, and high-CTR YouTube/Shorts SEO titles, timestamps, and tags."
        ),
        "agents": [
            {"role": "Capture Engineer (Unity/FFmpeg)", "model": "qwen/qwen-2.5-coder-32b-instruct"},
            {"role": "Video Pipeline Scripter (MoviePy)", "model": "qwen/qwen-2.5-coder-32b-instruct"},
            {"role": "YouTube & Growth SEO Strategist", "model": "deepseek/deepseek-chat"},
        ],
    },
}

# Detailed Catalog of all modes (Teams + Raw Models) — Pure text labels
AVAILABLE_MODES: List[Dict[str, Any]] = [
    *TEAM_WORKFLOWS.values(),
    {
        "id": "raw:deepseek-v3",
        "name": "DeepSeek V3",
        "badge": "Daily Workhorse",
        "category": "raw",
        "model_id": RAW_MODELS["raw:deepseek-v3"],
        "description": "Sonnet-grade coding and general systems reasoning at ultra-low cost ($0.14/M tokens).",
    },
    {
        "id": "raw:qwen-coder-32b",
        "name": "Qwen 2.5 Coder 32B",
        "badge": "C# & Unity Specialist",
        "category": "raw",
        "model_id": RAW_MODELS["raw:qwen-coder-32b"],
        "description": "Specialist coding model tuned for Unity C#, MonoBehaviour architecture, shaders, and procedural sound code.",
    },
    {
        "id": "raw:deepseek-r1",
        "name": "DeepSeek R1",
        "badge": "Reasoning & Bug Hunter",
        "category": "raw",
        "model_id": RAW_MODELS["raw:deepseek-r1"],
        "description": "Deep thinking chain-of-thought model. Solves complex physics, vector math, memory leaks, and impossible bugs.",
    },
    {
        "id": "raw:gemini-pro",
        "name": "Gemini 2.5 Pro",
        "badge": "1M Token Project Analyzer",
        "category": "raw",
        "model_id": RAW_MODELS["raw:gemini-pro"],
        "description": "Massive 1M+ token context window. Ingests entire game projects and multi-file codebases simultaneously.",
    },
    {
        "id": "raw:gemini-flash",
        "name": "Gemini 2.5 Flash",
        "badge": "Sub-Second Fast Q&A",
        "category": "raw",
        "model_id": RAW_MODELS["raw:gemini-flash"],
        "description": "Ultra-fast, sub-second responses for syntax checks, quick questions, and game music/audio prompt ideas.",
    },
    {
        "id": "raw:hermes-70b",
        "name": "Nous Hermes 4 70B",
        "badge": "Autonomous & Uncensored",
        "category": "raw",
        "model_id": RAW_MODELS["raw:hermes-70b"],
        "description": "Nous Research flagship 70B model for autonomous agent loops, strict JSON adherence, and career intelligence.",
    },
    {
        "id": "raw:claude-sonnet",
        "name": "Claude 3.5 Sonnet",
        "badge": "Frontier Benchmark",
        "category": "raw",
        "model_id": RAW_MODELS["raw:claude-sonnet"],
        "description": "Anthropic frontier model for complex multi-file refactoring and high-stakes tasks.",
    },
    {
        "id": "raw:free-deepseek",
        "name": "DeepSeek V3 (Free)",
        "badge": "100% Free Sandbox",
        "category": "raw",
        "model_id": RAW_MODELS["raw:free-deepseek"],
        "description": "Free-tier endpoint on OpenRouter ($0.00 spend) for casual queries, practice, and non-critical tasks.",
    },
]

# Default role model overrides from environment
DEFAULT_ROLE_MODELS: Dict[str, str] = {
    "leader": os.getenv("MODEL_LEADER", RAW_MODELS["raw:deepseek-v3"]),
    "code_maker": os.getenv("MODEL_CODE_MAKER", RAW_MODELS["raw:qwen-coder-32b"]),
    "code_reviewer": os.getenv("MODEL_CODE_REVIEWER", RAW_MODELS["raw:deepseek-r1"]),
    "ui_maker": os.getenv("MODEL_UI_MAKER", RAW_MODELS["raw:qwen-coder-32b"]),
    "ui_reviewer": os.getenv("MODEL_UI_REVIEWER", RAW_MODELS["raw:gemini-flash"]),
    "job_hunter": os.getenv("MODEL_JOB_HUNTER", RAW_MODELS["raw:hermes-70b"]),
    "content_coder": os.getenv("MODEL_CONTENT_CODER", RAW_MODELS["raw:qwen-coder-32b"]),
    "content_seo": os.getenv("MODEL_CONTENT_SEO", RAW_MODELS["raw:deepseek-v3"]),
}

# Workspace scanner token limit (~45,000 tokens)
WORKSPACE_TOKEN_BUDGET = 45000
MAX_SINGLE_FILE_BYTES = 512 * 1024  # 512 KB cap per individual file


class RuntimeSettings:
    """Thread-safe in-memory runtime settings backed by .env."""

    def __init__(self) -> None:
        load_dotenv(ENV_FILE, override=True)
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.temperature: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
        self.max_tokens: int = int(os.getenv("DEFAULT_MAX_TOKENS", "4096"))

    def get_api_key(self) -> str:
        """Returns the active OpenRouter API key."""
        if self.openrouter_api_key:
            return self.openrouter_api_key
        env_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if env_key and env_key != "your_openrouter_api_key_here":
            self.openrouter_api_key = env_key
            return env_key
        return ""

    def get_masked_key(self) -> str:
        """Returns a safely masked preview of the API key."""
        key = self.get_api_key()
        if not key or key == "your_openrouter_api_key_here":
            return ""
        if len(key) <= 12:
            return "***"
        return f"{key[:8]}...{key[-4:]}"

    def update(
        self,
        openrouter_api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        persist_env: bool = True,
    ) -> Dict[str, Any]:
        """Updates runtime settings in memory and optionally persists to root .env."""
        if openrouter_api_key is not None:
            cleaned_key = openrouter_api_key.strip()
            if cleaned_key:
                self.openrouter_api_key = cleaned_key
                os.environ["OPENROUTER_API_KEY"] = cleaned_key
                if persist_env and ENV_FILE.exists():
                    try:
                        set_key(str(ENV_FILE), "OPENROUTER_API_KEY", cleaned_key)
                    except Exception:
                        pass

        if temperature is not None:
            self.temperature = max(0.0, min(2.0, float(temperature)))
            os.environ["DEFAULT_TEMPERATURE"] = str(self.temperature)

        if max_tokens is not None:
            self.max_tokens = max(128, min(32768, int(max_tokens)))
            os.environ["DEFAULT_MAX_TOKENS"] = str(self.max_tokens)

        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current runtime configuration."""
        key = self.get_api_key()
        return {
            "api_key_configured": bool(key and key != "your_openrouter_api_key_here"),
            "api_key_masked": self.get_masked_key(),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "workspace_token_budget": WORKSPACE_TOKEN_BUDGET,
            "available_modes": AVAILABLE_MODES,
        }


runtime_settings = RuntimeSettings()


def resolve_mode(mode: Optional[str]) -> str:
    """Normalizes mode identifiers to canonical team:* or raw:* strings."""
    if not mode:
        return "team:dev-squad"
    mode = mode.strip()
    if mode in RAW_MODELS or mode in TEAM_WORKFLOWS:
        return mode

    aliases = {
        "dev-squad": "team:dev-squad",
        "dev_squad": "team:dev-squad",
        "career-hunter": "team:career-hunter",
        "career_hunter": "team:career-hunter",
        "job_hunter": "team:career-hunter",
        "content-video": "team:content-video",
        "content_video": "team:content-video",
        "deepseek-v3": "raw:deepseek-v3",
        "deepseek_v3": "raw:deepseek-v3",
        "deepseek-chat": "raw:deepseek-v3",
        "qwen-coder-32b": "raw:qwen-coder-32b",
        "qwen_coder_32b": "raw:qwen-coder-32b",
        "deepseek-r1": "raw:deepseek-r1",
        "deepseek_r1": "raw:deepseek-r1",
        "gemini-pro": "raw:gemini-pro",
        "gemini_pro": "raw:gemini-pro",
        "gemini-flash": "raw:gemini-flash",
        "gemini_flash": "raw:gemini-flash",
        "hermes-70b": "raw:hermes-70b",
        "hermes_70b": "raw:hermes-70b",
        "claude-sonnet": "raw:claude-sonnet",
        "claude_sonnet": "raw:claude-sonnet",
        "free-deepseek": "raw:free-deepseek",
        "free_deepseek": "raw:free-deepseek",
    }
    if mode in aliases:
        return aliases[mode]

    for k, v in RAW_MODELS.items():
        if mode == v:
            return k

    return "team:dev-squad"


def get_mode_badge(mode: str) -> str:
    """Returns a human-friendly pure-text badge string for a given mode."""
    resolved = resolve_mode(mode)
    for item in AVAILABLE_MODES:
        if item["id"] == resolved:
            return item["badge"]
    return resolved
