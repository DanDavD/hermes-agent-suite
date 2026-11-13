import {
  ChatMessage,
  ChatSession,
  FileAttachment,
  ProjectItem,
  ScannedFileItem,
  TelemetryData,
  WorkspaceScanResult,
  WorkflowModeId,
} from "./types";

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765"
    : "http://127.0.0.1:8765";

const LOCAL_PROJECTS_KEY = "hermes_studio_projects_v2";
const LOCAL_SESSION_PROJECT_MAP_KEY = "hermes_studio_session_projects_v2";

function getLocalSessionProjectMap(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(
      window.localStorage.getItem(LOCAL_SESSION_PROJECT_MAP_KEY) || "{}"
    );
  } catch {
    return {};
  }
}

export function setLocalSessionProject(
  sessionId: string,
  projectId: string | null
) {
  if (typeof window === "undefined" || !sessionId) return;
  try {
    const map = getLocalSessionProjectMap();
    if (projectId) {
      map[sessionId] = projectId;
    } else {
      delete map[sessionId];
    }
    window.localStorage.setItem(
      LOCAL_SESSION_PROJECT_MAP_KEY,
      JSON.stringify(map)
    );
  } catch {
    // ignore storage errors
  }
}

function getFallbackProjects(): ProjectItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LOCAL_PROJECTS_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveFallbackProjects(projects: ProjectItem[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LOCAL_PROJECTS_KEY, JSON.stringify(projects));
  } catch {
    // ignore
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
    });
    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        errText = errJson.detail || errJson.error || errJson.message || errText;
      } catch {
        // ignore JSON parse error
      }
      throw new Error(errText);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (
      typeof window !== "undefined" &&
      url.startsWith("http://127.0.0.1:8765")
    ) {
      const fallbackRes = await fetch(path, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options?.headers || {}),
        },
      });
      if (!fallbackRes.ok) {
        let errText = `HTTP ${fallbackRes.status}`;
        try {
          const errJson = await fallbackRes.json();
          errText =
            errJson.detail || errJson.error || errJson.message || errText;
        } catch {
          // ignore
        }
        throw new Error(errText);
      }
      return (await fallbackRes.json()) as T;
    }
    throw err;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeProject(raw: any): ProjectItem {
  return {
    id: raw.id,
    name: raw.name || raw.title || "Untitled Project",
    description: raw.description || "",
    workspace_path: raw.workspace_path || raw.folder_path || "",
    created_at: raw.created_at || new Date().toISOString(),
    updated_at: raw.updated_at || new Date().toISOString(),
    session_count: raw.session_count ?? 0,
  };
}

export async function fetchProjects(): Promise<ProjectItem[]> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = await apiFetch<any>("/api/projects");
    const list = Array.isArray(data) ? data : data.projects || [];
    const normalized = list.map(normalizeProject);
    saveFallbackProjects(normalized);
    return normalized;
  } catch {
    return getFallbackProjects();
  }
}

export async function createProject(params: {
  name: string;
  workspace_path?: string;
  description?: string;
}): Promise<ProjectItem> {
  const cleanName = params.name.trim() || "New Project";
  const cleanPath = (params.workspace_path || "").trim();
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = await apiFetch<any>("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: cleanName,
        title: cleanName,
        workspace_path: cleanPath,
        folder_path: cleanPath,
        description: params.description || "",
      }),
    });
    const created = normalizeProject(data.project || data);
    const existing = getFallbackProjects().filter((p) => p.id !== created.id);
    saveFallbackProjects([created, ...existing]);
    return created;
  } catch {
    const now = new Date().toISOString();
    const localProj: ProjectItem = {
      id: `proj-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: cleanName,
      description: params.description || "",
      workspace_path: cleanPath,
      created_at: now,
      updated_at: now,
      session_count: 0,
    };
    const next = [localProj, ...getFallbackProjects()];
    saveFallbackProjects(next);
    return localProj;
  }
}

export async function updateProjectById(
  projectId: string,
  params: {
    name?: string;
    workspace_path?: string;
    description?: string;
  }
): Promise<ProjectItem> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = await apiFetch<any>(
      `/api/projects/${encodeURIComponent(projectId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          name: params.name,
          title: params.name,
          workspace_path: params.workspace_path,
          folder_path: params.workspace_path,
          description: params.description,
        }),
      }
    );
    const updated = normalizeProject(data.project || data);
    const list = getFallbackProjects().map((p) =>
      p.id === projectId ? updated : p
    );
    saveFallbackProjects(list);
    return updated;
  } catch {
    const list = getFallbackProjects();
    const now = new Date().toISOString();
    let updatedItem: ProjectItem | null = null;
    const next = list.map((p) => {
      if (p.id === projectId) {
        updatedItem = {
          ...p,
          name: params.name !== undefined ? params.name : p.name,
          workspace_path:
            params.workspace_path !== undefined
              ? params.workspace_path
              : p.workspace_path,
          description:
            params.description !== undefined
              ? params.description
              : p.description,
          updated_at: now,
        };
        return updatedItem;
      }
      return p;
    });
    saveFallbackProjects(next);
    if (updatedItem) return updatedItem;
    throw new Error("Project not found");
  }
}

