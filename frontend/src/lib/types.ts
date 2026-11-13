export type WorkflowModeId =
  | "team:dev-squad"
  | "team:career-hunter"
  | "team:content-video"
  | "raw:deepseek-v3"
  | "raw:qwen-coder-32b"
  | "raw:deepseek-r1"
  | "raw:gemini-pro"
  | "raw:gemini-flash"
  | "raw:hermes-70b"
  | "raw:claude-sonnet"
  | "raw:free-deepseek"
  | "raw:hermes-8b";

export interface ModelDirectoryItem {
  id: string;
  name: string;
  provider: string;
  powerRating: string;
  speedRating: string;
  costLabel: string;
  contextWindow: string;
  roleBadge: string;
  specializedFor: string[];
  description: string;
}

export interface WorkflowAgentRole {
  role: string;
  model: string;
}

export interface WorkflowModeOption {
  id: WorkflowModeId;
  name: string;
  shortLabel: string;
  badge: string;
  category: "team" | "raw";
  description: string;
  modelId?: string;
  agents?: WorkflowAgentRole[];
}

export interface ProjectItem {
  id: string;
  name: string;
  description?: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
  session_count?: number;
}

export interface AgentThoughtStep {
  step?: number;
  agent: string;
  role?: string;
  model: string;
  status: "running" | "complete" | "completed" | "error";
  content: string;
  output?: string;
  duration_ms?: number;
  tokens?: number;
}

export interface AutonomousActionItem {
  type: string;
  path?: string;
  full_path?: string;
  bytes?: number;
  status: string;
  details?: string;
  summary?: string;
  runner?: string;
}

export interface FileAttachment {
  id: string;
  name: string;
  type: "code" | "image" | "text";
  extension: string;
  sizeBytes: number;
  content: string;
  previewUrl?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  mode?: WorkflowModeId | string;
  model?: string;
  agent_steps?: AgentThoughtStep[];
  actions_executed?: AutonomousActionItem[];
  attachments?: FileAttachment[];
  tokens_used?: number;
  WorkspaceContextUsed?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  mode: WorkflowModeId | string;
  project_id?: string | null;
  created_at: string;
  updated_at: string;
  workspace_path?: string | null;
  message_count?: number;
  messages: ChatMessage[];
}

export interface ScannedFileItem {
  path: string;
  relative_path: string;
  name: string;
  extension: string;
  size_bytes: number;
  tokens: number;
  included: boolean;
  category?: string;
}

export interface WorkspaceScanResult {
  path: string;
  project_name: string;
  is_unity_project: boolean;
  total_files: number;
  included_files: number;
  total_tokens: number;
  token_budget: number;
  files: ScannedFileItem[];
  pruned_dirs?: string[];
  summary?: string;
}

export interface TelemetryData {
  api_key_configured: boolean;
  api_key_masked: string;
  remaining_credits: number | null;
  total_usage: number;
  limit: number | null;
  is_free_tier: boolean;
  total_sessions: number;
  total_messages: number;
  total_tokens_used: number;
  temperature: number;
  max_tokens: number;
  status_message?: string;
}
