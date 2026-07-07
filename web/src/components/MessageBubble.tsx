"use client";

import { ExternalLink, User, CheckCircle, AlertCircle } from "lucide-react";
import type { Message, Source } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
}

function renderMarkdown(text: string): string {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^---$/gm, "<hr>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    )
    .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
    .replace(/^[\*\-] (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^([^<].+)$/gm, function (m) {
      if (m.match(/^<(h[1-3]|ul|ol|li|blockquote|hr|pre)/)) return m;
      return m;
    });

  html = "<p>" + html + "</p>";
  html = html.replace(/<p><\/p>/g, "");
  html = html.replace(
    /\[citation:(\d+)\]/g,
    '<sup class="citation" data-source-index="$1">$1</sup>'
  );
  return html;
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

function SourcePill({ source, index }: { source: Source; index: number }) {
  return (
    <a
      href={source.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-[5px] px-[3px] pr-[9px] py-[3px]
                 rounded-full bg-[var(--color-surface-raised)]
                 text-[var(--color-text-secondary)] text-xs font-medium
                 border border-[var(--color-border)]
                 hover:border-[var(--color-accent-border)] hover:text-[var(--color-text-primary)]
                 hover:bg-[var(--color-accent-subtle)] hover:shadow-[var(--shadow-xs)]
                 transition-all duration-150 max-w-[240px] min-h-[26px]
                 group"
    >
      <span className="inline-flex items-center justify-center w-[18px] h-[18px]
                     rounded-full bg-[var(--color-accent-subtle)]
                     text-[var(--color-accent-text)] text-[0.55rem] font-bold shrink-0
                     group-hover:bg-[var(--color-accent)] group-hover:text-[var(--color-text-on-accent)]
                     transition-colors duration-150">
        {index + 1}
      </span>
      <span className="truncate">{source.title || extractDomain(source.url)}</span>
      <ExternalLink size={10} className="shrink-0 text-[var(--color-text-quaternary)] opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
    </a>
  );
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const confidence = message.confidence != null ? Math.round(message.confidence * 100) : null;
  const timestamp = new Date(message.timestamp || Date.now()).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`flex gap-3.5 w-full animate-[message-in_350ms_ease]
        ${isUser ? "flex-row-reverse self-end max-w-[640px]" : "self-start max-w-[820px]"}`}
    >
      {/* Avatar */}
      <div
        className={`shrink-0 w-[32px] h-[32px] rounded-full flex items-center justify-center
          ${isUser
            ? "bg-[var(--color-surface-overlay)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"
            : "bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-accent-hover)] text-[var(--color-text-on-accent)] shadow-[var(--shadow-sm)]"
          }`}
        aria-hidden="true"
      >
        {isUser ? <User size={15} /> : <span className="text-xs font-bold">R</span>}
      </div>

      {/* Content */}
      <div
        className={`flex flex-col gap-2 min-w-0
          ${isUser ? "items-end" : "flex-1"}`}
      >
        {/* Bubble */}
        {isUser ? (
          <div
            className="px-3.5 py-3 bg-[var(--color-surface-raised)] border border-[var(--color-border)]
                       rounded-[16px] rounded-br-[6px] text-[0.9375rem] leading-relaxed
                       shadow-[var(--shadow-xs)]"
          >
            {message.content}
          </div>
        ) : (
          <div
            className="markdown text-[0.9375rem] leading-relaxed w-full"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
          />
        )}

        {/* Sources + Confidence */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
            {message.sources.slice(0, 5).map((src, i) => (
              <SourcePill key={i} source={src} index={i} />
            ))}
            {message.sources.length > 5 && (
              <span className="text-xs text-[var(--color-text-quaternary)] font-medium px-1">
                +{message.sources.length - 5} more
              </span>
            )}
            {confidence != null && (
              <span
                className={`inline-flex items-center gap-1 px-[9px] py-[3px] rounded-full text-xs font-medium
                  ${confidence >= 70
                    ? "bg-[var(--color-success-subtle)] text-[var(--color-success-text)]"
                    : confidence >= 40
                    ? "bg-[var(--color-accent-subtle)] text-[var(--color-accent-text)]"
                    : "bg-[var(--color-error-subtle)] text-[var(--color-error-text)]"
                  }`}
              >
                {confidence >= 70 ? <CheckCircle size={10} /> : <AlertCircle size={10} />}
                {confidence}% confidence
              </span>
            )}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[0.65rem] text-[var(--color-text-quaternary)] px-1 font-mono">
          {timestamp}
        </span>
      </div>
    </div>
  );
}
