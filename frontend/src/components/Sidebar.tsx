"use client";

import React, { useState } from "react";
import { ChatSession, ProjectItem, TelemetryData } from "@/lib/types";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  projects: ProjectItem[];
  activeProjectId: string | null;
  onSelectProject: (project: ProjectItem | null) => void;
  onCreateProjectInline: (name: string) => Promise<void>;
  onCreateProjectFromFinder: () => Promise<void>;
  onLinkProjectFolderInFinder: (project: ProjectItem) => Promise<void>;
  onDeleteProject: (projectId: string, e: React.MouseEvent) => Promise<void>;
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateLooseSession: () => void;
  onCreateProjectSession: (project: ProjectItem) => void;
  onDeleteSession: (sessionId: string, e: React.MouseEvent) => void;
  telemetry: TelemetryData | null;
  onOpenSettingsModal: () => void;
}

function ChevronArrow({
  open,
  className = "w-3 h-3 text-zinc-500",
}: {
  open: boolean;
  className?: string;
}) {
  return (
    <svg
      className={`${className} transition-transform duration-150 shrink-0 ${
        open ? "rotate-180" : "rotate-0"
      }`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  projects,
  activeProjectId,
  onSelectProject,
  onCreateProjectFromFinder,
  onLinkProjectFolderInFinder,
  onDeleteProject,
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateLooseSession,
  onCreateProjectSession,
  onDeleteSession,
  telemetry,
  onOpenSettingsModal,
}: SidebarProps) {
  const [projectsSectionCollapsed, setProjectsSectionCollapsed] =
    useState(false);
  const [collapsedProjects, setCollapsedProjects] = useState<
    Record<string, boolean>
  >({});
  const [looseChatsCollapsed, setLooseChatsCollapsed] = useState(false);

  if (collapsed) {
    return null;
  }

  const creditDisplay =
    telemetry?.remaining_credits !== null &&
    telemetry?.remaining_credits !== undefined
      ? `$${telemetry.remaining_credits.toFixed(4)}`
      : "$0.0000";

  const toggleProjectGroup = (proj: ProjectItem) => {
    setCollapsedProjects((prev) => ({
      ...prev,
      [proj.id]: !prev[proj.id],
    }));
    onSelectProject(proj);
  };

  const looseSessions = sessions.filter((s) => !s.project_id);

  return (
    <aside className="w-64 shrink-0 h-screen bg-[#111111] border-r border-zinc-800/80 flex flex-col select-none text-zinc-300">
      {/* Top Header / macOS Traffic Light Area (Draggable) */}
      <div
        data-window-drag
        className="h-11 pl-20 pr-3 flex items-center justify-between select-none [-webkit-app-region:drag]"
      >
        <span className="text-xs font-medium tracking-tight text-zinc-300 pointer-events-none select-none">
          Hermes Studio
        </span>
        <button
          type="button"
          data-no-drag
          onClick={onToggleCollapse}
          className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors [-webkit-app-region:no-drag]"
          title="Collapse sidebar"
        >
          <svg
            className="w-3.5 h-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>
      </div>

      {/* Top + New Button (Claude Desktop neutral gray bar) */}
      <div className="px-3 pb-3">
        <button
          type="button"
          data-no-drag
          onClick={() => {
            setLooseChatsCollapsed(false);
            onCreateLooseSession();
          }}
          className="w-full text-left bg-[#262626] hover:bg-[#303030] active:bg-[#383838] text-zinc-200 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors [-webkit-app-region:no-drag] flex items-center justify-between group"
        >
          <span>+ New</span>
          <span className="text-[10px] text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity">
            ⌘N
          </span>
        </button>
      </div>

      {/* Scrollable Body: 1. Projects Section, 2. Chats Section */}
      <div className="flex-1 overflow-y-auto px-2 space-y-3 pb-4">
        {/* 1. Collapsible Projects Section Header (like Chats, with folder+ icon on the right) */}
        <div className="space-y-0.5">
          <div
            onClick={() => setProjectsSectionCollapsed((prev) => !prev)}
            className="px-2.5 py-1.5 rounded-md hover:bg-[#1F1F1F] flex items-center justify-between cursor-pointer text-zinc-400"
          >
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-zinc-300">
                Projects
              </span>
              <ChevronArrow
                open={!projectsSectionCollapsed}
                className="w-3 h-3 text-zinc-500"
              />
            </div>

            {/* Folder with + icon on the right to create project from Finder */}
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                setProjectsSectionCollapsed(false);
                await onCreateProjectFromFinder();
              }}
              className="p-1 rounded text-zinc-400 hover:text-zinc-100 hover:bg-[#262626] transition-colors"
              title="Choose folder in Finder to create project"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.9"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                <line x1="12" y1="11" x2="12" y2="17" />
                <line x1="9" y1="14" x2="15" y2="14" />
              </svg>
            </button>
          </div>

          {/* Expanded Projects List */}
          {!projectsSectionCollapsed && (
            <div className="space-y-0.5 pl-1">
              {projects.length === 0 ? (
                <div className="px-3 py-1 text-[11px] text-zinc-600 italic">
                  No projects yet
                </div>
              ) : (
                projects.map((proj) => {
                  const isCollapsed = Boolean(collapsedProjects[proj.id]);
                  const isProjectActive = activeProjectId === proj.id;
                  const projectChats = sessions.filter(
                    (s) =>
                      s.project_id === proj.id ||
                      (!s.project_id &&
                        proj.workspace_path &&
                        s.workspace_path === proj.workspace_path)
                  );

                  return (
                    <div key={proj.id} className="space-y-0.5">
                      {/* Project Collapsible Row */}
                      <div
                        onClick={() => toggleProjectGroup(proj)}
                        className={`px-2.5 py-1.5 rounded-md hover:bg-[#1F1F1F] flex items-center justify-between group cursor-pointer transition-colors ${
                          isProjectActive && !activeSessionId
                            ? "bg-[#1F1F1F] text-zinc-100"
                            : isProjectActive
                            ? "text-zinc-100"
                            : "text-zinc-400"
                        }`}
                      >
                        <div className="flex items-center gap-1.5 min-w-0 pr-2">
                          <span className="text-xs font-medium truncate text-zinc-200">
                            {proj.name}
                          </span>
                          {projectChats.length > 0 && (
                            <ChevronArrow
                              open={!isCollapsed}
                              className="w-3 h-3 text-zinc-500"
                            />
                          )}
                        </div>

                        {/* Right Actions on Project Row */}
                        <div
                          className="flex items-center gap-1 shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {/* Change Folder in Finder (on hover) */}
                          <button
                            type="button"
                            onClick={() => onLinkProjectFolderInFinder(proj)}
                            title={
                              proj.workspace_path
                                ? `Folder: ${proj.workspace_path} (Click to change)`
                                : "Link local folder in Finder"
                            }
                            className="opacity-0 group-hover:opacity-100 p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-[#262626] transition-opacity"
                          >
                            <svg
                              width="12"
                              height="12"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.8"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                            </svg>
                          </button>

                          {/* Delete Project × (on hover) */}
                          <button
                            type="button"
                            onClick={(e) => onDeleteProject(proj.id, e)}
                            title="Delete project"
                            className="opacity-0 group-hover:opacity-100 px-1 text-xs text-zinc-500 hover:text-zinc-200 transition-opacity"
                          >
                            ×
                          </button>

                          {/* + Button to add a new conversation to this project's folder */}
                          <button
                            type="button"
                            onClick={() => {
                              setCollapsedProjects((prev) => ({
                                ...prev,
                                [proj.id]: false,
                              }));
                              onCreateProjectSession(proj);
                            }}
                            title={`New conversation in ${proj.name}`}
                            className="px-1.5 py-0.5 rounded text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#262626] transition-colors"
                          >
                            +
                          </button>
                        </div>
                      </div>

                      {/* Expanded Project Conversations List */}
                      {!isCollapsed && projectChats.length > 0 && (
                        <div className="space-y-0.5 pl-3 border-l border-zinc-800/60 ml-2.5">
                          {projectChats.map((sess) => {
                            const isActive = sess.id === activeSessionId;
                            return (
                              <div
                                key={sess.id}
                                onClick={() => onSelectSession(sess.id)}
                                className={`group flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs cursor-pointer transition-colors ${
                                  isActive
                                    ? "bg-[#262626] text-zinc-100"
                                    : "text-zinc-400 hover:bg-[#1F1F1F] hover:text-zinc-200"
                                }`}
                              >
                                <span className="truncate pr-2">
                                  {sess.title || "Untitled"}
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => onDeleteSession(sess.id, e)}
                                  className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-200 px-1 shrink-0 transition-opacity"
                                  title="Delete chat"
                                >
                                  ×
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* 2. Collapsible Loose Chats Section */}
        <div className="space-y-0.5 pt-1">
          <div
            onClick={() => setLooseChatsCollapsed((prev) => !prev)}
            className="px-2.5 py-1.5 rounded-md hover:bg-[#1F1F1F] flex items-center justify-between cursor-pointer text-zinc-400"
          >
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-zinc-300">Chats</span>
              <ChevronArrow
                open={!looseChatsCollapsed}
                className="w-3 h-3 text-zinc-500"
              />
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setLooseChatsCollapsed(false);
                onCreateLooseSession();
              }}
              className="px-1.5 py-0.5 rounded text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#262626] transition-colors"
              title="New chat"
            >
              +
            </button>
          </div>

          {!looseChatsCollapsed && (
            <div className="space-y-0.5 pl-1">
              {looseSessions.length === 0 ? (
                <div className="px-3 py-1 text-[11px] text-zinc-600 italic">
                  No chats yet
                </div>
              ) : (
                looseSessions.map((sess) => {
                  const isActive = sess.id === activeSessionId;
                  return (
                    <div
                      key={sess.id}
                      onClick={() => onSelectSession(sess.id)}
                      className={`group flex items-center justify-between px-3 py-1.5 rounded-md text-xs cursor-pointer transition-colors ${
                        isActive
                          ? "bg-[#262626] text-zinc-100"
                          : "text-zinc-400 hover:bg-[#1F1F1F] hover:text-zinc-200"
                      }`}
                    >
                      <span className="truncate pr-2">
                        {sess.title || "Untitled"}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => onDeleteSession(sess.id, e)}
                        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-200 px-1 shrink-0 transition-opacity"
                        title="Delete chat"
                      >
                        ×
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>

      {/* Minimal Neutral Footer */}
      <div className="px-3.5 py-3 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-400">
        <span className="font-mono text-[11px] text-zinc-400 truncate">
          Credits: {creditDisplay}
        </span>
        <button
          type="button"
          onClick={onOpenSettingsModal}
          className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-[#262626] transition-colors"
          title="Settings & Model Directory"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
