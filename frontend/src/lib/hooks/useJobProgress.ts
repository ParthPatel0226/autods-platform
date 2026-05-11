"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { jobsApi } from "@/lib/api/endpoints";
import type { JobStatus } from "@/lib/api/types";

const TERMINAL_STATUSES = ["success", "failed", "cancelled"] as const;
type TerminalStatus = (typeof TERMINAL_STATUSES)[number];

function isTerminal(s: string): s is TerminalStatus {
  return (TERMINAL_STATUSES as readonly string[]).includes(s);
}

function buildStreamUrl(jobId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("autods_token")
      : null;
  const qs = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${base}/jobs/${jobId}/stream${qs}`;
}

export function useJobProgress(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const retriesRef = useRef(0);
  const MAX_RETRIES = 5;
  const BASE_DELAY_MS = 1000;

  useEffect(() => {
    if (!jobId) {
      setStatus(null);
      return;
    }

    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      es = new EventSource(buildStreamUrl(jobId));

      es.onopen = () => {
        retriesRef.current = 0;
        setError(null);
      };

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as JobStatus;
          setStatus(data);
          if (isTerminal(data.status)) {
            es?.close();
          }
        } catch (e) {
          console.error("SSE parse error:", e);
        }
      };

      es.onerror = () => {
        es?.close();
        if (cancelled) return;

        if (retriesRef.current < MAX_RETRIES) {
          const delay = BASE_DELAY_MS * Math.pow(2, retriesRef.current);
          retriesRef.current++;

          // Poll REST before reconnecting — skip reconnect if job is already done
          jobsApi
            .status(jobId)
            .then((s) => {
              if (isTerminal(s.status)) {
                setStatus(s);
              } else if (!cancelled) {
                retryTimeout = setTimeout(connect, delay);
              }
            })
            .catch(() => {
              if (!cancelled) {
                retryTimeout = setTimeout(connect, delay);
              }
            });
        } else {
          setError("Lost connection to job progress. Please refresh.");
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      es?.close();
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [jobId]);

  const cancel = useCallback(async () => {
    if (jobId) {
      await jobsApi.cancel(jobId);
      setStatus((prev) =>
        prev ? { ...prev, status: "cancelled" } : null,
      );
    }
  }, [jobId]);

  return {
    status: status?.status ?? null,
    progress: status?.progress ?? 0,
    message: status?.current_step ?? "",
    data: status,
    error,
    cancel,
    isRunning: status?.status === "running",
    isComplete: status?.status === "success",
    isFailed: status?.status === "failed",
    isCancelled: status?.status === "cancelled",
  };
}
