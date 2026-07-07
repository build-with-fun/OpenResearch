"use client";

import { useMemo } from "react";
import { Check, Loader2, Search, Brain, FileText, Sparkles, ListOrdered } from "lucide-react";
import { PIPELINE_STEPS, STAGE_ORDER } from "@/lib/types";
import type { StatusEvent } from "@/lib/types";

interface PipelineTrackerProps {
  statusLog: StatusEvent[];
  currentStep: string;
  elapsed: number;
  visible: boolean;
}

const STAGE_META: Record<string, { label: string; icon: typeof Search; description: string }> = {
  planner: { label: "Plan", icon: ListOrdered, description: "Analyzing query and creating plan" },
  search: { label: "Search", icon: Search, description: "Searching for relevant sources" },
  extract: { label: "Extract", icon: FileText, description: "Extracting and ranking content" },
  reason: { label: "Reason", icon: Brain, description: "Deep reasoning and analysis" },
  synthesize: { label: "Synthesize", icon: Sparkles, description: "Synthesizing final answer" },
};

function getStageIndex(step: string): number {
  const lower = step.toLowerCase();
  for (const stage of PIPELINE_STEPS) {
    if (lower.includes(stage)) return STAGE_ORDER[stage];
  }
  if (lower === "initializing") return -1;
  if (lower === "complete" || lower === "done" || lower === "error") return 999;
  return -1;
}

function getStageKey(step: string): string {
  const lower = step.toLowerCase();
  for (const stage of PIPELINE_STEPS) {
    if (lower.includes(stage)) return stage;
  }
  if (lower === "initializing") return "initializing";
  if (lower === "complete" || lower === "done" || lower === "error") return "complete";
  return step;
}

const formatTime = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

