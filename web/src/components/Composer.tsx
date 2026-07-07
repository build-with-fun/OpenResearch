"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { ArrowUp, Zap, Timer, Layers } from "lucide-react";
import type { Depth } from "@/lib/types";
import { DEPTH_HINTS } from "@/lib/types";

interface ComposerProps {
  onSend: (query: string, depth: Depth) => void;
  disabled: boolean;
  initialDepth?: Depth;
}

const DEPTHS: Depth[] = ["quick", "standard", "deep", "deeper"];

const DEPTH_ICONS: Record<Depth, typeof Zap> = {
  quick: Zap,
  standard: Timer,
  deep: Layers,
  deeper: Layers,
};

export default function Composer({ onSend, disabled, initialDepth }: ComposerProps) {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState<Depth>(initialDepth || "standard");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialDepth) setDepth(initialDepth);
  }, [initialDepth]);

  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, depth);
    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="shrink-0 no-print">
      <div className="px-4 sm:px-6 pt-3 pb-4 bg-[var(--color-canvas)]">
        <form onSubmit={handleSubmit} className="max-w-[820px] mx-auto w-full">
          {/* Depth selector */}
          <div className="flex items-center justify-between gap-3 mb-2 px-1">
            <div className="inline-flex p-[2px] bg-[var(--color-surface-overlay)]
                            rounded-full gap-[2px]">
              {DEPTHS.map((d) => {
                const Icon = DEPTH_ICONS[d];
                return (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDepth(d)}
                    className={`inline-flex items-center gap-[6px] px-3 py-[5px] min-h-[24px]
                               rounded-full text-xs font-medium border-none
                               transition-all duration-150 cursor-pointer
                               ${
                                 depth === d
                                   ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] shadow-[var(--shadow-sm)]"
                                   : "bg-transparent text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
                               }`}
                  >
                    <span className="flex gap-[2px]">
                      {[...Array(d === "deeper" ? 4 : 3)].map((_, j) => (
                        <span
                          key={j}
                          className="w-[3px] h-[3px] rounded-full bg-current"
                          style={{
                            opacity:
                              d === "quick"
                                ? j === 0 ? 1 : 0.3
                                : d === "standard"
                                ? j < 2 ? 1 : 0.3
                                : 1,
                          }}
                        />
                      ))}
                    </span>
                    <Icon size={12} />
                    <span className="capitalize">{d}</span>
                  </button>
                );
              })}
            </div>
            <span className="text-[0.6875rem] text-[var(--color-text-tertiary)] hidden sm:block">
              {DEPTH_HINTS[depth]}
            </span>
          </div>

          {/* Input bar */}
          <div
            className={`flex items-end gap-2 bg-[var(--color-surface)]
                         border border-[var(--color-border)] rounded-[14px]
                         px-4 py-2 transition-all duration-150
                         ${disabled ? "opacity-60" : ""}
                         hover:border-[var(--color-border-strong)]`}
          >
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                autoResize();
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask any research question..."
              rows={1}
              disabled={disabled}
              className="flex-1 border-none outline-none focus:outline-none focus-visible:outline-none bg-transparent
                         font-sans text-[0.9375rem] text-[var(--color-text-primary)]
                         resize-none min-h-[24px] max-h-[200px] leading-normal py-2
                         placeholder:text-[var(--color-text-tertiary)]
                         disabled:opacity-60"
              aria-label="Research question"
            />
            <button
              type="submit"
              disabled={!query.trim() || disabled}
              className="shrink-0 flex items-center justify-center w-9 h-9 rounded-[10px]
                         border-none bg-[var(--color-accent)] text-[var(--color-text-on-accent)]
                         hover:bg-[var(--color-accent-hover)] active:scale-[0.94]
                         transition-all duration-150
                         disabled:opacity-35 disabled:cursor-not-allowed disabled:hover:scale-100"
              aria-label="Send message"
            >
              <ArrowUp size={18} />
            </button>
          </div>

          {/* Hint */}
          <div className="flex justify-center pt-2">
            <span className="text-[0.6875rem] text-[var(--color-text-tertiary)]">
              Press <kbd className="inline-block px-[5px] py-px font-mono text-[0.6rem]
                               border border-[var(--color-border)] rounded
                               bg-[var(--color-surface-overlay)] leading-[1.3]">Enter</kbd> to send ·
              <kbd className="inline-block px-[5px] py-px font-mono text-[0.6rem]
                             border border-[var(--color-border)] rounded
                             bg-[var(--color-surface-overlay)] leading-[1.3] ml-1">Shift+Enter</kbd> for new line
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
