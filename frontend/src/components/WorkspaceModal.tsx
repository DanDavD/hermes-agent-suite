"use client";

import React, { useState, useEffect } from "react";
import { WorkspaceScanResult } from "@/lib/types";
import { pickFolderInFinder, scanWorkspaceDirectory } from "@/lib/api";
import { WORKSPACE_PRESETS } from "@/lib/constants";

interface WorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentWorkspace: WorkspaceScanResult | null;
  selectedFiles: string[];
  onAssignWorkspace: (
    result: WorkspaceScanResult | null,
    selectedRelativePaths: string[]
  ) => void;
}

export default function WorkspaceModal({
  isOpen,
  onClose,
  currentWorkspace,
  selectedFiles,
  onAssignWorkspace,
}: WorkspaceModalProps) {
  const [pathInput, setPathInput] = useState(
    currentWorkspace?.path ||
      "/Users/Damid/.gemini/antigravity/scratch/hermes-agent-suite"
  );
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<WorkspaceScanResult | null>(
    currentWorkspace
  );
  const [checkedPaths, setCheckedPaths] = useState<Set<string>>(
    new Set(selectedFiles)
  );
  const [fileFilter, setFileFilter] = useState("");

  useEffect(() => {
    if (isOpen) {
      if (currentWorkspace) {
        setPathInput(currentWorkspace.path);
        setScanResult(currentWorkspace);
        setCheckedPaths(
          new Set(
            selectedFiles.length > 0
              ? selectedFiles
              : currentWorkspace.files.map((f) => f.relative_path)
          )
        );
      }
      setError(null);
    }
  }, [isOpen, currentWorkspace, selectedFiles]);

  if (!isOpen) return null;

  const applyNewScan = (res: WorkspaceScanResult) => {
    setScanResult(res);
    setPathInput(res.path);
    let runningTokens = 0;
    const defaultSelected = new Set<string>();
    for (const file of res.files) {
      if (runningTokens + file.tokens <= res.token_budget) {
        defaultSelected.add(file.relative_path);
        runningTokens += file.tokens;
      }
    }
    setCheckedPaths(defaultSelected);
  };

  const handleScan = async (targetPath?: string) => {
    const pathToScan = (targetPath ?? pathInput).trim();
    if (!pathToScan) return;

    setPathInput(pathToScan);
    setScanning(true);
    setError(null);

    try {
      const res = await scanWorkspaceDirectory(pathToScan);
      applyNewScan(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to scan local folder"
      );
    } finally {
      setScanning(false);
    }
  };

  const handlePickInFinder = async () => {
    setScanning(true);
    setError(null);
    try {
      const picked = await pickFolderInFinder();
      if (!picked.cancelled && picked.scan) {
        applyNewScan(picked.scan);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to open macOS Finder"
      );
    } finally {
      setScanning(false);
    }
  };

  const toggleFile = (relPath: string) => {
    setCheckedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(relPath)) {
        next.delete(relPath);
      } else {
        next.add(relPath);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!scanResult) return;
    setCheckedPaths(new Set(scanResult.files.map((f) => f.relative_path)));
  };

  const handleDeselectAll = () => {
    setCheckedPaths(new Set());
  };

  const filteredFiles = (scanResult?.files || []).filter((f) =>
    f.relative_path.toLowerCase().includes(fileFilter.toLowerCase())
  );

  const selectedTokenSum = (scanResult?.files || [])
    .filter((f) => checkedPaths.has(f.relative_path))
    .reduce((acc, f) => acc + f.tokens, 0);

  const budgetLimit = scanResult?.token_budget || 45000;
  const budgetPercent = Math.min(
    100,
    Math.round((selectedTokenSum / budgetLimit) * 100)
  );

  const handleConfirmAssign = () => {
    if (!scanResult) return;
    const selectedArray = Array.from(checkedPaths);
    const updatedResult: WorkspaceScanResult = {
      ...scanResult,
      included_files: selectedArray.length,
      total_tokens: selectedTokenSum,
      files: scanResult.files.map((f) => ({
        ...f,
        included: checkedPaths.has(f.relative_path),
      })),
    };
    onAssignWorkspace(updatedResult, selectedArray);
    onClose();
  };

  const handleUnlink = () => {
    setScanResult(null);
    setCheckedPaths(new Set());
    onAssignWorkspace(null, []);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-2xl border border-zinc-800 bg-[#1A1A1A] shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/80 bg-[#1F1F1F]">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">
              Project Workspace Folder
            </h2>
            <p className="text-xs text-zinc-400">
              Select a folder in Finder or enter a local directory path
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#2A2A2A] transition-colors"
          >
            Close
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium text-zinc-300">
                Local macOS Project Directory Path
              </label>
              <button
                type="button"
                onClick={handlePickInFinder}
                disabled={scanning}
                className="px-3 py-1 rounded-md bg-[#2A2A2A] hover:bg-[#333333] text-xs font-medium text-zinc-200 transition-colors"
              >
                Choose in Finder (~/Documents/GitHub)...
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={pathInput}
                onChange={(e) => setPathInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleScan();
                  }
                }}
                placeholder="/Users/Damid/Documents/GitHub/MyProject"
                className="flex-1 px-3.5 py-2 rounded-lg bg-[#111111] border border-zinc-800 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-600"
              />
              <button
                type="button"
                onClick={() => handleScan()}
                disabled={scanning || !pathInput.trim()}
                className="px-4 py-2 rounded-lg bg-zinc-200 hover:bg-white disabled:opacity-50 text-xs font-medium text-zinc-900 transition-colors shrink-0"
              >
                {scanning ? "Scanning..." : "Scan"}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-[11px] text-zinc-500">Presets:</span>
              {WORKSPACE_PRESETS.map((preset) => (
                <button
                  key={preset.path}
                  type="button"
                  onClick={() => handleScan(preset.path)}
                  className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-[#141414] hover:bg-[#262626] text-zinc-300 border border-zinc-800 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-[#141414] border border-zinc-800 text-xs text-rose-400">
              {error}
            </div>
          )}

          {scanResult && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#141414] border border-zinc-800/90 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-[#262626] text-zinc-200">
                      {scanResult.project_name}
                    </span>
                    <span className="text-xs text-zinc-400">
                      {scanResult.summary}
                    </span>
                  </div>
                  <span className="text-[11px] text-zinc-500 font-mono">
                    Pruned: Library/, Temp/, obj/, .git/, node_modules/
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-zinc-400">
                      Selected Files:{" "}
                      <strong className="text-zinc-100 font-mono">
                        {checkedPaths.size}
                      </strong>{" "}
                      / {scanResult.files.length} files
                    </span>
                    <span className="font-mono text-xs text-zinc-300">
                      {selectedTokenSum.toLocaleString()}{" "}
                      <span className="text-zinc-500">
                        / {budgetLimit.toLocaleString()} tokens ({budgetPercent}%)
                      </span>
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-[#262626] overflow-hidden">
                    <div
                      className="h-full bg-zinc-300 transition-all duration-300"
                      style={{ width: `${budgetPercent}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <input
                  type="text"
                  value={fileFilter}
                  onChange={(e) => setFileFilter(e.target.value)}
                  placeholder="Filter scanned files (.cs, .py, .ts, .md)..."
                  className="flex-1 px-3 py-1.5 rounded-lg bg-[#111111] border border-zinc-800 text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="px-2.5 py-1 rounded-md text-xs bg-[#262626] hover:bg-[#303030] text-zinc-200 transition-colors"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={handleDeselectAll}
                    className="px-2.5 py-1 rounded-md text-xs bg-[#262626] hover:bg-[#303030] text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    Deselect All
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-zinc-800/90 bg-[#111111] max-h-64 overflow-y-auto divide-y divide-zinc-800/50">
                {filteredFiles.length === 0 ? (
                  <div className="py-8 text-center text-xs text-zinc-500">
                    No matching code files found in this directory.
                  </div>
                ) : (
                  filteredFiles.map((file) => {
                    const isChecked = checkedPaths.has(file.relative_path);
                    return (
                      <div
                        key={file.relative_path}
                        onClick={() => toggleFile(file.relative_path)}
                        className={`flex items-center justify-between px-3.5 py-2 text-xs cursor-pointer transition-colors ${
                          isChecked
                            ? "bg-[#1A1A1A] hover:bg-[#222222]"
                            : "hover:bg-[#181818] opacity-55"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#262626] text-zinc-300">
                            {isChecked ? "IN" : "OUT"}
                          </span>
                          <span className="font-mono text-zinc-200 truncate">
                            {file.relative_path}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 font-mono text-[11px] text-zinc-400">
                          <span>{(file.size_bytes / 1024).toFixed(1)} KB</span>
                          <span>{file.tokens.toLocaleString()} tok</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-800/80 bg-[#1F1F1F]">
          <div>
            {currentWorkspace && (
              <button
                type="button"
                onClick={handleUnlink}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-[#2A2A2A] transition-colors"
              >
                Unlink Folder
              </button>
            )}
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-[#2A2A2A] transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmAssign}
              disabled={!scanResult}
              className="px-4 py-1.5 rounded-lg bg-zinc-200 hover:bg-white disabled:opacity-40 text-xs font-medium text-zinc-900 transition-colors"
            >
              Apply ({checkedPaths.size} files)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
