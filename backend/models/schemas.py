"""Pydantic v2 schemas for Hermes Studio v2 API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class AttachmentItem(BaseModel):
    """Represents a file or snippet attached to a chat message."""

    filename: str = Field(..., description="File name of the attachment")
    content: str = Field(default="", description="Text or base64 content of the attachment")
    content_type: Optional[str] = Field(default="text/plain", description="MIME type or format")
    size: Optional[int] = Field(default=None, description="File size in bytes")

    @model_validator(mode="before")
    @classmethod
    def normalize_attachment(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" in data and "filename" not in data:
                data["filename"] = data["name"]
            if "text" in data and "content" not in data:
                data["content"] = data["text"]
        return data


class AgentStep(BaseModel):
    """Represents a single execution step in a multi-agent or tool pipeline."""

    step: int
    agent: str
    model: str
    status: str = "Complete"
    output: Optional[str] = None
    tokens_used: int = 0


class MessageResponse(BaseModel):
    """Stored chat message with metadata and agent execution steps."""

    id: str
    session_id: str
    role: str
    content: str
    agent_badge: str = ""
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    attachments_json: str = "[]"
    agent_steps: List[AgentStep] = Field(default_factory=list)
    tokens_used: int = 0
    created_at: str


# =============================================================================
# PROJECT SCHEMAS
# =============================================================================


class ProjectCreate(BaseModel):
    """Request payload to create a new Claude-style Project."""

    name: str
    description: Optional[str] = ""
    workspace_path: Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_project_create(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "folder_path" in data and "workspace_path" not in data:
                data["workspace_path"] = data["folder_path"]
        return data


class ProjectUpdate(BaseModel):
    """Request payload to update an existing Project."""

    name: Optional[str] = None
    description: Optional[str] = None
    workspace_path: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_project_update(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "folder_path" in data and "workspace_path" not in data:
                data["workspace_path"] = data["folder_path"]
        return data


class ProjectSchema(BaseModel):
    """Response schema for a Project."""

    id: str
    name: str
    description: str = ""
    workspace_path: str = ""
    session_count: int = 0
    created_at: str
    updated_at: str


# Backwards/alias names
ProjectCreateRequest = ProjectCreate
ProjectUpdateRequest = ProjectUpdate
ProjectResponse = ProjectSchema


# =============================================================================
# SESSION SCHEMAS
# =============================================================================


class SessionCreateRequest(BaseModel):
    """Request payload to create a new session."""

    title: Optional[str] = "New Session"
    mode: Optional[str] = "team:dev-squad"
    workspace_path: Optional[str] = ""
    project_id: Optional[str] = ""


class SessionUpdateRequest(BaseModel):
    """Request payload to update an existing session."""

    title: Optional[str] = None
    mode: Optional[str] = None
    workspace_path: Optional[str] = None
    project_id: Optional[str] = None


class SessionSummary(BaseModel):
    """Lightweight session summary for sidebar listings."""

    id: str
    title: str
    mode: str
    workspace_path: str = ""
    project_id: Optional[str] = ""
    created_at: str
    updated_at: str
    message_count: int = 0
    total_tokens: int = 0


class SessionDetailResponse(SessionSummary):
    """Full session detail including ordered conversation history."""

    messages: List[MessageResponse] = Field(default_factory=list)


# Aliases requested by spec
SessionCreate = SessionCreateRequest
SessionUpdate = SessionUpdateRequest
SessionDetail = SessionDetailResponse


# =============================================================================
# CHAT & WORKSPACE SCHEMAS
# =============================================================================


class ChatRequest(BaseModel):
    """Request payload for executing an agent workflow or raw LLM completion."""

    session_id: Optional[str] = None
    project_id: Optional[str] = ""
    mode: str = "team:dev-squad"
    prompt: str
    workspace_path: Optional[str] = None
    selected_files: Optional[List[str]] = None
    attachments: Optional[List[AttachmentItem]] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    sub_mode: Optional[str] = None
    stream: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_chat_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "message" in data and "prompt" not in data:
                data["prompt"] = data["message"]
            if "content" in data and "prompt" not in data:
                data["prompt"] = data["content"]
            if "folder_path" in data and "workspace_path" not in data:
                data["workspace_path"] = data["folder_path"]
        return data


class ChatResponse(BaseModel):
    """Response payload from POST /api/chat."""

    session_id: str
    session_title: Optional[str] = None
    project_id: Optional[str] = ""
    mode: str
    agent_badge: str
    response: str
    content: str
    user_message: MessageResponse
    assistant_message: MessageResponse
    agent_steps: List[AgentStep] = Field(default_factory=list)
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    workspace_files_injected: List[str] = Field(default_factory=list)
    workspace_tokens_injected: int = 0


class WorkspaceFileNode(BaseModel):
    """Metadata for a single indexed file inside a scanned workspace."""

    path: str
    relative_path: str
    name: str
    extension: str
    size: int
    language: str
    estimated_tokens: int


class WorkspaceScanRequest(BaseModel):
    """Request payload to scan a local macOS directory."""

    folder_path: str
    selected_files: Optional[List[str]] = None
    include_context: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_folder_path(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "workspace_path" in data and "folder_path" not in data:
                data["folder_path"] = data["workspace_path"]
            elif "path" in data and "folder_path" not in data:
                data["folder_path"] = data["path"]
        return data


class WorkspaceScanResponse(BaseModel):
    """Response payload describing a scanned local workspace."""

    folder_path: str
    workspace_path: str
    valid: bool
    error: Optional[str] = None
    project_type: str = "General Workspace"
    total_files: int = 0
    total_size_bytes: int = 0
    total_estimated_tokens: int = 0
    capped_tokens: int = 0
    token_budget: int = 45000
    files: List[WorkspaceFileNode] = Field(default_factory=list)
    language_breakdown: Dict[str, int] = Field(default_factory=dict)
    pruned_dirs: List[str] = Field(default_factory=list)
    context_preview: Optional[str] = None


class WorkspaceWriteFileRequest(BaseModel):
    """Request payload to safely write or update a file inside a workspace."""

    folder_path: str
    relative_path: str
    content: str

    @model_validator(mode="before")
    @classmethod
    def normalize_write_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "workspace_path" in data and "folder_path" not in data:
                data["folder_path"] = data["workspace_path"]
            if "file_path" in data and "relative_path" not in data:
                data["relative_path"] = data["file_path"]
            elif "path" in data and "relative_path" not in data:
                data["relative_path"] = data["path"]
        return data


class WorkspaceWriteFileResponse(BaseModel):
    """Response payload after writing a generated file to the workspace."""

    success: bool
    folder_path: str
    relative_path: str
    full_path: str
    bytes_written: int
    message: str


class SettingsUpdateRequest(BaseModel):
    """Request payload to update runtime API key and generation parameters."""

    openrouter_api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_settings_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "api_key" in data and "openrouter_api_key" not in data:
                data["openrouter_api_key"] = data["api_key"]
        return data


class TelemetryResponse(BaseModel):
    """Combined OpenRouter credit/key telemetry and local SQLite statistics."""

    api_key_configured: bool
    api_key_masked: str
    key_status: str
    label: Optional[str] = None
    usage_usd: float = 0.0
    limit_usd: Optional[float] = None
    remaining_usd: Optional[float] = None
    total_credits_usd: Optional[float] = None
    total_usage_usd: Optional[float] = None
    is_free_tier: bool = False
    rate_limit: Optional[Dict[str, Any]] = None
    local_stats: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
