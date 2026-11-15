"use client";

import React, { useState, useMemo } from "react";
import { AutonomousActionItem } from "@/lib/types";

interface FilesChangedSummaryBarProps {
  actionsExecuted?: AutonomousActionItem[];
  content?: string;
}

interface FileDiffRow {
  path: string;
  basename: string;
  status: "created" | "modified" | "patched" | "deleted";
  linesAdded: number;
  linesRemoved: number;
}

function getBasename(filePath: string): string {
  const normalized = (filePath || "").replace(/\\/g, "/").replace(/\/+$/, "");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || normalized || "file";
}

function parseFallbackFilesFromContent(content: string): FileDiffRow[] {
  if (!content) return [];
  const results: FileDiffRow[] = [];
  const seen = new Set<string>();

  const codeBlockRegex = /```([a-zA-Z0-9_+#-]*)\n([\s\S]*?)```/g;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    const body = match[2] || "";
    const firstLines = body.split("\n").slice(0, 5);

    for (const ln of firstLines) {
      const delMatch = ln.match(
        /(?:\/\/|#|\/\*|<!--|--)\s*(?:Delete|Delete-File|File-Delete|Remove-File|Eliminar):\s*([^\s*<>]+\.[a-zA-Z0-9]+)/i
      );
      if (delMatch && delMatch[1]) {
        const rel = delMatch[1].trim().replace(/^\/+/, "");
        if (!seen.has(rel)) {
          seen.add(rel);
          const totalLines = Math.max(1, body.split("\n").length - 1);
          results.push({
            path: rel,
            basename: getBasename(rel),
            status: "deleted",
            linesAdded: 0,
            linesRemoved: totalLines,
          });
        }
        break;
      }

      const fileMatch = ln.match(
        /(?:\/\/|#|\/\*|<!--|--)\s*(?:File|Path|Target|Archivo|Filename|Append|Append-File|Prepend|Prepend-File):\s*([^\r\n*<>]+\.[a-zA-Z0-9]+)/i
      );
      if (fileMatch && fileMatch[1]) {
        const rel = fileMatch[1].trim().replace(/^\/+/, "");
        // Check if this block is preceded by **Before:**
        const preceding = content.slice(Math.max(0, match.index - 140), match.index).trim();
        const lastPrecLine = preceding.split("\n").pop()?.trim() || "";
        if (/(?:\*\*Before.*?\*\*|###+\s*Before|^Before\s*:)/i.test(lastPrecLine)) {
          break;
        }

        let added = 0;
        let removed = 0;
        if (body.includes("<<<<<<< SEARCH") && body.includes(">>>>>>> REPLACE")) {
          const srRegex = /<<<<<<<\s*SEARCH[ \t]*\r?\n([\s\S]*?)\r?\n=======[ \t]*\r?\n([\s\S]*?)\r?\n>>>>>>>\s*REPLACE/g;
          let sr: RegExpExecArray | null;
          while ((sr = srRegex.exec(body)) !== null) {
            removed += sr[1] ? sr[1].split("\n").length : 0;
            added += sr[2] ? sr[2].split("\n").length : 0;
          }
        } else {
          const bodyLines = body.replace(/\n$/, "").split("\n");
          added = Math.max(1, bodyLines.length - 1);
          removed = 0;
        }

        const existingIdx = results.findIndex((r) => r.path === rel);
        const row: FileDiffRow = {
          path: rel,
          basename: getBasename(rel),
          status: removed > 0 ? "patched" : "modified",
          linesAdded: added,
          linesRemoved: removed,
        };
        if (existingIdx >= 0) {
          results[existingIdx] = row;
        } else {
          seen.add(rel);
          results.push(row);
        }
        break;
      }
    }
  }

  return results;
}

export default function FilesChangedSummaryBar({
  actionsExecuted,
  content,
}: FilesChangedSummaryBarProps) {
  const [expanded, setExpanded] = useState(false);

  const fileRows = useMemo<FileDiffRow[]>(() => {
    const fromActions: FileDiffRow[] = [];
    if (Array.isArray(actionsExecuted) && actionsExecuted.length > 0) {
      for (const act of actionsExecuted) {
        if (
          (act.type === "file_written" || act.type === "file_deleted") &&
          act.path
        ) {
          const isDeleted =
            act.type === "file_deleted" || act.status === "deleted";
          const estLinesFromBytes = act.bytes
            ? Math.max(1, Math.round(act.bytes / 38))
            : 1;
          fromActions.push({
            path: act.path,
            basename: act.filename || getBasename(act.path),
            status: isDeleted
              ? "deleted"
              : (act.status as FileDiffRow["status"]) || "modified",
            linesAdded:
              typeof act.lines_added === "number"
                ? act.lines_added
                : isDeleted
                  ? 0
                  : estLinesFromBytes,
            linesRemoved:
              typeof act.lines_removed === "number"
                ? act.lines_removed
                : isDeleted
                  ? estLinesFromBytes
                  : 0,
          });
        }
      }
    }

    if (fromActions.length > 0) {
      return fromActions;
    }
    return parseFallbackFilesFromContent(content || "");
  }, [actionsExecuted, content]);

  if (fileRows.length === 0) return null;

  const totalFiles = fileRows.length;
  const createdOrModifiedFiles = fileRows.filter(
    (f) => f.status !== "deleted"
  ).length;
  const deletedFiles = fileRows.filter((f) => f.status === "deleted").length;

  return (
    <div className="mt-3 rounded-xl border border-zinc-800/80 bg-[#121212] overflow-hidden select-none">
      {/* Main Summary Bar */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((prev) => !prev);
          }
        }}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[#181818] transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 text-[13px]">
          <span className="text-zinc-300 font-medium">
            {totalFiles} {totalFiles === 1 ? "file" : "file(s)"} changed
          </span>

          <span className="font-mono font-medium text-emerald-400">
            +{createdOrModifiedFiles}
          </span>

          <span className="font-mono font-medium text-rose-400">
            -{deletedFiles}
          </span>

          <svg
            className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-150 ${
              expanded ? "rotate-90" : "rotate-0"
            }`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </div>

        {/* Right Review Pill Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((prev) => !prev);
          }}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#1C1C1C] hover:bg-[#252525] border border-zinc-800 text-xs font-medium text-zinc-200 transition-colors"
        >
          <svg
            className="w-3.5 h-3.5 text-zinc-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.9"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
          <span>Review</span>
        </button>
      </div>

      {/* Expandable Submenu of Files Changed (Basename + Lines Added/Removed) */}
      {expanded && (
        <div className="border-t border-zinc-800/80 bg-[#0E0E0E] divide-y divide-zinc-800/50">
          {fileRows.map((file, idx) => {
            const isDeleted = file.status === "deleted";
            return (
              <div
                key={`${file.path}-${idx}`}
                title={file.path}
                className="flex items-center justify-between px-4 py-2 text-xs font-mono hover:bg-[#151515] transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      isDeleted ? "bg-rose-400" : "bg-emerald-400"
                    }`}
                  />
                  <span
                    className={`truncate font-medium ${
                      isDeleted
                        ? "text-rose-400 line-through"
                        : "text-emerald-300"
                    }`}
                  >
                    {file.basename}
                  </span>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  <span className="text-emerald-400 font-medium">
                    +{file.linesAdded}
                  </span>
                  <span className="text-rose-400 font-medium">
                    -{file.linesRemoved}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
