"use client";

import React, { useRef, useEffect, useState } from "react";
import {
  FileAttachment,
  ProjectItem,
  WorkflowModeId,
  WorkspaceScanResult,
} from "@/lib/types";
import { WORKFLOW_MODES } from "@/lib/constants";

interface BottomComposerProps {
  prompt: string;
  onChangePrompt: (val: string) => void;
  onSend: () => void;
  isSending: boolean;
  attachments: FileAttachment[];
  onAddAttachment: (att: FileAttachment) => void;
  onRemoveAttachment: (id: string) => void;
  includeWorkspace: boolean;
  onToggleIncludeWorkspace: () => void;
  workspace: WorkspaceScanResult | null;
  onOpenWorkspaceModal: () => void;
  onPickFolderInFinder: () => Promise<void>;
  onUnlinkWorkspace: () => void;
  projects: ProjectItem[];
  activeProjectId: string | null;
  onSelectProject: (project: ProjectItem | null) => void;
  activeMode: WorkflowModeId;
  onSelectMode: (mode: WorkflowModeId) => void;
  temperature: number;
  onChangeTemperature: (val: number) => void;
  maxTokens: number;
  onChangeMaxTokens: (val: number) => void;
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

export default function BottomComposer({
  prompt,
  onChangePrompt,
  onSend,
  isSending,
  attachments,
  onAddAttachment,
  onRemoveAttachment,
  includeWorkspace,
  onToggleIncludeWorkspace,
  workspace,
  onOpenWorkspaceModal,
  onPickFolderInFinder,
  onUnlinkWorkspace,
  projects,
  activeProjectId,
  onSelectProject,
  activeMode,
  onSelectMode,
  temperature,
  onChangeTemperature,
  maxTokens,
  onChangeMaxTokens,
}: BottomComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const codeFileInputRef = useRef<HTMLInputElement>(null);
  const imageFileInputRef = useRef<HTMLInputElement>(null);

  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [pickingFinder, setPickingFinder] = useState(false);

  const attachMenuRef = useRef<HTMLDivElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [prompt]);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (
        attachMenuRef.current &&
        !attachMenuRef.current.contains(e.target as Node)
      ) {
        setAttachMenuOpen(false);
      }
      if (
        modelMenuRef.current &&
        !modelMenuRef.current.contains(e.target as Node)
      ) {
        setModelMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isSending && (prompt.trim() || attachments.length > 0)) {
        onSend();
      }
    }
  };

  const handleScriptFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const textContent =
          typeof reader.result === "string" ? reader.result : "";
        const ext = file.name.split(".").pop()?.toLowerCase() || "txt";
        onAddAttachment({
          id: `att-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: file.name,
          type: "code",
          extension: ext,
          sizeBytes: file.size,
          content: textContent,
        });
      };
      reader.readAsText(file);
    });

    e.target.value = "";
    setAttachMenuOpen(false);
  };

  const handleImageFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = typeof reader.result === "string" ? reader.result : "";
        const ext = file.name.split(".").pop()?.toLowerCase() || "png";
        onAddAttachment({
          id: `img-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: file.name,
          type: "image",
          extension: ext,
          sizeBytes: file.size,
          content: dataUrl,
          previewUrl: dataUrl,
        });
      };
      reader.readAsDataURL(file);
    });

    e.target.value = "";
    setAttachMenuOpen(false);
  };

  const handleFinderClick = async () => {
    setPickingFinder(true);
    try {
      await onPickFolderInFinder();
    } finally {
      setPickingFinder(false);
    }
  };

  const currentModeObj =
    WORKFLOW_MODES.find((m) => m.id === activeMode) || WORKFLOW_MODES[0];

  const activeProject = projects.find((p) => p.id === activeProjectId) || null;
  const folderButtonLabel = pickingFinder
    ? "Opening Finder..."
    : workspace?.project_name || activeProject?.name || "Assign folder";

  const teamModes = WORKFLOW_MODES.filter((m) => m.category === "team");
  const rawModes = WORKFLOW_MODES.filter((m) => m.category === "raw");

  return (
    <div className="px-4 sm:px-8 pt-2 pb-4 bg-[#141414] shrink-0">
      <div className="w-full max-w-4xl mx-auto space-y-2 transition-all duration-200">
        {/* Hidden File Inputs */}
        <input
          ref={codeFileInputRef}
          type="file"
          accept=".cs,.py,.md,.json,.txt,.shader,.hlsl,.ts,.tsx,.js,.sh,.pdf"
          multiple
          onChange={handleScriptFileSelect}
          className="hidden"
        />
        <input
          ref={imageFileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleImageFileSelect}
          className="hidden"
        />

        {/* Layer 1: The Input Box (Claude Desktop style #1F1F1F rounded-2xl) */}
        <div className="bg-[#1F1F1F] border border-zinc-800/90 focus-within:border-zinc-700 rounded-2xl px-4 py-2.5 transition-colors">
          {/* Attached Files & Image Previews Row */}
          {attachments.length > 0 && (
            <div className="pb-2 mb-2 flex flex-wrap items-center gap-2 border-b border-zinc-800/70">
              {attachments.map((att) => (
                <div
                  key={att.id}
                  className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#141414] border border-zinc-800 text-xs"
                >
                  {att.type === "image" && att.previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={att.previewUrl}
                      alt={att.name}
                      className="w-5 h-5 rounded object-cover"
                    />
                  ) : null}
                  <span className="font-mono text-[11px] text-zinc-300 truncate max-w-[160px]">
                    {att.name}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemoveAttachment(att.id)}
                    className="text-zinc-500 hover:text-zinc-200 px-1"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Input Row: + Button on the Left, Auto-Expanding Textarea in Center, Send on Right */}
          <div className="flex items-center gap-3">
            {/* + Button (Double Size with Upward Submenu) */}
            <div className="relative shrink-0 flex items-center" ref={attachMenuRef}>
              <button
                type="button"
                onClick={() => setAttachMenuOpen((prev) => !prev)}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-[#2A2A2A] transition-colors"
                title="Attach script or image"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </button>

              {attachMenuOpen && (
                <div className="absolute left-0 bottom-full mb-2 w-44 rounded-xl border border-zinc-800 bg-[#1F1F1F] shadow-2xl p-1.5 z-50 space-y-0.5">
                  <button
                    type="button"
                    onClick={() => codeFileInputRef.current?.click()}
                    className="w-full text-left px-3 py-1.5 rounded-lg text-xs text-zinc-200 hover:bg-[#2A2A2A] transition-colors"
                  >
                    Attach script
                  </button>
                  <button
                    type="button"
                    onClick={() => imageFileInputRef.current?.click()}
                    className="w-full text-left px-3 py-1.5 rounded-lg text-xs text-zinc-200 hover:bg-[#2A2A2A] transition-colors"
                  >
                    Attach image
                  </button>
                </div>
              )}
            </div>

            {/* Auto-expanding Textarea, Vertically Centered on Single Line */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={prompt}
              onChange={(e) => onChangePrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              placeholder="Describe a task or ask a question"
              className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-500 text-sm leading-5 py-1 focus:outline-none resize-none min-h-[28px] max-h-[180px]"
            />

            {/* Circular Send Button with Upward Arrow INSIDE prompt box, Vertically Centered */}
            <div className="shrink-0 flex items-center">
              <button
                type="button"
                onClick={onSend}
                disabled={isSending || (!prompt.trim() && attachments.length === 0)}
                className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
                  isSending
                    ? "bg-zinc-700 text-zinc-300 animate-pulse"
                    : prompt.trim() || attachments.length > 0
                    ? "bg-zinc-100 text-zinc-950 hover:bg-white hover:scale-105 shadow-sm"
                    : "bg-[#2A2A2A] text-zinc-600 cursor-not-allowed"
                }`}
                title={isSending ? "Processing..." : "Send message (Enter)"}
              >
                {isSending ? (
                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" className="opacity-25" />
                    <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" className="opacity-75" />
                  </svg>
                ) : (
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Layer 2: Minimal Bottom Control Row (Directly underneath the input box, borderless muted text) */}
        <div className="flex items-center justify-between px-1 text-xs text-zinc-400">
          {/* Left Side: Direct Finder Folder Selector (Opens Finder directly, no mini menu) */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleFinderClick}
              disabled={pickingFinder}
              className="inline-flex items-center gap-1.5 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
              title="Click to open macOS Finder and select folder (~/Documents/GitHub)"
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0"
              >
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <span className="truncate max-w-[240px]">
                {pickingFinder ? "Opening Finder..." : folderButtonLabel}
              </span>
            </button>

            {/* If workspace is linked, allow quick unlinking with an x button */}
            {workspace && (
              <button
                type="button"
                onClick={onUnlinkWorkspace}
                className="text-zinc-500 hover:text-zinc-200 p-0.5 rounded transition-colors text-xs"
                title="Unlink folder"
              >
                ×
              </button>
            )}
          </div>

          {/* Right Side: Minimalist Model & Logic Trigger + Send Button */}
          <div className="flex items-center gap-3">
            <div className="relative" ref={modelMenuRef}>
              <button
                type="button"
                onClick={() => setModelMenuOpen((prev) => !prev)}
                className="inline-flex items-center gap-2 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <span className="text-zinc-300">
                  {currentModeObj.shortLabel}
                </span>
                <span className="text-zinc-500">
                  Logic {temperature.toFixed(2)}
                </span>
                <ChevronArrow open={modelMenuOpen} className="w-3 h-3 text-zinc-500" />
              </button>

              {modelMenuOpen && (
                <div className="absolute right-0 bottom-full mb-2 w-80 rounded-xl border border-zinc-800 bg-[#1F1F1F] shadow-2xl p-3.5 z-50 space-y-3.5">
                  <div className="space-y-1">
                    <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500 px-2">
                      Multi-Agent Squads
                    </div>
                    {teamModes.map((mode) => {
                      const isSelected = mode.id === activeMode;
                      return (
                        <button
                          key={mode.id}
                          type="button"
                          onClick={() => onSelectMode(mode.id)}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                            isSelected
                              ? "bg-[#2A2A2A] text-zinc-100 font-medium"
                              : "text-zinc-300 hover:bg-[#262626]"
                          }`}
                        >
                          <span>{mode.name}</span>
                          <span className="text-[10px] font-mono text-zinc-500">
                            {mode.badge}
                          </span>
                        </button>
                      );
                    })}

                    <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500 px-2 pt-2">
                      Raw Models
                    </div>
                    {rawModes.map((mode) => {
                      const isSelected = mode.id === activeMode;
                      return (
                        <button
                          key={mode.id}
                          type="button"
                          onClick={() => onSelectMode(mode.id)}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                            isSelected
                              ? "bg-[#2A2A2A] text-zinc-100 font-medium"
                              : "text-zinc-300 hover:bg-[#262626]"
                          }`}
                        >
                          <span>{mode.name}</span>
                          <span className="text-[10px] font-mono text-zinc-500">
                            {mode.badge}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Logic Level Slider */}
                  <div className="pt-2.5 border-t border-zinc-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-300">Logic Level</span>
                      <span className="font-mono text-zinc-400">
                        {temperature.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={temperature}
                      onChange={(e) =>
                        onChangeTemperature(parseFloat(e.target.value))
                      }
                      className="w-full accent-zinc-300 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] font-mono text-zinc-500">
                      <span>0.00 Deterministic</span>
                      <span>1.00 Creative</span>
                    </div>
                  </div>

                  {/* Max Output Tokens */}
                  <div className="pt-2.5 border-t border-zinc-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-300">Max Output Tokens</span>
                      <span className="font-mono text-zinc-400">
                        {maxTokens.toLocaleString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5">
                      {[2048, 4096, 8192, 16384].map((tok) => (
                        <button
                          key={tok}
                          type="button"
                          onClick={() => onChangeMaxTokens(tok)}
                          className={`py-1 rounded-md text-xs font-mono border transition-colors ${
                            maxTokens === tok
                              ? "bg-[#2A2A2A] border-zinc-600 text-zinc-100 font-medium"
                              : "bg-[#141414] border-zinc-800 text-zinc-400 hover:text-zinc-200"
                          }`}
                        >
                          {tok}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
