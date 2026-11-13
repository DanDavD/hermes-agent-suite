"use client";

import React from "react";

interface TopBarProps {
  sidebarCollapsed: boolean;
  onExpandSidebar: () => void;
  sessionTitle: string;
  projectName?: string | null;
}

export default function TopBar({
  sidebarCollapsed,
  onExpandSidebar,
  sessionTitle,
  projectName,
}: TopBarProps) {
  return (
    <header
      data-window-drag
      className={`h-11 border-b border-zinc-800/70 bg-[#141414] z-20 shrink-0 flex items-center justify-between gap-3 select-none [-webkit-app-region:drag] ${
        sidebarCollapsed ? "pl-20 pr-4" : "px-4"
      }`}
    >
      <div className="flex items-center gap-3 min-w-0" data-no-drag>
        {sidebarCollapsed && (
          <button
            type="button"
            data-no-drag
            onClick={onExpandSidebar}
            className="px-2 py-1 rounded-md bg-[#262626] hover:bg-[#303030] text-zinc-300 hover:text-zinc-100 transition-colors shrink-0 flex items-center gap-1.5 [-webkit-app-region:no-drag]"
            title="Expand Sidebar"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
            <span className="text-[11px] font-medium">Sidebar</span>
          </button>
        )}

        <div className="flex items-center gap-2 min-w-0 text-xs">
          {projectName && (
            <>
              <span className="font-medium text-zinc-400 truncate max-w-[180px]">
                {projectName}
              </span>
              <span className="text-zinc-600">/</span>
            </>
          )}
          <h1 className="font-medium text-zinc-200 truncate select-none pointer-events-none">
            {sessionTitle || "New Chat"}
          </h1>
        </div>
      </div>
    </header>
  );
}