export default function PipelineTracker({
  statusLog,
  currentStep,
  elapsed,
  visible,
}: PipelineTrackerProps) {
  const currentIdx = getStageIndex(currentStep);
  const currentStageKey = getStageKey(currentStep);
  const isComplete = currentStageKey === "complete";

  const stageEvents = useMemo(() => {
    const grouped: Record<string, StatusEvent[]> = {};
    for (const stage of [...PIPELINE_STEPS, "initializing"]) {
      grouped[stage] = [];
    }
    for (const evt of statusLog) {
      const key = getStageKey(evt.step);
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(evt);
    }
    return grouped;
  }, [statusLog]);

  const activeMessages = useMemo(() => {
    if (isComplete || !currentStageKey || currentStageKey === "initializing") return [];
    const events = stageEvents[currentStageKey] || [];
    const seen = new Set<string>();
    return events.filter((e) => {
      if (seen.has(e.message)) return false;
      seen.add(e.message);
      return true;
    });
  }, [stageEvents, currentStageKey, isComplete]);

  const latestEvent = statusLog[statusLog.length - 1];
  const latestMessage = latestEvent?.message || "";

  if (!visible) return null;

  return (
    <div className="shrink-0 no-print">
      {/* Header bar */}
      <div className="flex items-center gap-2.5 px-4 sm:px-6 py-2.5
                      border-b border-[var(--color-border-subtle)]
                      bg-[var(--color-surface-raised)]">
        <div className={`w-2 h-2 rounded-full shrink-0
          ${isComplete ? "bg-[var(--color-success)]" : "bg-[var(--color-signal)] animate-pulse"}`} />
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          {isComplete ? "Research complete" : "Researching"}
        </span>
        <span className="text-xs text-[var(--color-text-tertiary)] font-mono tabular-nums">
          {formatTime(elapsed)}
        </span>
        {latestMessage && !isComplete && (
          <span className="text-xs text-[var(--color-text-quaternary)] truncate ml-auto hidden sm:block max-w-[300px]">
            {latestMessage}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="border-b border-[var(--color-border-subtle)]
                      bg-[var(--color-surface)]">
        <div className="max-w-[820px] mx-auto px-4 sm:px-6 py-3.5 space-y-3.5">
          {/* Stage progress chips */}
          <div className="flex items-center gap-1.5">
            {PIPELINE_STEPS.map((stage, i) => {
              const meta = STAGE_META[stage];
              const stageIdx = STAGE_ORDER[stage];
              const isDone = stageIdx < currentIdx || (isComplete && stageIdx < PIPELINE_STEPS.length);
              const isActive = stageIdx === currentIdx && !isComplete;
              const isPending = stageIdx > currentIdx;

              return (
                <div key={stage} className="flex items-center flex-1 min-w-0 gap-1.5">
                  <div
                    className={`
                      flex items-center gap-1.5 px-2.5 py-1.5 rounded-[8px] text-[0.7rem] font-semibold
                      transition-all duration-300
                      ${isDone
                        ? "text-[var(--color-success-text)] bg-[var(--color-success-subtle)]"
                        : ""}
                      ${isActive
                        ? "text-[var(--color-signal-text)] bg-[var(--color-signal-subtle)] ring-1 ring-[var(--color-signal-border)]"
                        : ""}
                      ${isPending
                        ? "text-[var(--color-text-quaternary)]"
                        : ""}
                      ${isComplete
                        ? "text-[var(--color-success-text)] bg-[var(--color-success-subtle)]"
                        : ""}
                    `}
                  >
                    {isDone || isComplete ? (
                      <Check size={10} className="shrink-0" />
                    ) : isActive ? (
                      <div className="w-[10px] h-[10px] shrink-0 flex items-center justify-center">
                        <div className="w-[6px] h-[6px] rounded-full bg-[var(--color-signal)] animate-pulse" />
                      </div>
                    ) : (
                      <div className="w-[10px] h-[10px] shrink-0 flex items-center justify-center">
                        <div className="w-[5px] h-[5px] rounded-full bg-[var(--color-border-strong)]" />
                      </div>
                    )}
                    <span className="whitespace-nowrap">{meta.label}</span>
                  </div>
                  {i < PIPELINE_STEPS.length - 1 && (
                    <div
                      className={`flex-1 h-[2px] rounded-full transition-colors duration-300
                        ${isDone ? "bg-[var(--color-success-border)]" : "bg-[var(--color-border-subtle)]"}`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Active stage thoughts */}
          {isComplete && (
            <div className="flex items-center gap-2 text-sm text-[var(--color-success-text)] font-medium animate-[fade-in_300ms_ease]">
              <Check size={16} />
              Research completed in {formatTime(elapsed)}
            </div>
          )}

          {currentStageKey === "initializing" && stageEvents["initializing"]?.length > 0 && (
            <div className="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)] animate-[fade-in_200ms_ease]">
              <Loader2 size={12} className="animate-spin shrink-0 text-[var(--color-signal)]" />
              {stageEvents["initializing"].slice(-1)[0]?.message || "Initializing..."}
            </div>
          )}

          {activeMessages.length > 0 && (
            <div className="space-y-1.5 animate-[fade-in_200ms_ease]">
              <div className="ml-[5px] space-y-1">
                {activeMessages.slice(-6).map((evt, i) => (
                  <div key={i} className="text-xs text-[var(--color-text-secondary)] leading-relaxed flex gap-2.5 items-start">
                    <span className="text-[var(--color-text-quaternary)] shrink-0 font-mono tabular-nums w-[52px] text-right">
                      {new Date(evt.timestamp).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" })}
                    </span>
                    <span className="flex-1 min-w-0">{evt.message}</span>
                  </div>
                ))}
                {/* Typing dots */}
                <div className="flex gap-1 items-center pt-0.5 pl-[60px]">
                  <span className="w-[5px] h-[5px] rounded-full bg-[var(--color-signal)] animate-[bounce-dot_1.2s_ease-in-out_infinite]" />
                  <span className="w-[5px] h-[5px] rounded-full bg-[var(--color-signal)] animate-[bounce-dot_1.2s_ease-in-out_infinite]" style={{ animationDelay: "0.2s" }} />
                  <span className="w-[5px] h-[5px] rounded-full bg-[var(--color-signal)] animate-[bounce-dot_1.2s_ease-in-out_infinite]" style={{ animationDelay: "0.4s" }} />
                </div>
              </div>
            </div>
          )}

          {/* Completed stages summary */}
          {currentIdx >= 1 && !isComplete && (
            <div className="space-y-1 pt-1 border-t border-[var(--color-border-subtle)] animate-[fade-in_300ms_ease]">
              {PIPELINE_STEPS.slice(0, currentIdx).map((stage) => {
                const events = stageEvents[stage] || [];
                const meta = STAGE_META[stage];
                const lastMsg = events
                  .map((e) => e.message)
                  .filter(Boolean)
                  .pop();
                return (
                  <div key={stage} className="flex items-start gap-2 text-xs text-[var(--color-text-tertiary)] leading-relaxed">
                    <Check size={11} className="shrink-0 mt-0.5 text-[var(--color-success)]" />
                    <span className="font-medium text-[var(--color-text-secondary)] shrink-0 min-w-0">
                      {meta.label}
                    </span>
                    {lastMsg && (
                      <>
                        <span className="text-[var(--color-text-quaternary)] hidden sm:inline">·</span>
                        <span className="truncate text-[var(--color-text-quaternary)] hidden sm:inline">{lastMsg}</span>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
