"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import BottomComposer from "@/components/BottomComposer";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import AgentStepsAccordion from "@/components/AgentStepsAccordion";
import WorkspaceModal from "@/components/WorkspaceModal";
import SettingsTelemetryModal from "@/components/SettingsTelemetryModal";
import {
  ChatMessage,
  ChatSession,
  FileAttachment,
  ProjectItem,
  TelemetryData,
  WorkflowModeId,
  WorkspaceScanResult,
} from "@/lib/types";
import { WORKFLOW_MODES } from "@/lib/constants";
import {
  createNewSession,
  createProject,
  deleteProjectById,
  deleteSessionById,
  fetchProjects,
  fetchSessionById,
  fetchSessions,
  fetchTelemetry,
  pickFolderInFinder,
  scanWorkspaceDirectory,
  sendChatMessage,
  updateProjectById,
  updateRuntimeSettings,
  updateSessionById,
} from "@/lib/api";

const CLEVER_DEV_GREETINGS: string[] = [
  "What are we coding today, Daniel?",
  "Ready to discombobulate some bugs, Daniel?",
  "Hey Daniel, let's turn caffeine into clean architecture.",
  "Zero warnings, zero leaks. What are we building, Daniel?",
  "Ready to ship to production on a Friday, Daniel?",
  "Compilers are warmed up, Daniel. What's the plan?",
  "Hey Daniel, let's refactor something that already works.",
  "What's on the stack today, Daniel?",
  "Ready to discombobulate a complex algorithm, Daniel?",
  "It works on your machine, Daniel. Let's make it work everywhere.",
  "Hey Daniel, time to delete more lines of code than we write.",
  "No merge conflicts in sight, Daniel. Where do we start?",
  "Ready to make the frame rate go brrr, Daniel?",
  "What problem are we over-engineering today, Daniel?",
  "Hey Daniel, let's build something ridiculously fast.",
  "Pointers are aligned and caches are hot, Daniel.",
  "Ready to squash some Heisenbugs today, Daniel?",
  "Hey Daniel, what are we shipping before midnight?",
  "Git status is clean, Daniel. What's the next move?",
  "Ready to discombobulate legacy bottlenecks, Daniel?",
  "Hey Daniel, let's write code Future Daniel will thank us for.",
  "Segfaults fear you, Daniel. What are we architecting?",
  "What wild idea are we turning into a feature today, Daniel?",
  "Hey Daniel, ready for some O(1) magic?",
  "The terminal is yours, Daniel. What are we cooking?",
  "Ready to turn spaghetti into symphony, Daniel?",
  "Hey Daniel, let's make those benchmarks cry.",
  "Another day, another zero-allocation loop, Daniel.",
  "What's the mission today, Daniel? Backend, UI, or shaders?",
  "Hey Daniel, ready to discombobulate the status quo?",
  "Rubber duck mode disabled. Full architect mode ready, Daniel.",
  "What masterpiece are we pushing to main today, Daniel?",
  "Hey Daniel, let's automate the boring stuff and build the fun stuff.",
  "All threads synchronized, Daniel. Awaiting your command.",
  "Ready to shave some milliseconds off the render loop, Daniel?",
  "Hey Daniel, what are we prototyping right now?",
  "Clean types, pure functions, zero drama. Ready, Daniel?",
  "Let's turn a 3-hour debugging session into a 3-second fix, Daniel.",
  "Hey Daniel, ready to build something players won't put down?",
  "Syntax trees are blooming, Daniel. What are we writing?",
  "Ready to discombobulate some race conditions, Daniel?",
  "Hey Daniel, what's the architecture of the day?",
  "Memory is allocated and ready to roll, Daniel.",
  "Let's write code so clean it doesn't even need comments, Daniel.",
  "Hey Daniel, ready to deploy without breaking a sweat?",
  "From empty file to production-ready. Where do we begin, Daniel?",
  "Ready to discombobulate the impossible today, Daniel?",
  "Hey Daniel, let's craft some pixel-perfect UX.",
  "Stack overflow? Never heard of her. What's up, Daniel?",
  "Ready when you are, Daniel. What are we coding today?",
];

