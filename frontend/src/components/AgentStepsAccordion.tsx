"use client";

import React, { useState } from "react";
import { AgentThoughtStep, AutonomousActionItem } from "@/lib/types";
import MarkdownRenderer from "./MarkdownRenderer";

interface AgentStepsAccordionProps {
  steps?: AgentThoughtStep[];
  actionsExecuted?: AutonomousActionItem[];
  isStreaming?: boolean;
  currentStatus?: string;
  workspacePath?: string;
  onOpenWorkspaceModal?: () => void;
  onFileApplied?: (relativePath: string, fullPath: string) => void;
}

function shortModelName(model: string): string {
  if (!model) return "Hermes 3";
  if (model.includes("70b")) return "Hermes 3 70B";
  if (model.includes("8b")) return "Hermes 3 8B";
  if (model.includes("qwen") || model.includes("32b")) return "Qwen 2.5 Coder 32B";
  if (model.includes("deepseek-v3")) return "DeepSeek V3";
  if (model.includes("deepseek-r1")) return "DeepSeek R1";
  if (model.includes("claude")) return "Claude 3.5 Sonnet";
  return model.split("/").pop() || model;
}

function ChevronArrow({
  open,
  className = "w-3 h-3 text-zinc-400",
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

export default function AgentStepsAccordion({
  steps = [],
  actionsExecuted = [],
  isStreaming = false,
  currentStatus,
  workspacePath,
  onOpenWorkspaceModal,
  onFileApplied,
}: AgentStepsAccordionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedStepIdx, setExpandedStepIdx] = useState<number | null>(null);

  const hasSteps = steps && steps.length > 0;
  const hasActions = actionsExecuted && actionsExecuted.length > 0;

  if (!hasSteps && !hasActions && !isStreaming) return null;

  const completedCount = steps.filter(
    (s) =>
      s.status === "complete" ||
      s.status === "completed" ||
      String(s.status).toLowerCase() === "complete"
  ).length;

  const leadAgentSummary =
    steps[0]?.output?.split?.("\n")?.[0]?.slice(0, 70) ||
    currentStatus ||
    "Completed autonomous reasoning and execution";

  return (
    <div className="mb-3 rounded-xl border border-zinc-800/80 bg-[#161616] overflow-hidden">
      {/* Antigravity-Style Thinking Bar */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-[#1E1E1E] transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Subtle pulse / completed indicator */}
          {isStreaming ? (
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
          )}

          <span className="text-xs font-medium text-zinc-300 shrink-0">
            {isStreaming ? "Thinking..." : `Thinking (${steps.length} ${steps.length === 1 ? "step" : "steps"})`}
          </span>

          <span className="text-[11px] font-mono text-zinc-500 truncate max-w-sm hidden sm:inline">
            {leadAgentSummary}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {hasActions && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
              ⚡ Autonomous Action
            </span>
          )}
          <span className="text-[11px] font-mono text-zinc-400">
            {isOpen ? "Hide" : "Trace"}
          </span>
          <ChevronArrow open={isOpen} className="w-3 h-3 text-zinc-400" />
        </div>
      </button>

      {/* Expandable Trace Drawer */}
      {isOpen && (
        <div className="border-t border-zinc-800/80 divide-y divide-zinc-800/60 bg-[#121212]">
          {/* Autonomous Actions Banner (Files Written / Tests Run) */}
          {hasActions && (
            <div className="px-4 py-2.5 bg-[#171717] space-y-1.5">
              <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">
                Autonomous Workspace Execution
              </div>
              {actionsExecuted.map((act, aIdx) => (
                <div
                  key={aIdx}
                  className="flex items-center justify-between text-xs font-mono text-zinc-300"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-400">✓</span>
                    <span>{act.details || act.summary || act.path}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">{act.status}</span>
                </div>
              ))}
            </div>
          )}

          {/* Individual Agent Steps */}
          {steps.map((step, idx) => {
            const isStepExpanded = expandedStepIdx === idx;
            const isStepRunning = step.status === "running";
            const stepText = step.output || step.content || "";

            return (
              <div key={idx} className="transition-colors">
                <button
                  type="button"
                  onClick={() =>
                    setExpandedStepIdx(isStepExpanded ? null : idx)
                  }
                  className="w-full flex items-center justify-between px-3.5 py-2 text-left hover:bg-[#1A1A1A] transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-[11px] font-mono text-zinc-500">
                      0{step.step ?? idx + 1}
                    </span>
                    <span className="text-xs font-medium text-zinc-200 truncate">
                      {step.agent}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#242424] text-zinc-400">
                      {shortModelName(step.model)}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      {isStepRunning ? "Running..." : "Done"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {step.tokens ? (
                      <span className="text-[10px] font-mono text-zinc-500">
                        {step.tokens.toLocaleString()} tok
                      </span>
                    ) : null}
                    <span className="text-[11px] font-mono text-zinc-400">
                      {isStepExpanded ? "Hide" : "Inspect"}
                    </span>
                    <ChevronArrow open={isStepExpanded} className="w-3 h-3 text-zinc-400" />
                  </div>
                </button>

                {isStepExpanded && stepText && (
                  <div className="px-4 py-3 bg-[#0E0E0E] border-t border-zinc-800/60 text-xs">
                    <div className="mb-2 text-[11px] font-mono text-zinc-400">
                      Stage {step.step ?? idx + 1} Deliverable ({step.agent})
                    </div>
                    <MarkdownRenderer
                      content={stepText}
                      workspacePath={workspacePath}
                      onOpenWorkspaceModal={onOpenWorkspaceModal}
                      onFileApplied={onFileApplied}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
