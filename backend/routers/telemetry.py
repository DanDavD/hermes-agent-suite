"""OpenRouter Credit Telemetry & Runtime Settings Router (/api/telemetry, /api/settings)."""

from typing import Any, Dict, List
from fastapi import APIRouter

from backend.config import AVAILABLE_MODES, runtime_settings
from backend.database import get_telemetry_stats
from backend.models.schemas import SettingsUpdateRequest, TelemetryResponse
from backend.services.openrouter_client import fetch_openrouter_telemetry

router = APIRouter(prefix="/api", tags=["telemetry", "settings"])


@router.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry() -> Dict[str, Any]:
    """
    Queries OpenRouter (/api/v1/auth/key & /api/v1/credits) for live credit balance,
    total usage, and key status, combined with local SQLite session/token metrics.
    """
    openrouter_data = await fetch_openrouter_telemetry()
    local_stats = get_telemetry_stats()
    settings_dict = runtime_settings.to_dict()

    remaining_val = openrouter_data.get("remaining_usd")
    total_usage_val = (
        openrouter_data.get("total_usage_usd")
        if openrouter_data.get("total_usage_usd") is not None
        else openrouter_data.get("usage_usd", 0.0)
    )
    limit_val = (
        openrouter_data.get("limit_usd")
        if openrouter_data.get("limit_usd") is not None
        else openrouter_data.get("total_credits_usd")
    )

    return {
        **openrouter_data,
        "status_message": openrouter_data.get("key_status", "Connected"),
        "remaining_credits": remaining_val,
        "total_usage": float(total_usage_val or 0.0),
        "limit": limit_val,
        "total_sessions": int(local_stats.get("total_sessions", 0)),
        "total_messages": int(local_stats.get("total_messages", 0)),
        "total_tokens_used": int(local_stats.get("total_tokens_used", 0)),
        "temperature": float(settings_dict.get("temperature", 0.2)),
        "max_tokens": int(settings_dict.get("max_tokens", 4096)),
        "local_stats": local_stats,
        "settings": settings_dict,
    }


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Returns current runtime settings (masked API key, temperature, max_tokens, modes)."""
    return runtime_settings.to_dict()


@router.post("/settings")
async def update_settings(payload: SettingsUpdateRequest) -> Dict[str, Any]:
    """
    Updates the OpenRouter API key, default temperature, and max_tokens in memory and .env,
    then returns refreshed settings and OpenRouter telemetry.
    """
    updated = runtime_settings.update(
        openrouter_api_key=payload.openrouter_api_key,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        persist_env=True,
    )
    openrouter_data = await fetch_openrouter_telemetry()
    local_stats = get_telemetry_stats()

    return {
        "success": True,
        "settings": updated,
        "telemetry": {
            **openrouter_data,
            "local_stats": local_stats,
            "settings": updated,
        },
    }


@router.get("/modes")
@router.get("/models")
async def get_available_modes() -> Dict[str, List[Dict[str, Any]]]:
    """Returns the catalog of all available agent squads and raw models."""
    return {"modes": AVAILABLE_MODES}