function selectFilesWithinBudget(scanRes: WorkspaceScanResult): {
  workspace: WorkspaceScanResult;
  selectedFiles: string[];
} {
  let runningTokens = 0;
  const defaultSelected: string[] = [];
  for (const f of scanRes.files) {
    if (runningTokens + f.tokens <= scanRes.token_budget) {
      defaultSelected.push(f.relative_path);
      runningTokens += f.tokens;
    }
  }
  return {
    workspace: {
      ...scanRes,
      included_files: defaultSelected.length,
      total_tokens: runningTokens,
    },
    selectedFiles: defaultSelected,
  };
}

export default function HermesWorkstationPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Greeting state (50 clever developer messages for Daniel)
  const [greetingIndex, setGreetingIndex] = useState<number>(0);
  const [greetingAnimKey, setGreetingAnimKey] = useState<number>(0);

  // Projects state
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  // Sessions & Messages state (starts in clean Draft state — nothing created in DB yet)
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeMode, setActiveMode] =
    useState<WorkflowModeId>("team:dev-squad");

  // Composer & Logic state
  const [prompt, setPrompt] = useState("");
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [includeWorkspace, setIncludeWorkspace] = useState(true);
  const [temperature, setTemperature] = useState<number>(0.2);
  const [maxTokens, setMaxTokens] = useState<number>(4096);
  const [isSending, setIsSending] = useState(false);
  const [liveThinkingStatus, setLiveThinkingStatus] = useState<string>(
    "Analyzing prompt & workspace context..."
  );
  const [showLiveTrace, setShowLiveTrace] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [toastBanner, setToastBanner] = useState<string | null>(null);

  // Workspace & Telemetry state
  const [workspace, setWorkspace] = useState<WorkspaceScanResult | null>(null);
  const [selectedWorkspaceFiles, setSelectedWorkspaceFiles] = useState<
    string[]
  >([]);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);

  // Modals state
  const [workspaceModalOpen, setWorkspaceModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const rotateGreeting = useCallback(() => {
    setGreetingIndex((prev) => {
      if (CLEVER_DEV_GREETINGS.length <= 1) return 0;
      let next = Math.floor(Math.random() * CLEVER_DEV_GREETINGS.length);
      if (next === prev) {
        next = (prev + 1) % CLEVER_DEV_GREETINGS.length;
      }
      return next;
    });
    setGreetingAnimKey((k) => k + 1);
  }, []);

  // Pick a random clever greeting on client mount
  useEffect(() => {
    setGreetingIndex(Math.floor(Math.random() * CLEVER_DEV_GREETINGS.length));
  }, []);

  // Antigravity-style dynamic Thinking status progression
  useEffect(() => {
    if (!isSending) return;
    const stages = [
      "Analyzing prompt & workspace context...",
      "Lead Architect planning system architecture...",
      "Code Maker generating production code...",
      "Auditing performance, memory safety, and edge cases...",
      "Executing autonomous workspace actions & tests...",
    ];
    let i = 0;
    setLiveThinkingStatus(stages[0]);
    const timer = setInterval(() => {
      i = (i + 1) % stages.length;
      setLiveThinkingStatus(stages[i]);
    }, 2200);
    return () => clearInterval(timer);
  }, [isSending]);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const syncWorkspaceFromPath = useCallback(async (folderPath: string) => {
    const clean = (folderPath || "").trim();
    if (!clean) {
      setWorkspace(null);
      setSelectedWorkspaceFiles([]);
      return;
    }
    try {
      const scanRes = await scanWorkspaceDirectory(clean);
      const { workspace: ws, selectedFiles } = selectFilesWithinBudget(scanRes);
      setWorkspace(ws);
      setSelectedWorkspaceFiles(selectedFiles);
      setIncludeWorkspace(true);
    } catch {
      // Leave workspace unlinked if path cannot be scanned
    }
  }, []);

  // Initial load: fetch existing projects, sessions & telemetry without creating any fake chat
  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      try {
        const [projList, sessList, telem] = await Promise.all([
          fetchProjects().catch(() => []),
          fetchSessions().catch(() => []),
          fetchTelemetry().catch(() => null),
        ]);

        if (!mounted) return;
        setProjects(projList);
        setSessions(sessList);
        if (telem) {
          setTelemetry(telem);
          if (typeof telem.temperature === "number") {
            setTemperature(telem.temperature);
          }
          if (typeof telem.max_tokens === "number") {
            setMaxTokens(telem.max_tokens);
          }
        }
      } catch {
        // Start cleanly in draft mode
      }
    }

    bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  // Native macOS window drag & zoom listener for titlebar elements
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const isInteractive = target.closest(
        "button, input, textarea, select, a, [data-no-drag]"
      );
      if (isInteractive) return;
      const isDrag =
        target.closest("[data-window-drag]") ||
        (e.clientY <= 44 && !isInteractive);
      if (isDrag) {
        const webkit = (
          window as unknown as {
            webkit?: {
              messageHandlers?: {
                windowDrag?: { postMessage: (msg: string) => void };
              };
            };
          }
        ).webkit;
        if (webkit?.messageHandlers?.windowDrag) {
          webkit.messageHandlers.windowDrag.postMessage("drag");
        }
      }
    };

    const handleDblClick = (e: MouseEvent) => {
      if (e.button !== 0) return;
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const isInteractive = target.closest(
        "button, input, textarea, select, a, [data-no-drag]"
      );
      if (isInteractive) return;
      const isDrag =
        target.closest("[data-window-drag]") ||
        (e.clientY <= 44 && !isInteractive);
      if (isDrag) {
        const webkit = (
          window as unknown as {
            webkit?: {
              messageHandlers?: {
                windowZoom?: { postMessage: (msg: string) => void };
              };
            };
          }
        ).webkit;
        if (webkit?.messageHandlers?.windowZoom) {
          webkit.messageHandlers.windowZoom.postMessage("zoom");
        }
      }
    };

    window.addEventListener("mousedown", handleMouseDown, true);
    window.addEventListener("dblclick", handleDblClick, true);
    return () => {
      window.removeEventListener("mousedown", handleMouseDown, true);
      window.removeEventListener("dblclick", handleDblClick, true);
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending, scrollToBottom]);

  const activeProject =
    projects.find((p) => p.id === activeProjectId) || null;

  const handleSelectSession = async (sessionId: string) => {
    setActiveSessionId(sessionId);
    setErrorBanner(null);
    try {
      const detail = await fetchSessionById(sessionId);
      setMessages(detail.messages || []);
      if (detail.mode) {
        setActiveMode(detail.mode as WorkflowModeId);
      }
      setActiveProjectId(detail.project_id || null);

      const proj = projects.find((p) => p.id === detail.project_id) || null;
      const targetPath = detail.workspace_path || proj?.workspace_path || "";
      if (targetPath) {
        if (targetPath !== workspace?.path) {
          await syncWorkspaceFromPath(targetPath);
        }
      } else {
        setWorkspace(null);
        setSelectedWorkspaceFiles([]);
      }
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to load session"
      );
    }
  };

  const handleSelectProject = async (project: ProjectItem | null) => {
    if (!project) {
      setActiveProjectId(null);
      return;
    }
    setActiveProjectId(project.id);
    if (project.workspace_path) {
      await syncWorkspaceFromPath(project.workspace_path);
    } else {
      setWorkspace(null);
      setSelectedWorkspaceFiles([]);
    }

    const matching = sessions.filter(
      (s) =>
        s.project_id === project.id ||
        (!s.project_id &&
          project.workspace_path &&
          s.workspace_path === project.workspace_path)
    );
    if (matching.length > 0) {
      handleSelectSession(matching[0].id);
    } else {
      // Enter clean draft view scoped to this project without creating a session yet
      setActiveSessionId("");
      setMessages([]);
      rotateGreeting();
    }
  };

  const handleCreateProjectInline = async (name: string) => {
    const created = await createProject({
      name,
      workspace_path: "",
    });
    setProjects((prev) => [created, ...prev]);
    setActiveProjectId(created.id);
    setActiveSessionId("");
    setMessages([]);
    rotateGreeting();
  };

  // Unified folder selection: picks folder in Finder and automatically creates/selects Project
  const handleSelectFolderAndEnsureProject = async () => {
    try {
      const picked = await pickFolderInFinder();
      if (picked.cancelled || !picked.folder_path || !picked.scan) return;

      const folderName =
        picked.scan.project_name ||
        picked.folder_path.split("/").pop() ||
        "New Project";

      const { workspace: ws, selectedFiles } = selectFilesWithinBudget(
        picked.scan
      );
      setWorkspace(ws);
      setSelectedWorkspaceFiles(selectedFiles);
      setIncludeWorkspace(true);

      // If an existing project already points to this folder, activate it; otherwise create it automatically
      let targetProject = projects.find(
        (p) => p.workspace_path === picked.folder_path
      );

      if (!targetProject) {
        targetProject = await createProject({
          name: folderName,
          workspace_path: picked.folder_path,
        });
        setProjects((prev) => [
          targetProject!,
          ...prev.filter((p) => p.id !== targetProject!.id),
        ]);
      }

      setActiveProjectId(targetProject.id);

      // If already inside an active persisted session, link the session to the project & folder
      if (activeSessionId) {
        updateSessionById(activeSessionId, {
          workspace_path: picked.folder_path,
          project_id: targetProject.id,
        })
          .then((updated) => {
            setSessions((prev) =>
              prev.map((s) => (s.id === updated.id ? updated : s))
            );
          })
          .catch(() => {});
      }
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to pick folder in Finder"
      );
    }
  };

  const handleLinkProjectFolderInFinder = async (project: ProjectItem) => {
    try {
      const picked = await pickFolderInFinder();
      if (picked.cancelled || !picked.folder_path || !picked.scan) return;

      const updated = await updateProjectById(project.id, {
        name: project.name,
        workspace_path: picked.folder_path,
      });
      setProjects((prev) =>
        prev.map((p) => (p.id === project.id ? updated : p))
      );
      setActiveProjectId(project.id);

      const { workspace: ws, selectedFiles } = selectFilesWithinBudget(
        picked.scan
      );
      setWorkspace(ws);
      setSelectedWorkspaceFiles(selectedFiles);
      setIncludeWorkspace(true);
      setToastBanner(`Linked ${picked.scan.project_name} to ${project.name}`);
      setTimeout(() => setToastBanner(null), 3000);
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to link folder in Finder"
      );
    }
  };

  const handleDeleteProject = async (
    projectId: string,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    await deleteProjectById(projectId);
    setProjects((prev) => prev.filter((p) => p.id !== projectId));
    if (activeProjectId === projectId) {
      setActiveProjectId(null);
      setWorkspace(null);
      setSelectedWorkspaceFiles([]);
    }
  };

  // Clicking "+ New" only resets to a fresh Draft view with a new greeting (does NOT create a DB session yet)
  const handleCreateLooseSession = useCallback(() => {
    setErrorBanner(null);
    setActiveSessionId("");
    setActiveProjectId(null);
    setWorkspace(null);
    setSelectedWorkspaceFiles([]);
    setMessages([]);
    setPrompt("");
    setAttachments([]);
    rotateGreeting();
  }, [rotateGreeting]);

  // Keyboard shortcut: Cmd+B / Ctrl+B to toggle sidebar, Cmd+N to open fresh draft view
  useEffect(() => {
    const handleGlobalShortcuts = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarCollapsed((prev) => !prev);
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        handleCreateLooseSession();
      }
    };
    window.addEventListener("keydown", handleGlobalShortcuts);
    return () => window.removeEventListener("keydown", handleGlobalShortcuts);
  }, [handleCreateLooseSession]);

  // Clicking "+" on a project prepares a fresh draft scoped to that project without creating a DB row until Send
  const handleCreateProjectSession = async (project: ProjectItem) => {
    setErrorBanner(null);
    setActiveSessionId("");
    setActiveProjectId(project.id);
    setMessages([]);
    setPrompt("");
    setAttachments([]);
    rotateGreeting();
    if (project.workspace_path) {
      await syncWorkspaceFromPath(project.workspace_path);
    } else {
      setWorkspace(null);
      setSelectedWorkspaceFiles([]);
    }
  };

  const handleDeleteSession = async (
    sessionId: string,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await deleteSessionById(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining.length > 0) {
          handleSelectSession(remaining[0].id);
        } else {
          handleCreateLooseSession();
        }
      }
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to delete chat"
      );
    }
  };

  const handleChangeTemperature = (val: number) => {
    setTemperature(val);
    updateRuntimeSettings({ temperature: val })
      .then((t) => setTelemetry(t))
      .catch(() => {});
  };

  const handleChangeMaxTokens = (val: number) => {
    setMaxTokens(val);
    updateRuntimeSettings({ max_tokens: val })
      .then((t) => setTelemetry(t))
      .catch(() => {});
  };

  const handleSend = async () => {
    const trimmed = prompt.trim();
    if (!trimmed && attachments.length === 0) return;
    if (isSending) return;

    setErrorBanner(null);
    const currentPrompt = trimmed || "Analyze the attached files.";
    const currentAttachments = [...attachments];

    const optimisticUserMsg: ChatMessage = {
      id: `temp-user-${Date.now()}`,
      role: "user",
      content: currentPrompt,
      timestamp: new Date().toISOString(),
      attachments: currentAttachments,
      WorkspaceContextUsed: Boolean(workspace && includeWorkspace),
    };

    setMessages((prev) => [...prev, optimisticUserMsg]);
    setPrompt("");
    setAttachments([]);
    setIsSending(true);

    try {
      let targetSessionId = activeSessionId;
      if (!targetSessionId) {
        const created = await createNewSession({
          title: currentPrompt.slice(0, 48),
          mode: activeMode,
          workspace_path: workspace?.path || "",
          project_id: activeProjectId,
        });
        targetSessionId = created.id;
        setActiveSessionId(created.id);
        setSessions((prev) => [created, ...prev]);
      }

      const result = await sendChatMessage({
        session_id: targetSessionId,
        prompt: currentPrompt,
        mode: activeMode,
        workspace_path: workspace?.path,
        include_workspace: Boolean(workspace && includeWorkspace),
        selected_files:
          workspace && includeWorkspace ? selectedWorkspaceFiles : undefined,
        attachments: currentAttachments,
        temperature,
        max_tokens: maxTokens,
      });

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUserMsg.id),
        result.userMessage,
        result.assistantMessage,
      ]);

      // Smart dynamic title renaming (Requirement 4)
      if (result.session_title) {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === targetSessionId ? { ...s, title: result.session_title! } : s
          )
        );
      }

      // Autonomous actions feedback toast (Requirement 2)
      if (result.actionsExecuted && result.actionsExecuted.length > 0) {
        const filesCount = result.actionsExecuted.filter(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (a: any) => a.type === "file_written"
        ).length;
        const testAction = result.actionsExecuted.find(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (a: any) => a.type === "test_run"
        );
        let msg = "";
        if (filesCount > 0) {
          msg += `⚡ Auto-applied ${filesCount} file(s) to workspace. `;
        }
        if (testAction) {
          msg += `🧪 ${testAction.details || testAction.summary}`;
        }
        if (msg) {
          setToastBanner(msg);
          setTimeout(() => setToastBanner(null), 5000);
        }
        if (workspace?.path) {
          syncWorkspaceFromPath(workspace.path);
        }
      }

      fetchSessions()
        .then((list) => setSessions(list))
        .catch(() => {});
      fetchProjects()
        .then((list) => setProjects(list))
        .catch(() => {});
      fetchTelemetry()
        .then((t) => setTelemetry(t))
        .catch(() => {});
    } catch (err) {
      setErrorBanner(
        err instanceof Error
          ? err.message
          : "Request failed. Verify backend is running."
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleFileApplied = async (relativePath: string) => {
    setToastBanner(`Saved ${relativePath} directly to active workspace.`);
    setTimeout(() => setToastBanner(null), 3500);
    if (workspace) {
      try {
        const refreshed = await scanWorkspaceDirectory(
          workspace.path,
          selectedWorkspaceFiles
        );
        setWorkspace(refreshed);
      } catch {
        // ignore
      }
    }
  };

  const activeWorkflowMeta =
    WORKFLOW_MODES.find((m) => m.id === activeMode) || WORKFLOW_MODES[0];

  const currentSessionObj = sessions.find((s) => s.id === activeSessionId);
  const currentGreeting =
    CLEVER_DEV_GREETINGS[greetingIndex] || CLEVER_DEV_GREETINGS[0];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#141414] text-zinc-100">
      {/* Left Collapsible Sidebar (Claude Desktop Structure) */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        projects={projects}
        activeProjectId={activeProjectId}
        onSelectProject={handleSelectProject}
        onCreateProjectInline={handleCreateProjectInline}
        onCreateProjectFromFinder={handleSelectFolderAndEnsureProject}
        onLinkProjectFolderInFinder={handleLinkProjectFolderInFinder}
        onDeleteProject={handleDeleteProject}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onCreateLooseSession={handleCreateLooseSession}
        onCreateProjectSession={handleCreateProjectSession}
        onDeleteSession={handleDeleteSession}
        telemetry={telemetry}
        onOpenSettingsModal={() => setSettingsModalOpen(true)}
      />

      {/* Main Central Workstation Column */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden bg-[#141414]">
        {/* Top Header Bar */}
        <TopBar
          sidebarCollapsed={sidebarCollapsed}
          onExpandSidebar={() => setSidebarCollapsed(false)}
          sessionTitle={currentSessionObj?.title || "New Chat"}
          projectName={activeProject?.name || null}
        />

        {/* Floating Neutral Toast / Error Banners */}
        {toastBanner && (
          <div className="mx-auto mt-3 px-4 py-1.5 rounded-lg bg-[#262626] border border-zinc-700 text-zinc-200 text-xs font-mono shadow-lg z-30">
            {toastBanner}
          </div>
        )}

        {errorBanner && (
          <div className="mx-4 mt-3 px-4 py-2 rounded-lg bg-[#1F1F1F] border border-zinc-800 text-rose-300 text-xs flex items-center justify-between gap-3">
            <span>{errorBanner}</span>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="text-xs underline text-zinc-400 hover:text-zinc-200"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Central Scrollable Chat Area */}
        <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 flex flex-col">
          {messages.length === 0 && !isSending ? (
            <div className="flex-1 flex flex-col items-center justify-center select-none pb-12">
              <div
                key={greetingAnimKey}
                className="max-w-2xl w-full text-center space-y-5 px-4"
              >
                {/* Minimalist Animated Greeting for Daniel */}
                <h2 className="animate-hero-greeting text-2xl sm:text-[28px] font-normal tracking-tight text-zinc-100 leading-snug">
                  {currentGreeting}
                </h2>

                {/* Below greeting: Select Folder button (automatically creates/selects Project) */}
                <div className="animate-hero-sub flex items-center justify-center pt-1">
                  {workspace ? (
                    <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#1C1C1C] border border-zinc-800 text-xs text-zinc-300 shadow-sm">
                      <button
                        type="button"
                        onClick={handleSelectFolderAndEnsureProject}
                        className="inline-flex items-center gap-2 hover:text-white transition-colors"
                        title="Change project folder in Finder"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="text-zinc-400"
                        >
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                        </svg>
                        <span className="font-medium text-zinc-200">
                          {activeProject?.name || workspace.project_name}
                        </span>
                        <span className="text-[11px] font-mono text-zinc-500">
                          {workspace.included_files} files
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setWorkspace(null);
                          setSelectedWorkspaceFiles([]);
                          setActiveProjectId(null);
                        }}
                        className="ml-1 text-zinc-500 hover:text-zinc-200 transition-colors"
                        title="Clear selected folder"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSelectFolderAndEnsureProject}
                      className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#1A1A1A] hover:bg-[#222222] border border-zinc-800/90 hover:border-zinc-700 text-xs text-zinc-400 hover:text-zinc-200 transition-all duration-200 shadow-sm group"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="text-zinc-500 group-hover:text-zinc-300 transition-colors"
                      >
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                      </svg>
                      <span>Select folder</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="w-full max-w-4xl mx-auto space-y-6 transition-all duration-200">
              {messages.map((msg) => {
                const isUser = msg.role === "user";

                return (
                  <div
                    key={msg.id}
                    className={`flex ${
                      isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`min-w-0 max-w-full ${
                        isUser
                          ? "w-auto max-w-[82%] rounded-2xl bg-[#262626] px-4 py-2.5 text-zinc-100"
                          : "w-full rounded-2xl bg-transparent px-1 py-1"
                      }`}
                    >
                      {/* Message Metadata Header */}
                      {!isUser && (
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-zinc-300">
                              Hermes Studio
                            </span>
                            {msg.mode && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#1F1F1F] text-zinc-400">
                                {msg.mode}
                              </span>
                            )}
                          </div>

                          {msg.tokens_used ? (
                            <span className="text-[10px] font-mono text-zinc-500">
                              {msg.tokens_used.toLocaleString()} tok
                            </span>
                          ) : null}
                        </div>
                      )}

                      {/* User Attachments Display */}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                          {msg.attachments.map((att, idx) => (
                            <div
                              key={att.id || idx}
                              className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#1A1A1A] border border-zinc-800 text-xs font-mono text-zinc-300"
                            >
                              {att.type === "image" && att.previewUrl ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img
                                  src={att.previewUrl}
                                  alt={att.name}
                                  className="w-6 h-6 rounded object-cover"
                                />
                              ) : null}
                              <span>{att.name}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Real-Time Step-by-Step Agent Thoughts Accordion */}
                      {!isUser &&
                        ((msg.agent_steps && msg.agent_steps.length > 0) ||
                          (msg.actions_executed &&
                            msg.actions_executed.length > 0)) && (
                          <AgentStepsAccordion
                            steps={msg.agent_steps}
                            actionsExecuted={msg.actions_executed}
                            workspacePath={workspace?.path}
                            onOpenWorkspaceModal={() =>
                              setWorkspaceModalOpen(true)
                            }
                            onFileApplied={handleFileApplied}
                          />
                        )}

                      {/* Message Markdown & Code Blocks */}
                      <MarkdownRenderer
                        content={msg.content}
                        workspacePath={workspace?.path}
                        onOpenWorkspaceModal={() => setWorkspaceModalOpen(true)}
                        onFileApplied={handleFileApplied}
                      />
                    </div>
                  </div>
                );
              })}

              {/* Antigravity-Style Live Thinking Card while Sending */}
              {isSending && (
                <div className="rounded-xl bg-[#161616] border border-zinc-800/80 overflow-hidden mb-3">
                  <div className="flex items-center justify-between px-3.5 py-2.5">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="relative flex h-2 w-2 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                      </span>
                      <span className="text-xs font-medium text-zinc-200 shrink-0">
                        Thinking...
                      </span>
                      <span className="text-[11px] font-mono text-zinc-400 truncate max-w-sm animate-pulse">
                        {liveThinkingStatus}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => setShowLiveTrace((prev) => !prev)}
                      className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      <span>{showLiveTrace ? "Hide" : "Trace"}</span>
                      <svg
                        className={`w-3 h-3 text-zinc-400 transition-transform ${
                          showLiveTrace ? "rotate-180" : ""
                        }`}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                      >
                        <polyline points="18 15 12 9 6 15" />
                      </svg>
                    </button>
                  </div>

                  {showLiveTrace && (
                    <div className="border-t border-zinc-800/80 p-3 bg-[#111111] space-y-2">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                        Active Squad ({activeWorkflowMeta.name})
                      </div>
                      <div className="space-y-1.5">
                        {(activeWorkflowMeta.agents || []).map((ag, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between px-2.5 py-1.5 rounded bg-[#171717] border border-zinc-800/60 text-xs"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-zinc-500 font-mono text-[10px]">
                                0{idx + 1}
                              </span>
                              <span className="text-zinc-300 font-medium">
                                {ag.role}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-zinc-500">
                              {ag.model.split("/").pop()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div ref={chatEndRef} />
            </div>
          )}
        </main>

        {/* Bottom Composer (Claude Desktop 2-Layer Layout) */}
        <BottomComposer
          prompt={prompt}
          onChangePrompt={setPrompt}
          onSend={handleSend}
          isSending={isSending}
          attachments={attachments}
          onAddAttachment={(att) => setAttachments((prev) => [...prev, att])}
          onRemoveAttachment={(id) =>
            setAttachments((prev) => prev.filter((a) => a.id !== id))
          }
          includeWorkspace={includeWorkspace}
          onToggleIncludeWorkspace={() =>
            setIncludeWorkspace((prev) => !prev)
          }
          workspace={workspace}
          onOpenWorkspaceModal={() => setWorkspaceModalOpen(true)}
          onPickFolderInFinder={handleSelectFolderAndEnsureProject}
          onUnlinkWorkspace={() => {
            setWorkspace(null);
            setSelectedWorkspaceFiles([]);
            if (activeSessionId) {
              updateSessionById(activeSessionId, { workspace_path: "" }).catch(
                () => {}
              );
            }
          }}
          projects={projects}
          activeProjectId={activeProjectId}
          onSelectProject={handleSelectProject}
          activeMode={activeMode}
          onSelectMode={setActiveMode}
          temperature={temperature}
          onChangeTemperature={handleChangeTemperature}
          maxTokens={maxTokens}
          onChangeMaxTokens={handleChangeMaxTokens}
        />
      </div>

      {/* Assign Project Workspace Modal */}
      <WorkspaceModal
        isOpen={workspaceModalOpen}
        onClose={() => setWorkspaceModalOpen(false)}
        currentWorkspace={workspace}
        selectedFiles={selectedWorkspaceFiles}
        onAssignWorkspace={(result, selectedPaths) => {
          setWorkspace(result);
          setSelectedWorkspaceFiles(selectedPaths);
          if (activeSessionId) {
            updateSessionById(activeSessionId, {
              workspace_path: result ? result.path : "",
            })
              .then((updated) => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === updated.id ? updated : s))
                );
              })
              .catch(() => {});
          }
          if (result) {
            setIncludeWorkspace(true);
          }
        }}
      />

      {/* Simplified Settings & Real-Time Credit Telemetry Modal */}
      <SettingsTelemetryModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        telemetry={telemetry}
        onTelemetryUpdated={(updated) => setTelemetry(updated)}
      />
    </div>
  );
}
