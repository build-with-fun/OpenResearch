"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { Depth, Source, Conversation, ResearchStatus, StatusEvent, PipelineStep } from "./types";
import { STEP_LABELS, STAGE_ORDER } from "./types";

const STORAGE_KEY = "openresearch_conversations";
const ACTIVE_KEY = "openresearch_active_conv";

function saveConversations(convs: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
  } catch {}
}

function loadConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function useResearch() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeConvId, setActiveConvId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(ACTIVE_KEY);
    } catch {
      return null;
    }
  });
  const [isResearching, setIsResearching] = useState(false);
  const [currentRid, setCurrentRid] = useState<string | null>(null);
  const [pipelineStep, setPipelineStep] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [showPipeline, setShowPipeline] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [statusLog, setStatusLog] = useState<StatusEvent[]>([]);

  const statusLogRef = useRef<StatusEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Persist conversations on change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Persist active conversation
  useEffect(() => {
    if (activeConvId) {
      localStorage.setItem(ACTIVE_KEY, activeConvId);
    } else {
      localStorage.removeItem(ACTIVE_KEY);
    }
  }, [activeConvId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const activeConv = conversations.find((c) => c.id === activeConvId) || null;

  const updateConv = useCallback(
    (id: string, updater: (c: Conversation) => Conversation) => {
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? updater(c) : c))
      );
    },
    []
  );

  const addStatusEvent = useCallback(
    (step: string, message: string, progress: number) => {
      const stage = STEP_LABELS[step] || step;
      const evt: StatusEvent = {
        step,
        stage: stage as StatusEvent["stage"],
        message,
        progress,
        timestamp: Date.now(),
      };
      statusLogRef.current = [...statusLogRef.current, evt];
      setStatusLog(statusLogRef.current);
    },
    []
  );

  const createConversation = useCallback(
    (query: string, depth: Depth): Conversation => {
      const conv: Conversation = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        query,
        depth,
        messages: [],
        sources: [],
        createdAt: Date.now(),
        status: "active",
      };
      setConversations((prev) => [conv, ...prev]);
      setActiveConvId(conv.id);
      setSources([]);
      setError(null);
      return conv;
    },
    []
  );

  const switchConversation = useCallback((id: string) => {
    if (isResearching) return;
    setActiveConvId(id);
    const conv = loadConversations().find((c) => c.id === id);
    if (conv) {
      setSources(conv.sources || []);
    } else {
      setSources([]);
    }
    setError(null);
    setShowPipeline(false);
  }, [isResearching]);

  const deleteConversation = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setActiveConvId((prev) => (prev === id ? null : prev));
  }, []);

  const clearAllConversations = useCallback(() => {
    setConversations([]);
    setActiveConvId(null);
    setSources([]);
    setShowPipeline(false);
    setError(null);
  }, []);

  // Timer
  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Polling fallback
  const startPolling = useCallback(
    (rid: string, convId: string) => {
      let attempts = 0;
      const maxAttempts = 300;

      pollRef.current = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch(`/api/research/${rid}/status`);
          if (!res.ok) return;
          const status: ResearchStatus = await res.json();
          const step = status.current_step || "";
          setPipelineStep(step);
          setProgress(status.progress || 0);
          if (step) {
            addStatusEvent(step, `Status: ${step}`, status.progress || 0);
          }

          if (status.status === "complete") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            await fetchResult(rid, convId);
            return;
          }

          if (status.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            handleError(status.error || "Research failed", convId);
            return;
          }

          if (attempts >= maxAttempts) {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            handleError("Research timed out", convId);
          }
        } catch {
          if (attempts > 3) console.warn("Poll error");
        }
      }, 1000);
    },
    []
  );

  // SSE connection
  const connectSSE = useCallback(
    (rid: string, convId: string) => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource(`/api/research/${rid}/stream`);
      eventSourceRef.current = es;

      es.addEventListener("status", (e) => {
        try {
          const data = JSON.parse(e.data);
          const step = data.current_step || data.status || "";
          const msg = data.message || "";
          const prog = data.progress || 0;
          setPipelineStep(step);
          setProgress(prog);
          if (msg) addStatusEvent(step, msg, prog);
        } catch {}
      });

      es.addEventListener("source", (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.source) {
            setSources((prev) => [...prev, data.source]);
          }
        } catch {}
      });

      es.addEventListener("complete", async () => {
        es.close();
        eventSourceRef.current = null;
        await fetchResult(rid, convId);
      });

      es.addEventListener("error", (e: Event) => {
        const msgEvent = e as MessageEvent;
        try {
          const data = JSON.parse(msgEvent.data);
          handleError(data.error || "Research failed", convId);
        } catch {
          handleError("Research failed", convId);
        }
        es.close();
        eventSourceRef.current = null;
      });

      es.addEventListener("cancelled", () => {
        es.close();
        eventSourceRef.current = null;
        handleCancel(convId);
      });

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        startPolling(rid, convId);
      };
    },
    [startPolling]
  );

  const fetchResult = useCallback(
    async (rid: string, convId: string) => {
      stopTimer();
      try {
        const res = await fetch(`/api/research/${rid}`);
        if (!res.ok) throw new Error("Failed to fetch result");
        const result = await res.json();

        const answer = result.final_answer || "Research complete. No answer was generated.";
        const srcs: Source[] = result.sources || [];
        const confidence = result.confidence_score || 0;

        updateConv(convId, (c) => ({
          ...c,
          status: "done",
          messages: [
            ...c.messages,
            { role: "assistant", content: answer, sources: srcs, confidence, timestamp: Date.now() },
          ],
          sources: srcs,
        }));

        setSources(srcs);
        setShowPipeline(false);
        setIsResearching(false);
        setPipelineStep("");

        if (result.total_time) {
          const secs = Math.round(result.total_time);
          showToast(`Completed in ${secs}s`);
        }
      } catch (err: any) {
        handleError(err.message, convId);
      }
    },
    [updateConv, stopTimer]
  );

  const handleError = useCallback(
    (msg: string, convId: string) => {
      stopTimer();
      setError(msg);
      setIsResearching(false);
      setShowPipeline(false);
      updateConv(convId, (c) => ({ ...c, status: "error" }));
      showToast(`Research failed: ${msg}`, "error");
    },
    [updateConv, stopTimer]
  );

  const handleCancel = useCallback(
    (convId: string) => {
      stopTimer();
      setError("Cancelled");
      setIsResearching(false);
      setShowPipeline(false);
      updateConv(convId, (c) => ({ ...c, status: "error" }));
      showToast("Research cancelled");
    },
    [updateConv, stopTimer]
  );

  const startResearch = useCallback(
    async (query: string, depth: Depth) => {
      if (isResearching || !query.trim()) return;

      const conv = createConversation(query.trim(), depth);
      setShowPipeline(true);
      setPipelineStep("initializing");
      setProgress(0);
      setError(null);
      statusLogRef.current = [];
      setStatusLog([]);
      addStatusEvent("initializing", "Starting research...", 0);
      startTimer();
      setIsResearching(true);

      // Add user message
      updateConv(conv.id, (c) => ({
        ...c,
        messages: [
          ...c.messages,
          { role: "user", content: query.trim(), timestamp: Date.now() },
        ],
      }));

      try {
        const res = await fetch("/api/research", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query.trim(), depth }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `API error: ${res.status}`);
        }
        const data = await res.json();
        setCurrentRid(data.research_id);

        // Try SSE first
        connectSSE(data.research_id, conv.id);
      } catch (err: any) {
        stopTimer();
        setError(err.message);
        setIsResearching(false);
        setShowPipeline(false);
        updateConv(conv.id, (c) => ({ ...c, status: "error" }));
        showToast(`Failed: ${err.message}`, "error");
      }
    },
    [isResearching, createConversation, updateConv, startTimer, stopTimer, connectSSE]
  );

  const cancelResearch = useCallback(async () => {
    if (!currentRid) return;
    try {
      await fetch(`/api/research/${currentRid}/cancel`, { method: "POST" });
    } catch {}
  }, [currentRid]);

  const newConversation = useCallback(() => {
    if (isResearching) {
      cancelResearch();
    }
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    stopTimer();
    setCurrentRid(null);
    setIsResearching(false);
    setShowPipeline(false);
    setPipelineStep("");
    setError(null);
    setActiveConvId(null);
    setSources([]);
  }, [isResearching, cancelResearch, stopTimer]);

  return {
    conversations,
    activeConv,
    isResearching,
    pipelineStep,
    progress,
    showPipeline,
    elapsed,
    sources,
    error,
    statusLog,
    startResearch,
    cancelResearch,
    newConversation,
    switchConversation,
    deleteConversation,
    clearAllConversations,
    setActiveConvId,
  };
}

// Toast state (global singleton)
let toastCallback: ((msg: string, type?: string) => void) | null = null;

export function setToastCallback(cb: typeof toastCallback) {
  toastCallback = cb;
}

export function showToast(message: string, type?: string) {
  if (toastCallback) toastCallback(message, type);
}
