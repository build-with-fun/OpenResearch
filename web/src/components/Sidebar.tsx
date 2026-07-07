"use client";

import { Moon, Sun, Plus, Search, Trash2, History } from "lucide-react";
import { useEffect, useState } from "react";
import type { Conversation } from "@/lib/types";

interface SidebarProps {
  conversations: Conversation[];
  activeConvId: string | null;
  onNewChat: () => void;
  onSwitchConv: (id: string) => void;
  onDeleteConv: (id: string) => void;
  onClearAll: () => void;
  isResearching: boolean;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-[var(--color-signal)]",
  done: "bg-[var(--color-success)]",
  error: "bg-[var(--color-error)]",
};

export default function Sidebar({
  conversations,
  activeConvId,
  onNewChat,
  onSwitchConv,
  onDeleteConv,
  onClearAll,
  isResearching,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("openresearch_theme");
    if (saved === "light" || saved === "dark") {
      setTheme(saved);
    } else {
      setTheme(window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("openresearch_theme", next);
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm sm:hidden animate-[fade-in_200ms_ease]"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          fixed sm:relative z-40 h-full w-[280px] shrink-0
          bg-[var(--color-surface)] border-r border-[var(--color-border-subtle)]
          flex flex-col
          transition-transform duration-300 ease-out
          ${mobileOpen ? "translate-x-0" : "-translate-x-full sm:translate-x-0"}
          shadow-[var(--shadow-lg)]
          sm:shadow-none
        `}
        aria-label="Conversation sidebar"
      >
        {/* Header */}
        <div className="px-4 pt-5 pb-4 flex items-center gap-3 border-b border-[var(--color-border-subtle)]">
          <span className="text-[var(--color-accent)] shrink-0">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="2.25" fill="currentColor" />
              <path d="M12 1.5v4M12 18.5v4M1.5 12h4M18.5 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="text-[1.0625rem] font-[650] tracking-[-0.02em] text-[var(--color-text-primary)]">
            OpenResearch
          </span>
        </div>

        {/* New Chat */}
        <div className="px-3 pt-3 pb-2">
          <button
            onClick={() => { onNewChat(); onMobileClose(); }}
            className="flex items-center gap-2.5 w-full px-3.5 py-2.5 text-sm font-medium
                       bg-[var(--color-accent)] text-[var(--color-text-on-accent)]
                       rounded-[10px] hover:bg-[var(--color-accent-hover)]
                       transition-all duration-150 active:scale-[0.98]
                       shadow-[var(--shadow-sm)]"
          >
            <Plus size={18} />
            <span>New Research</span>
            <kbd className="ml-auto font-mono text-[0.625rem] px-1.5 py-0.5
                         bg-black/15 text-[var(--color-text-on-accent)] rounded
                         leading-none hidden sm:inline">
              ⌘N
            </kbd>
          </button>
        </div>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto px-2 pb-3 sidebar-scroll">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
              <History size={20} className="text-[var(--color-text-quaternary)]" />
              <span className="text-sm text-[var(--color-text-tertiary)]">
                No conversations yet
              </span>
              <span className="text-xs text-[var(--color-text-quaternary)]">
                Start a new research to begin
              </span>
            </div>
          ) : (
            <div className="space-y-0.5 pt-1">
              <div className="px-3 py-1.5 text-[0.65rem] font-semibold uppercase tracking-[0.08em]
                            text-[var(--color-text-quaternary)]">
                History
              </div>
              {conversations.map((conv, idx) => (
                <div
                  key={conv.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    if (!isResearching) {
                      onSwitchConv(conv.id);
                      onMobileClose();
                    }
                  }}
                  onKeyDown={(e) => {
                    if ((e.key === "Enter" || e.key === " ") && !isResearching) {
                      e.preventDefault();
                      onSwitchConv(conv.id);
                      onMobileClose();
                    }
                  }}
                  className={`
                    group relative flex items-start gap-2.5 w-full px-3 py-2.5 rounded-[10px] text-sm text-left
                    transition-all duration-150
                    ${conv.id === activeConvId
                      ? "bg-[var(--color-accent-subtle)] text-[var(--color-text-primary)]"
                      : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
                    }
                    ${isResearching ? "opacity-50 cursor-default" : "cursor-pointer"}
                    animate-[fade-in_300ms_ease]
                  `}
                  style={{ animationDelay: `${idx * 30}ms`, animationFillMode: "both" }}
                >
                  <span className="shrink-0 mt-1">
                    {conv.status === "done" ? (
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-[var(--color-success-text)]">
                        <path d="M3 7.5L6 10.5L11 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : conv.status === "error" ? (
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-[var(--color-error-text)]">
                        <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                      </svg>
                    ) : (
                      <span className="flex items-center justify-center w-[14px] h-[14px]">
                        <span className="w-2 h-2 rounded-full bg-[var(--color-signal)] animate-[pulse-dot_1.6s_ease-in-out_infinite]" />
                      </span>
                    )}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{conv.query.slice(0, 60)}</div>
                    <div className="text-[0.65rem] text-[var(--color-text-quaternary)] mt-0.5 font-mono">
                      {formatDate(conv.createdAt)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConv(conv.id);
                    }}
                    className="shrink-0 flex items-center justify-center w-6 h-6 rounded-md
                               opacity-0 group-hover:opacity-100 focus-visible:opacity-100
                               text-[var(--color-text-tertiary)] hover:text-[var(--color-error-text)]
                               hover:bg-[var(--color-error-subtle)]
                               transition-all duration-150"
                    aria-label={`Delete conversation: ${conv.query}`}
                  >
                    <Trash2 size={12} />
                  </button>
                  </div>
                ))}
              </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-1">
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 flex-1 px-3 py-2 rounded-[10px] text-sm
                         text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]
                         hover:text-[var(--color-text-primary)] transition-all duration-150"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              <span>{theme === "dark" ? "Light" : "Dark"}</span>
            </button>
            {conversations.length > 0 && (
              <button
                onClick={onClearAll}
                className="flex items-center justify-center w-9 h-9 rounded-[10px]
                           text-[var(--color-text-tertiary)] hover:bg-[var(--color-surface-hover)]
                           hover:text-[var(--color-error-text)] transition-all duration-150"
                aria-label="Clear all conversations"
                title="Clear all conversations"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