export async function deleteProjectById(projectId: string): Promise<void> {
  try {
    await apiFetch(`/api/projects/${encodeURIComponent(projectId)}`, {
      method: "DELETE",
    });
  } catch {
    // fallback to local removal
  }
  const next = getFallbackProjects().filter((p) => p.id !== projectId);
  saveFallbackProjects(next);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeMessage(raw: any): ChatMessage {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const steps = Array.isArray(raw.agent_steps)
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      raw.agent_steps.map((s: any, idx: number) => ({
        step: s.step ?? idx + 1,
        agent: s.agent || s.role || `Agent ${idx + 1}`,
        role: s.role || s.agent || "",
        model: s.model || "nousresearch/hermes-3-llama-3.1-70b",
        status: (s.status || "complete").toLowerCase(),
        content: s.output || s.content || "",
        output: s.output || s.content || "",
        tokens: s.tokens_used || s.tokens || 0,
      }))
    : [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const attachments: FileAttachment[] = Array.isArray(raw.attachments)
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      raw.attachments.map((a: any, idx: number) => ({
        id: a.id || `att-${idx}`,
        name: a.filename || a.name || "attachment",
        type: (a.content_type || "").startsWith("image/") ? "image" : "code",
        extension: (a.filename || a.name || "").split(".").pop() || "txt",
        sizeBytes: a.size || a.sizeBytes || (a.content ? a.content.length : 0),
        content: a.content || "",
        previewUrl: (a.content_type || "").startsWith("image/")
          ? a.content
          : undefined,
      }))
    : [];

  return {
    id: raw.id || `msg-${Date.now()}-${Math.random()}`,
    role: raw.role || "assistant",
    content: raw.content || raw.response || "",
    timestamp: raw.created_at || raw.timestamp || new Date().toISOString(),
    mode: raw.agent_badge || raw.mode || "",
    model: raw.agent_badge || raw.model || "",
    agent_steps: steps,
    actions_executed: raw.actions_executed || [],
    attachments,
    tokens_used: raw.tokens_used || 0,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeSession(raw: any): ChatSession {
  const messages = Array.isArray(raw.messages)
    ? raw.messages.map(normalizeMessage)
    : [];
  const localMap = getLocalSessionProjectMap();
  return {
    id: raw.id,
    title: raw.title || "Untitled Session",
    mode: (raw.mode as WorkflowModeId) || "team:dev-squad",
    project_id: raw.project_id || localMap[raw.id] || null,
    created_at: raw.created_at || new Date().toISOString(),
    updated_at: raw.updated_at || new Date().toISOString(),
    workspace_path: raw.workspace_path || "",
    message_count: raw.message_count ?? messages.length,
    messages,
  };
}

export async function fetchSessions(
  projectId?: string | null
): Promise<ChatSession[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>(`/api/sessions${query}`);
  const list = Array.isArray(data) ? data : data.sessions || [];
  return list.map(normalizeSession);
}

export async function fetchSessionById(sessionId: string): Promise<ChatSession> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>(
    `/api/sessions/${encodeURIComponent(sessionId)}`
  );
  return normalizeSession(data.session || data);
}

export async function createNewSession(params: {
  title?: string;
  mode?: string;
  workspace_path?: string;
  project_id?: string | null;
}): Promise<ChatSession> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      title: params.title || "New Chat",
      mode: params.mode || "team:dev-squad",
      workspace_path: params.workspace_path || "",
      project_id: params.project_id || null,
    }),
  });
  const created = normalizeSession(data.session || data);
  if (params.project_id) {
    setLocalSessionProject(created.id, params.project_id);
    created.project_id = params.project_id;
  }
  return created;
}

