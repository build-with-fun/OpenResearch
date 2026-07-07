"use client";

import { useState } from "react";
import { ChevronDown, ExternalLink, Globe, FileText } from "lucide-react";
import type { Source } from "@/lib/types";

interface SourcePanelProps {
  sources: Source[];
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const domain = extractDomain(source.url);
  const hasContent = source.snippet || source.content;
  const preview = (source.snippet || source.content || "").slice(0, 140);

  return (
    <a
      href={source.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 p-3 border border-[var(--color-border)]
                 rounded-[12px] bg-[var(--color-surface-raised)]
                 hover:border-[var(--color-accent-border)]
                 hover:shadow-[var(--shadow-md)]
                 hover:bg-[var(--color-accent-subtle)]
                 transition-all duration-200
                 animate-[card-in_300ms_ease]
                 group"
      style={{ animationFillMode: "both" }}
    >
      {/* Number badge */}
      <span className="shrink-0 w-[24px] h-[24px] flex items-center justify-center
                     rounded-[8px] text-[0.6rem] font-bold
                     bg-[var(--color-accent-subtle)] text-[var(--color-accent-text)]
                     group-hover:bg-[var(--color-accent)] group-hover:text-[var(--color-text-on-accent)]
                     transition-colors duration-150">
        {index + 1}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1 flex flex-col gap-1">
        <div className="flex items-center gap-1.5 text-[0.65rem] text-[var(--color-text-quaternary)]
                      uppercase tracking-[0.05em] font-medium">
          <Globe size={10} />
          <span className="truncate">{domain}</span>
        </div>

        <div className="text-xs text-[var(--color-text-primary)] font-medium leading-snug line-clamp-2
                      group-hover:text-[var(--color-accent-text)] transition-colors duration-150">
          {source.title || source.url || "Untitled"}
        </div>

        {hasContent && (
          <div className="text-[0.65rem] text-[var(--color-text-tertiary)] leading-relaxed line-clamp-2">
            {preview}
          </div>
        )}
      </div>

      {/* External link indicator */}
      <ExternalLink size={12} className="shrink-0 text-[var(--color-text-quaternary)]
                     opacity-0 group-hover:opacity-100 transition-opacity duration-150 mt-0.5" />
    </a>
  );
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div
      className={`border-t border-[var(--color-border-subtle)]
                  bg-[var(--color-surface)] shrink-0 no-print
                  transition-all duration-300 ease-out overflow-hidden
                  ${collapsed ? "max-h-[48px]" : "max-h-[340px]"}`}
    >
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2.5 w-full px-4 sm:px-6 py-3 min-h-[48px] shrink-0
                   hover:bg-[var(--color-surface-hover)] transition-colors duration-150
                   group"
        aria-expanded={!collapsed}
        aria-controls="sources-grid"
      >
        <FileText size={14} className="text-[var(--color-text-tertiary)]" />
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          Sources
        </span>
        <span className="text-xs font-mono bg-[var(--color-accent-subtle)]
                        text-[var(--color-accent-text)] px-[8px] py-[1px] rounded-full font-semibold">
          {sources.length}
        </span>
        <span className={`ml-auto text-[var(--color-text-tertiary)] transition-transform duration-200
                          group-hover:text-[var(--color-text-primary)]
                          ${collapsed ? "rotate-[-90deg]" : ""}`}>
          <ChevronDown size={14} />
        </span>
      </button>

      {/* Grid */}
      <div
        id="sources-grid"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 px-4 sm:px-6 pb-4 overflow-y-auto sources-scroll"
      >
        {sources.map((src, i) => (
          <SourceCard key={`${src.url}-${i}`} source={src} index={i} />
        ))}
      </div>
    </div>
  );
}
