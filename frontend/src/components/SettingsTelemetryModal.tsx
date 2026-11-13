"use client";

import React, { useState } from "react";
import { TelemetryData } from "@/lib/types";
import { fetchTelemetry } from "@/lib/api";
import { MODEL_DIRECTORY_DATA } from "@/lib/constants";

interface SettingsTelemetryModalProps {
  isOpen: boolean;
  onClose: () => void;
  telemetry: TelemetryData | null;
  onTelemetryUpdated: (updated: TelemetryData) => void;
}

export default function SettingsTelemetryModal({
  isOpen,
  onClose,
  telemetry,
  onTelemetryUpdated,
}: SettingsTelemetryModalProps) {
  const [activeTab, setActiveTab] = useState<"telemetry" | "models">("telemetry");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  if (!isOpen) return null;

  const handleRefreshTelemetry = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const fresh = await fetchTelemetry();
      onTelemetryUpdated(fresh);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to refresh telemetry"
      );
    } finally {
      setRefreshing(false);
    }
  };

  const remainingFormatted =
    telemetry?.remaining_credits !== null &&
    telemetry?.remaining_credits !== undefined
      ? `$${telemetry.remaining_credits.toFixed(4)}`
      : "$0.0000";

  const filteredModels = MODEL_DIRECTORY_DATA.filter((m) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      m.name.toLowerCase().includes(q) ||
      m.roleBadge.toLowerCase().includes(q) ||
      m.specializedFor.some((s) => s.toLowerCase().includes(q)) ||
      m.description.toLowerCase().includes(q)
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl max-h-[88vh] rounded-2xl border border-zinc-800 bg-[#1A1A1A] shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-zinc-800/80 bg-[#1F1F1F]">
          <div className="flex items-center gap-6">
            <h2 className="text-sm font-semibold text-zinc-100">
              Settings and Telemetry
            </h2>
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-[#141414] border border-zinc-800">
              <button
                type="button"
                onClick={() => setActiveTab("telemetry")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "telemetry"
                    ? "bg-[#2A2A2A] text-zinc-100"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Telemetry
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("models")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  activeTab === "models"
                    ? "bg-[#2A2A2A] text-zinc-100"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Model Directory and Stats
              </button>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-2.5 py-1 rounded-md text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[#2A2A2A] transition-colors"
          >
            Close
          </button>
        </div>

        {/* Tab 1: Telemetry */}
        {activeTab === "telemetry" && (
          <div className="p-6 space-y-5 overflow-y-auto">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div className="p-4 rounded-xl bg-[#141414] border border-zinc-800/90">
                <div className="text-zinc-400 text-xs font-medium mb-1.5">
                  Remaining Credits
                </div>
                <div className="text-lg font-mono font-semibold text-zinc-100 truncate">
                  {remainingFormatted}
                </div>
                <div className="text-[11px] text-zinc-500 mt-1">
                  {telemetry?.status_message || "OpenRouter Live"}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#141414] border border-zinc-800/90">
                <div className="text-zinc-400 text-xs font-medium mb-1.5">
                  Total Sessions
                </div>
                <div className="text-lg font-mono font-semibold text-zinc-100">
                  {telemetry?.total_sessions ?? 0}
                </div>
                <div className="text-[11px] text-zinc-500 mt-1">
                  {telemetry?.total_messages ?? 0} stored messages
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#141414] border border-zinc-800/90">
                <div className="text-zinc-400 text-xs font-medium mb-1.5">
                  Total Tokens Used
                </div>
                <div className="text-lg font-mono font-semibold text-zinc-100">
                  {(telemetry?.total_tokens_used ?? 0).toLocaleString()}
                </div>
                <div className="text-[11px] text-zinc-500 mt-1">
                  SQLite session ledger
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#141414] border border-zinc-800/80 text-xs text-zinc-400 leading-relaxed space-y-1">
              <div className="text-zinc-200 font-medium mb-1">
                OpenRouter Key Integration
              </div>
              <p>
                API Key is loaded directly from your local <code className="text-zinc-300">.env</code> file. No keys are exposed to the client.
              </p>
              <p className="text-zinc-500 text-[11px]">
                Tokens are billed strictly per call without recurring subscription caps.
              </p>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-[#141414] border border-zinc-800 text-xs text-rose-400">
                {error}
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-zinc-800/70">
              <button
                type="button"
                onClick={handleRefreshTelemetry}
                disabled={refreshing}
                className="px-4 py-1.5 rounded-lg bg-[#262626] hover:bg-[#303030] disabled:opacity-50 text-xs font-medium text-zinc-200 transition-colors"
              >
                {refreshing ? "Refreshing..." : "Refresh Live"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-zinc-200 hover:bg-white text-xs font-medium text-zinc-900 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Model Directory and Stats */}
        {activeTab === "models" && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Search Bar */}
            <div className="px-6 py-3 border-b border-zinc-800/80 bg-[#161616]">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search models by role (e.g. C#, bugs, audio, project, free)..."
                className="w-full bg-[#1F1F1F] border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-500 rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-700"
              />
            </div>

            {/* Model Cards List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-3.5">
              {filteredModels.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-[#141414] border border-zinc-800/90 space-y-2.5"
                >
                  {/* Top Row: Name, Provider, Role Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-zinc-100">
                        {item.name}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {item.provider}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-mono text-zinc-300 bg-[#242424] border border-zinc-700/60">
                      {item.roleBadge}
                    </span>
                  </div>

                  {/* Stat Metrics Row: Power, Cost, Speed, Context */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-zinc-800/60 text-[11px] font-mono">
                    <div>
                      <span className="text-zinc-500 block text-[10px]">POWER</span>
                      <span className="text-zinc-200">{item.powerRating}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block text-[10px]">COST / 1M</span>
                      <span className="text-zinc-200">{item.costLabel}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block text-[10px]">SPEED</span>
                      <span className="text-zinc-200">{item.speedRating}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block text-[10px]">CONTEXT</span>
                      <span className="text-zinc-200">{item.contextWindow}</span>
                    </div>
                  </div>

                  {/* Best For Tags */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {item.specializedFor.map((tag, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] px-2 py-0.5 rounded bg-[#1C1C1C] text-zinc-400 border border-zinc-800"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* Description */}
                  <p className="text-[11px] text-zinc-400 leading-relaxed pt-0.5">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-zinc-800/80 bg-[#1F1F1F] flex items-center justify-between text-xs text-zinc-500">
              <span>{filteredModels.length} models curated for game and software dev</span>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-zinc-200 hover:bg-white text-xs font-medium text-zinc-900 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