export async function updateSessionById(
  sessionId: string,
  params: {
    title?: string;
    mode?: string;
    workspace_path?: string;
    project_id?: string | null;
  }
): Promise<ChatSession> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>(
    `/api/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(params),
    }
  );
  if (params.project_id !== undefined) {
    setLocalSessionProject(sessionId, params.project_id);
  }
  return normalizeSession(data.session || data);
}

export async function deleteSessionById(sessionId: string): Promise<void> {
  await apiFetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  setLocalSessionProject(sessionId, null);
}

export async function sendChatMessage(params: {
  session_id: string;
  prompt: string;
  mode: WorkflowModeId | string;
  workspace_path?: string;
  include_workspace?: boolean;
  selected_files?: string[];
  attachments?: FileAttachment[];
  temperature?: number;
  max_tokens?: number;
}): Promise<{
  session_id: string;
  session_title?: string;
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
  workspaceFilesInjected: string[];
  workspaceTokensInjected: number;
  actionsExecuted: any[];
}> {
  const payload = {
    session_id: params.session_id,
    mode: params.mode,
    prompt: params.prompt,
    message: params.prompt,
    workspace_path: params.include_workspace ? params.workspace_path || "" : "",
    selected_files: params.include_workspace ? params.selected_files : undefined,
    attachments: (params.attachments || []).map((att) => ({
      filename: att.name,
      content: att.content,
      content_type:
        att.type === "image"
          ? `image/${att.extension === "jpg" ? "jpeg" : att.extension}`
          : "text/plain",
      size: att.sizeBytes,
    })),
    temperature: params.temperature,
    max_tokens: params.max_tokens,
    stream: false,
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const normalizedUserMsg = data.user_message
    ? normalizeMessage(data.user_message)
    : null;

  const userMessage: ChatMessage = normalizedUserMsg
    ? {
        ...normalizedUserMsg,
        attachments:
          params.attachments && params.attachments.length > 0
            ? params.attachments
            : normalizedUserMsg.attachments,
        WorkspaceContextUsed: Boolean(
          params.include_workspace && params.workspace_path
        ),
      }
    : {
        id: `user-${Date.now()}`,
        role: "user" as const,
        content: params.prompt,
        timestamp: new Date().toISOString(),
        attachments: params.attachments,
        WorkspaceContextUsed: Boolean(
          params.include_workspace && params.workspace_path
        ),
      };

  const assistantMessage = data.assistant_message
    ? normalizeMessage(data.assistant_message)
    : normalizeMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.response || data.content || "",
        agent_badge: data.agent_badge || params.mode,
        agent_steps: data.agent_steps || [],
        tokens_used: data.tokens_used || 0,
        created_at: new Date().toISOString(),
      });

  return {
    session_id: data.session_id || params.session_id,
    session_title: data.session_title,
    userMessage,
    assistantMessage: {
      ...assistantMessage,
      actions_executed: data.actions_executed || assistantMessage.actions_executed || [],
    },
    workspaceFilesInjected: data.workspace_files_injected || [],
    workspaceTokensInjected: data.workspace_tokens_injected || 0,
    actionsExecuted: data.actions_executed || [],
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeWorkspaceScanPayload(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any,
  fallbackPath: string,
  selectedFiles?: string[]
): WorkspaceScanResult {
  if (data.valid === false && data.error) {
    throw new Error(data.error);
  }

  const resolvedPath: string =
    data.workspace_path || data.folder_path || fallbackPath;
  const parts = resolvedPath.replace(/\/+$/, "").split("/");
  const projectName = parts[parts.length - 1] || resolvedPath;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const files: ScannedFileItem[] = Array.isArray(data.files)
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      data.files.map((f: any) => ({
        path: f.path || f.relative_path,
        relative_path: f.relative_path || f.name,
        name: f.name || (f.relative_path || "").split("/").pop() || "file",
        extension: f.extension || "",
        size_bytes: f.size ?? f.size_bytes ?? 0,
        tokens: f.estimated_tokens ?? f.tokens ?? 0,
        included: selectedFiles ? selectedFiles.includes(f.relative_path) : true,
        category: f.language || f.extension || "code",
      }))
    : [];

  return {
    path: resolvedPath,
    project_name: data.project_name || projectName,
    is_unity_project:
      Boolean(data.is_unity_project) ||
      String(data.project_type || "")
        .toLowerCase()
        .includes("unity") ||
      files.some((f) => f.extension === ".cs" || f.extension === ".shader"),
    total_files: data.total_files ?? files.length,
    included_files: files.filter((f) => f.included).length,
    total_tokens:
      data.capped_tokens ??
      data.total_estimated_tokens ??
      files.reduce((acc, f) => acc + f.tokens, 0),
    token_budget: data.token_budget ?? 45000,
    files,
    pruned_dirs: data.pruned_dirs || [],
    summary: data.project_type || "Local Project Workspace",
  };
}

export async function scanWorkspaceDirectory(
  folderPath: string,
  selectedFiles?: string[]
): Promise<WorkspaceScanResult> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/workspace/scan", {
    method: "POST",
    body: JSON.stringify({
      folder_path: folderPath,
      workspace_path: folderPath,
      selected_files: selectedFiles,
      include_context: false,
    }),
  });

  return normalizeWorkspaceScanPayload(data, folderPath, selectedFiles);
}

export async function pickFolderInFinder(): Promise<{
  cancelled: boolean;
  folder_path: string;
  scan: WorkspaceScanResult | null;
}> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/workspace/pick-folder", {
    method: "POST",
  });

  if (data.cancelled || !data.folder_path) {
    return {
      cancelled: true,
      folder_path: "",
      scan: null,
    };
  }

  const scan = data.scan
    ? normalizeWorkspaceScanPayload(data.scan, data.folder_path)
    : await scanWorkspaceDirectory(data.folder_path);

  return {
    cancelled: false,
    folder_path: data.folder_path,
    scan,
  };
}

export async function applyCodeToWorkspace(params: {
  workspace_path: string;
  relative_path: string;
  content: string;
}): Promise<{
  success: boolean;
  full_path: string;
  relative_path: string;
  bytes_written: number;
  message: string;
}> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/workspace/apply", {
    method: "POST",
    body: JSON.stringify({
      folder_path: params.workspace_path,
      workspace_path: params.workspace_path,
      relative_path: params.relative_path,
      file_path: params.relative_path,
      content: params.content,
    }),
  });
  return {
    success: Boolean(data.success ?? true),
    full_path:
      data.full_path || `${params.workspace_path}/${params.relative_path}`,
    relative_path: data.relative_path || params.relative_path,
    bytes_written: data.bytes_written ?? params.content.length,
    message: data.message || `Saved ${params.relative_path}`,
  };
}

export async function fetchTelemetry(): Promise<TelemetryData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await apiFetch<any>("/api/telemetry");
  const localStats = data.local_stats || {};
  const settings = data.settings || {};

  return {
    api_key_configured: Boolean(data.api_key_configured),
    api_key_masked: data.api_key_masked || "",
    remaining_credits:
      typeof data.remaining_usd === "number"
        ? data.remaining_usd
        : typeof data.remaining_credits === "number"
          ? data.remaining_credits
          : typeof data.total_credits_usd === "number" &&
              typeof data.total_usage_usd === "number"
            ? Math.max(0, data.total_credits_usd - data.total_usage_usd)
            : null,
    total_usage:
      typeof data.total_usage_usd === "number"
        ? data.total_usage_usd
        : typeof data.usage_usd === "number"
          ? data.usage_usd
          : 0,
    limit:
      typeof data.limit_usd === "number"
        ? data.limit_usd
        : typeof data.total_credits_usd === "number"
          ? data.total_credits_usd
          : null,
    is_free_tier: Boolean(data.is_free_tier),
    total_sessions: localStats.total_sessions ?? data.total_sessions ?? 0,
    total_messages: localStats.total_messages ?? data.total_messages ?? 0,
    total_tokens_used:
      localStats.total_tokens_used ?? data.total_tokens_used ?? 0,
    temperature: settings.temperature ?? data.temperature ?? 0.2,
    max_tokens: settings.max_tokens ?? data.max_tokens ?? 4096,
    status_message: data.key_status || "Connected",
  };
}

export async function updateRuntimeSettings(params: {
  openrouter_api_key?: string;
  temperature?: number;
  max_tokens?: number;
}): Promise<TelemetryData> {
  await apiFetch("/api/settings", {
    method: "POST",
    body: JSON.stringify(params),
  });
  return fetchTelemetry();
}
