import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (checks root repository first, then local directory)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Models
MODELS = {
    # Hermes Models
    "hermes_70b": "nousresearch/hermes-3-llama-3.1-70b",
    "hermes_8b": "nousresearch/hermes-3-llama-3.1-8b",
    "hermes_405b": "nousresearch/hermes-3-llama-3.1-405b",
    # Coding specialist models
    "qwen_coder_32b": "qwen/qwen-2.5-coder-32b-instruct",
    # Frontier model for complex tasks if desired
    "claude_sonnet": "anthropic/claude-3.5-sonnet",
}

# Role default mappings
DEFAULT_ROLES = {
    "leader": os.getenv("MODEL_LEADER", MODELS["hermes_70b"]),
    "code_maker": os.getenv("MODEL_CODE_MAKER", MODELS["qwen_coder_32b"]),
    "code_reviewer": os.getenv("MODEL_CODE_REVIEWER", MODELS["hermes_70b"]),
    "ui_maker": os.getenv("MODEL_UI_MAKER", MODELS["hermes_70b"]),
    "ui_reviewer": os.getenv("MODEL_UI_REVIEWER", MODELS["hermes_8b"]),
    "job_hunter": os.getenv("MODEL_JOB_HUNTER", MODELS["hermes_70b"]),
}
