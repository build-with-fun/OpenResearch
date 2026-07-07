"use client";

interface EmptyStateProps {
  onSuggestionClick: (query: string) => void;
}

const SUGGESTIONS = [
  {
    label: "Quantum computing",
    detail: "Recent breakthroughs in error correction",
    query: "What are the most significant recent breakthroughs in quantum error correction?",
    gradient: "from-[var(--color-signal-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-signal-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-signal-text)]">
        <circle cx="9" cy="9" r="2.2" fill="currentColor" />
        <ellipse cx="9" cy="9" rx="7.5" ry="3" stroke="currentColor" strokeWidth="1.2" />
        <ellipse cx="9" cy="9" rx="7.5" ry="3" stroke="currentColor" strokeWidth="1.2" transform="rotate(60 9 9)" />
        <ellipse cx="9" cy="9" rx="7.5" ry="3" stroke="currentColor" strokeWidth="1.2" transform="rotate(120 9 9)" />
      </svg>
    ),
  },
  {
    label: "AI & employment",
    detail: "Economic impact across industries",
    query: "Compare how AI automation is reshaping employment across different industries right now",
    gradient: "from-[var(--color-accent-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-accent-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-accent-text)]">
        <path d="M3 16V10M7 16V6M11 16V3M14 16H2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Fusion energy",
    detail: "Commercial viability timeline",
    query: "What is the current state of fusion energy and when might it be commercially viable?",
    gradient: "from-[var(--color-success-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-success-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-success-text)]">
        <path d="M9.5 2L4 10h4.5L7 16l6-8H8.5L9.5 2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "AI regulation",
    detail: "Global approaches compared",
    query: "How are major governments approaching AI regulation right now, and where do their approaches differ?",
    gradient: "from-[var(--color-signal-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-signal-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-signal-text)]">
        <path d="M9 2v14M4.5 4.5h9M2.5 4.5L1 9a2 2 0 004 0L2.5 4.5zM15.5 4.5L14 9a2 2 0 004 0l-2.5-4.5zM6 16h6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Space exploration",
    detail: "Mars missions & beyond",
    query: "What are the latest developments in Mars exploration and how do different space agencies compare?",
    gradient: "from-[var(--color-accent-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-accent-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-accent-text)]">
        <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.2" />
        <path d="M9 3v3M9 12v3M3 9h3M12 9h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <circle cx="9" cy="9" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    label: "Biotech trends",
    detail: "Gene editing & therapeutics",
    query: "What are the most promising developments in CRISPR-based therapies currently in clinical trials?",
    gradient: "from-[var(--color-success-subtle)] to-[var(--color-surface-raised)]",
    border: "border-[var(--color-success-border)]",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-[var(--color-success-text)]">
        <path d="M9 2a7 7 0 100 14A7 7 0 009 2z" stroke="currentColor" strokeWidth="1.2" />
        <path d="M6 9h6M9 6v6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 overflow-y-auto">
      <div className="max-w-[680px] w-full mx-auto flex flex-col items-center animate-[fade-in_500ms_ease]">
        {/* Logo symbol */}
        <div className="mb-8 text-[var(--color-accent)]" aria-hidden="true">
          <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeWidth="1.3" opacity="0.5" />
            <circle cx="12" cy="12" r="2.25" fill="currentColor" />
            <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </div>

        {/* Heading */}
        <h1 className="font-[family-name:var(--font-spectral)] text-[2rem] sm:text-[2.25rem] font-medium italic
                       tracking-[-0.02em] mb-3 text-[var(--color-text-primary)] leading-[1.15] text-center">
          What would you like to research?
        </h1>

        <p className="text-[0.9375rem] text-[var(--color-text-secondary)] max-w-[460px] mb-10 leading-relaxed text-center">
          Ask any complex question. OpenResearch plans, searches, extracts, reasons, and
          synthesizes a comprehensive, cited answer.
        </p>

        {/* Bento grid suggestions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={s.label}
              onClick={() => onSuggestionClick(s.query)}
              className={`
                flex flex-col gap-1.5 p-4 rounded-[14px] text-left border
                bg-gradient-to-br ${s.gradient}
                ${s.border}
                text-[var(--color-text-secondary)]
                hover:border-opacity-100 hover:shadow-[var(--shadow-md)]
                transition-all duration-200 min-h-[80px] group
                animate-[slide-up_400ms_ease]
              `}
              style={{ animationDelay: `${i * 60}ms`, animationFillMode: "both" }}
            >
              <div className="flex items-center gap-2.5">
                <span className="flex items-center justify-center w-8 h-8 rounded-[10px]
                               bg-[var(--color-surface)] border border-[var(--color-border)]
                               group-hover:border-transparent group-hover:scale-105 transition-all duration-200">
                  {s.icon}
                </span>
                <span className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent-text)]
                              transition-colors duration-150">
                  {s.label}
                </span>
              </div>
              <span className="text-xs text-[var(--color-text-tertiary)] leading-relaxed ml-[42px]">
                {s.detail}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
