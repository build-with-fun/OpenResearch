"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { setToastCallback } from "@/lib/research";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

interface Toast {
  id: number;
  message: string;
  type: string;
  exiting?: boolean;
}

let toastId = 0;

const TYPE_STYLES: Record<string, { icon: typeof Info; bg: string; border: string }> = {
  info: { icon: Info, bg: "bg-[var(--color-signal-subtle)]", border: "border-[var(--color-signal-border)]" },
  success: { icon: CheckCircle, bg: "bg-[var(--color-success-subtle)]", border: "border-[var(--color-success-border)]" },
  error: { icon: AlertCircle, bg: "bg-[var(--color-error-subtle)]", border: "border-[var(--color-error-border)]" },
};

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 200);
  }, []);

  const addToast = useCallback((message: string, type?: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type: type || "info" }]);

    const timer = setTimeout(() => {
      removeToast(id);
      timersRef.current.delete(id);
    }, 4000);
    timersRef.current.set(id, timer);
  }, [removeToast]);

  useEffect(() => {
    setToastCallback(addToast);
    return () => {
      setToastCallback(null);
      timersRef.current.forEach((t) => clearTimeout(t));
    };
  }, [addToast]);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const typeStyle = TYPE_STYLES[toast.type] || TYPE_STYLES.info;
        const IconEl = typeStyle.icon;

        return (
          <div
            key={toast.id}
            className={`
              flex items-center gap-2.5 px-4 py-3 rounded-[12px] text-sm
              bg-[var(--color-surface-raised)] border
              shadow-[var(--shadow-lg)] text-[var(--color-text-primary)]
              pointer-events-auto max-w-[420px] min-w-[280px]
              ${typeStyle.bg} ${typeStyle.border}
              ${toast.exiting ? "animate-[toast-out_200ms_ease]" : "animate-[toast-in_320ms_ease]"}
            `}
          >
            <IconEl size={16} className="shrink-0 text-[var(--color-text-secondary)]" />
            <span className="flex-1">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 flex items-center justify-center w-6 h-6 rounded-md
                         text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]
                         hover:bg-[var(--color-surface-overlay)] transition-colors"
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
