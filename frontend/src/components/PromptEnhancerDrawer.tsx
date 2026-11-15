"use client";

import React, { useState, useRef, useEffect } from "react";
import { PromptEnhancerMessage, WorkspaceScanResult } from "@/lib/types";
import { enhancePromptApi } from "@/lib/api";

interface PromptEnhancerDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentComposerPrompt: string;
  onInsertIntoComposer: (enhancedText: string) => void;
  workspace: WorkspaceScanResult | null;
  activeMode: string;
}

const STARTER_CHIPS = [
  {
    label: "🎮 Unity C# Mechanic",
    prompt: "Create an inventory grid system in Unity C# using ScriptableObjects, JSON save/load, and drag-and-drop.",
  },
  {
    label: "🌐 Fullstack Feature",
    prompt: "Build an async REST endpoint in FastAPI with SQLite WAL and a matching Next.js 14 client component.",
  },
  {
    label: "⚡ 0-Allocation Optimization",
    prompt: "Refactor my game update loop to eliminate garbage collection heap allocations and prevent frame spikes.",
  },
  {
    label: "🧪 Test Suite Spec",
    prompt: "Write unit and integration tests with edge cases, failure states, and deterministic mock assertions.",
  },
];

export default function PromptEnhancerDrawer({
  isOpen,
  onClose,
  currentComposerPrompt,
  onInsertIntoComposer,
  workspace,
  activeMode,
}: PromptEnhancerDrawerProps) {
  const [messages, setMessages] = useState<PromptEnhancerMessage[]>([]);
  const [input, setInput] = useState("");
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [insertedId, setInsertedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll chat inside drawer
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 150);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSend = async (customPrompt?: string) => {
    const textToSend = (customPrompt || input).trim();
    if (!textToSend || isEnhancing) return;

    const userMsg: PromptEnhancerMessage = {
      id: "usr-" + Date.now(),
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setInput("");
    setIsEnhancing(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.role === "assistant" && m.enhanced_prompt ? m.enhanced_prompt : m.content,
      }));

      const res = await enhancePromptApi({
        prompt: textToSend,
        history: historyPayload,
        workspace_name: workspace?.project_name,
        workspace_files: workspace?.files?.map((f) => f.relative_path),
        active_mode: activeMode,
      });

      const assistantMsg: PromptEnhancerMessage = {
        id: "asst-" + Date.now(),
        role: "assistant",
        content: res.enhanced_prompt,
        summary: res.summary,
        enhanced_prompt: res.enhanced_prompt,
        explanation: res.explanation,
        tips: res.tips,
        model_used: res.model_used,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: PromptEnhancerMessage = {
        id: "err-" + Date.now(),
        role: "assistant",
        content: `Could not optimize prompt: ${err.message || "Network error"}. Please verify your OpenRouter key.`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleInsert = (text: string, id: string) => {
    onInsertIntoComposer(text);
    setInsertedId(id);
    setTimeout(() => setInsertedId(null), 2500);
  };

  const handlePullFromComposer = () => {
    if (currentComposerPrompt.trim()) {
      setInput(currentComposerPrompt.trim());
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <aside
      className="w-full sm:w-[420px] lg:w-[460px] h-screen flex flex-col bg-[#141414] border-l border-zinc-800/80 shadow-2xl z-30 shrink-0 select-none animate-in slide-in-from-right duration-200"
      data-no-drag
    >
      {/* Header */}
      <div className="h-11 px-4 border-b border-zinc-800/80 bg-[#171717] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex items-center justify-center w-5 h-5 rounded-md bg-emerald-500/10 text-emerald-400 text-xs">
            ✨
          </span>
          <h2 className="text-xs font-semibold text-zinc-100 tracking-tight">
            Prompt Architect
          </h2>
          <span className="px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-mono font-medium text-emerald-400">
            $0 · Free
          </span>
        </div>

        <div className="flex items-center gap-1">
          {currentComposerPrompt.trim() && (
            <button
              type="button"
              onClick={handlePullFromComposer}
              className="px-2 py-1 rounded text-[11px] font-medium text-zinc-400 hover:text-zinc-200 bg-[#222222] hover:bg-[#282828] border border-zinc-700/60 transition-colors flex items-center gap-1"
              title="Import draft text currently in main chat composer"
            >
              <span>⚡ Pull Draft</span>
            </button>
          )}

          {messages.length > 0 && (
            <button
              type="button"
              onClick={() => setMessages([])}
              className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-[#222222] transition-colors"
              title="Clear mini-chat"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-[#222222] transition-colors"
            title="Close Drawer"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Workspace Context Bar */}
      <div className="px-4 py-1.5 bg-[#121212] border-b border-zinc-800/50 flex items-center justify-between text-[11px] text-zinc-400">
        <div className="flex items-center gap-1.5 truncate">
          <span className="text-zinc-500">Target Stack:</span>
          <span className="font-medium text-zinc-300 truncate">
            {workspace?.project_name || "General Software"}
          </span>
          {workspace?.is_unity_project && (
            <span className="px-1 rounded bg-amber-500/10 text-amber-400 font-mono text-[9px]">
              Unity C#
            </span>
          )}
        </div>
        <span className="text-zinc-500 font-mono text-[10px]">Gemini 2.0 Flash</span>
      </div>

      {/* Chat Messages Stream */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 select-text">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-center px-2 space-y-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/30 flex items-center justify-center text-lg">
              ✨
            </div>
            <div>
              <h3 className="text-xs font-semibold text-zinc-200 tracking-tight">
                AI Prompt Architect
              </h3>
              <p className="text-[11px] text-zinc-400 mt-1 max-w-[280px] leading-relaxed">
                Type rough instructions in Spanish or casual English. I will craft a production-grade, structured English prompt ready for Claude Opus & Sonnet.
              </p>
            </div>

            <div className="w-full space-y-2 pt-2">
              <div className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 text-left px-1">
                Quick Inspiration
              </div>
              <div className="grid grid-cols-1 gap-1.5">
                {STARTER_CHIPS.map((chip, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSend(chip.prompt)}
                    className="w-full text-left p-2.5 rounded-lg bg-[#1A1A1A] hover:bg-[#222222] border border-zinc-800/80 hover:border-zinc-700 transition-all text-xs text-zinc-300 group"
                  >
                    <div className="font-medium text-zinc-200 group-hover:text-emerald-300 transition-colors">
                      {chip.label}
                    </div>
                    <div className="text-[10px] text-zinc-500 line-clamp-1 mt-0.5">
                      {chip.prompt}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";

            if (isUser) {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl bg-[#262626] border border-zinc-700/60 px-3.5 py-2 text-xs text-zinc-100 leading-relaxed">
                    {msg.content}
                  </div>
                </div>
              );
            }

            return (
              <div key={msg.id} className="space-y-2.5">
                {/* Summary Pill */}
                {msg.summary && (
                  <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md">
                    <span>✨</span>
                    <span className="font-medium leading-tight">{msg.summary}</span>
                  </div>
                )}

                {/* Enhanced Prompt Card */}
                {msg.enhanced_prompt && (
                  <div className="rounded-xl bg-[#191919] border border-zinc-800 shadow-sm overflow-hidden">
                    <div className="px-3 py-2 bg-[#202020] border-b border-zinc-800/80 flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">
                          English Spec
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 font-mono">
                          Ready for AI
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleCopy(msg.enhanced_prompt!, msg.id)}
                          className="px-2 py-1 rounded text-[11px] font-medium text-zinc-300 hover:text-white bg-[#2A2A2A] hover:bg-[#333333] border border-zinc-700/60 transition-colors flex items-center gap-1"
                          title="Copy to clipboard"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <svg className="w-3 h-3 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                              <span className="text-emerald-400 font-mono text-[10px]">Copied</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                              </svg>
                              <span>Copy</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleInsert(msg.enhanced_prompt!, msg.id)}
                          className="px-2.5 py-1 rounded text-[11px] font-medium text-emerald-300 hover:text-emerald-200 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 transition-colors flex items-center gap-1 shadow-sm"
                          title="Insert prompt directly into main chat composer"
                        >
                          {insertedId === msg.id ? (
                            <>
                              <svg className="w-3 h-3 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                              <span className="font-mono text-[10px]">Inserted!</span>
                            </>
                          ) : (
                            <>
                              <span>⚡</span>
                              <span>Use in Chat</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="p-3 text-[11px] font-mono leading-relaxed text-zinc-200 whitespace-pre-wrap max-h-96 overflow-y-auto selection:bg-emerald-500/30">
                      {msg.enhanced_prompt}
                    </div>
                  </div>
                )}

                {/* Explanation & Tips */}
                {msg.explanation && (
                  <div className="px-3 py-2 rounded-lg bg-[#171717] border border-zinc-800/60 text-[11px] text-zinc-400 space-y-1">
                    <div className="font-medium text-zinc-300">Why this works better:</div>
                    <div className="leading-relaxed">{msg.explanation}</div>
                    {msg.tips && msg.tips.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {msg.tips.map((tip, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded bg-[#222222] border border-zinc-700/50 text-zinc-300"
                          >
                            ✓ {tip}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}

        {isEnhancing && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#181818] border border-zinc-800 text-xs text-zinc-400 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>Architecting optimal English prompt ($0 Free Tier)...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Mini Composer */}
      <div className="p-3 bg-[#181818] border-t border-zinc-800/80 shrink-0">
        <div className="rounded-xl bg-[#202020] border border-zinc-700/70 focus-within:border-emerald-500/60 focus-within:ring-1 focus-within:ring-emerald-500/30 transition-all p-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type rough instructions (Spanish or English) to transform into a prompt..."
            rows={2}
            className="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 resize-none outline-none leading-relaxed select-text"
          />

          <div className="flex items-center justify-between pt-1 text-[10px] text-zinc-500 border-t border-zinc-800/60 mt-1">
            <span className="font-mono">Enter ↵ to architect · $0</span>
            <button
              type="button"
              onClick={() => handleSend()}
              disabled={!input.trim() || isEnhancing}
              className={`px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1 transition-all ${
                input.trim() && !isEnhancing
                  ? "bg-emerald-500 hover:bg-emerald-400 text-black shadow-sm font-semibold"
                  : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
              }`}
            >
              <span>Enhance</span>
              <span>⚡</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
