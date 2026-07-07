"use client";

import { useState, useCallback, useEffect } from "react";
import { Menu, Square, Copy, Trash2 } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import PipelineTracker from "@/components/PipelineTracker";
import SourcePanel from "@/components/SourcePanel";
import MessageBubble from "@/components/MessageBubble";
import EmptyState from "@/components/EmptyState";
import Composer from "@/components/Composer";
import ToastContainer from "@/components/Toast";
import { useResearch } from "@/lib/research";
import type { Depth } from "@/lib/types";

export default function Home() {
  const {
    conversations,
    activeConv,
    isResearching,
    pipelineStep,
    showPipeline,
    elapsed,
    sources,
    statusLog,
    startResearch,
    cancelResearch,
    newConversation,
    switchConversation,
    deleteConversation,
    clearAllConversations,
  } = useResearch();

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") {
        e.preventDefault();
        newConversation();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [newConversation]);

  const handleSend = useCallback(
    (query: string, depth: Depth) => {
      setMobileSidebarOpen(false);
      startResearch(query, depth);
    },
    [startResearch]
  );

  const handleSuggestionClick = useCallback(
    (query: string) => {
      handleSend(query, activeConv?.depth || "standard");
    },
    [handleSend, activeConv]
  );

  const handleCopyMarkdown = useCallback(async () => {
    if (!activeConv) return;
    const lastMsg = activeConv.messages.find((m) => m.role === "assistant");
    if (!lastMsg) return;

    let md = `# Research: ${activeConv.query}\n\n`;
    md += `**Depth**: ${activeConv.depth}  \n`;
    md += `**Date**: ${new Date().toLocaleDateString()}  \n\n---\n\n`;
    md += lastMsg.content || "";
    md += `\n\n---\n\n## Sources\n\n`;
    (activeConv.sources || []).forEach((src, i) => {
      md += `${i + 1}. **${src.title || "Untitled"}**  \n   ${src.url || "#"}  \n`;
    });

    try {
      await navigator.clipboard.writeText(md);
    } catch {
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research-${activeConv.query.slice(0, 30).replace(/[^a-z0-9]/gi, "_")}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [activeConv]);

  const hasResult = activeConv && activeConv.messages.some((m) => m.role === "assistant");

  // Avoid hydration mismatch
  if (!mounted) return null;

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConvId={activeConv?.id || null}
        onNewChat={newConversation}
        onSwitchConv={switchConversation}
        onDeleteConv={deleteConversation}
        onClearAll={clearAllConversations}
        isResearching={isResearching}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main area */}
      <main
        id="main-content"
        className="flex-1 flex flex-col h-full min-w-0 relative"
      >
        {/* Mobile menu button */}
        <button
          onClick={() => setMobileSidebarOpen(true)}
          className="sm:hidden absolute top-3 left-3 z-10 flex items-center justify-center
                     w-9 h-9 rounded-[10px] text-[var(--color-text-secondary)]
                     hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-text-primary)]
                     transition-colors duration-150"
          aria-label="Open conversation list"
        >
          <Menu size={18} />
        </button>

        {/* Chat Header */}
        {activeConv && (
          <div className="flex items-center gap-3 px-4 sm:px-6 py-3
                          border-b border-[var(--color-border-subtle)]
                          bg-[var(--color-surface)] shrink-0">
            <div className="flex flex-col gap-px min-w-0 flex-1">
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                Current Research
              </span>
              <span className="text-xs text-[var(--color-text-tertiary)] truncate">
                {activeConv.query}
              </span>
            </div>
            <div className="flex gap-1 shrink-0">
              {isResearching && (
                <button
                  onClick={cancelResearch}
                  className="flex items-center justify-center w-8 h-8 rounded-[9px]
                             text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]
                             hover:text-[var(--color-error-text)] transition-colors duration-150"
                  aria-label="Stop research"
                  title="Stop research"
                >
                  <Square size={15} />
                </button>
              )}
              {hasResult && !isResearching && (
                <button
                  onClick={handleCopyMarkdown}
                  className="flex items-center justify-center w-8 h-8 rounded-[9px]
                             text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]
                             hover:text-[var(--color-text-primary)] transition-colors duration-150"
                  aria-label="Copy as Markdown"
                  title="Copy as Markdown"
                >
                  <Copy size={15} />
                </button>
              )}
              <button
                onClick={newConversation}
                className="flex items-center justify-center w-8 h-8 rounded-[9px]
                           text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]
                           hover:text-[var(--color-text-primary)] transition-colors duration-150"
                aria-label="New conversation"
                title="New conversation"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        )}

        {/* Pipeline Tracker */}
        <PipelineTracker
          statusLog={statusLog}
          currentStep={pipelineStep}
          elapsed={elapsed}
          visible={showPipeline}
        />

        {/* Scrollable messages area */}
        {!activeConv ? (
          <EmptyState onSuggestionClick={handleSuggestionClick} />
        ) : (
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 messages-scroll">
            <div className="max-w-[820px] mx-auto flex flex-col gap-5">
              {activeConv.messages.length === 0 && !isResearching && (
                <div className="flex-1 flex items-center justify-center text-sm text-[var(--color-text-tertiary)] py-12">
                  Send a query to start researching
                </div>
              )}
              {activeConv.messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              {/* Loading indicator for empty research state */}
              {isResearching && activeConv.messages.length === 0 && (
                <div className="flex items-center justify-center gap-2 py-12 text-sm text-[var(--color-text-tertiary)]">
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-signal)] animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-signal)] animate-bounce" style={{ animationDelay: "0.15s" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-signal)] animate-bounce" style={{ animationDelay: "0.3s" }} />
                  <span className="ml-1">Starting research...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Source Panel */}
        <SourcePanel sources={sources} />

        {/* Composer */}
        <Composer
          onSend={handleSend}
          disabled={isResearching}
          initialDepth={activeConv?.depth || "standard"}
        />
      </main>

      <ToastContainer />
    </div>
  );
}
