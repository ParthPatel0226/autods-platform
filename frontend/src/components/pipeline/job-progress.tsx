"use client";

import { useEffect } from "react";
import { Progress as ProgressPrimitive } from "@base-ui/react/progress";
import { cn } from "@/lib/utils";
import { useJobProgress } from "@/lib/hooks/useJobProgress";

// ─── Types ────────────────────────────────────────────────────────────────────

interface JobProgressProps {
  jobId: string | null;
  onComplete?: () => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function JobProgress({ jobId, onComplete, className }: JobProgressProps) {
  const { status, progress, message, error, cancel, isComplete, isFailed } =
    useJobProgress(jobId);

  // Fire onComplete once when job transitions to 'success'
  useEffect(() => {
    if (isComplete) onComplete?.();
  }, [isComplete, onComplete]);

  if (!jobId) return null;

  const pct = Math.round(Math.min(Math.max(progress, 0), 100));

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Progress bar */}
      <ProgressPrimitive.Root
        value={pct}
        className="flex flex-col gap-2"
        aria-label="Job progress"
      >
        {/* Label row */}
        <div className="flex items-center justify-between">
          <ProgressPrimitive.Label className="text-sm text-muted-foreground truncate max-w-[70%]">
            {message || "Processing…"}
          </ProgressPrimitive.Label>
          <ProgressPrimitive.Value className="text-sm font-mono text-accent-violet tabular-nums" />
        </div>

        {/* Track */}
        <ProgressPrimitive.Track
          className={cn(
            "relative h-2 w-full overflow-hidden rounded-full",
            "bg-white/10",
          )}
        >
          <ProgressPrimitive.Indicator
            className={cn(
              "h-full rounded-full transition-all duration-500 ease-out",
              isFailed
                ? "bg-red-500"
                : "bg-gradient-to-r from-accent-violet to-purple-400",
            )}
          />
        </ProgressPrimitive.Track>
      </ProgressPrimitive.Root>

      {/* Status / error row */}
      {isFailed && (
        <p className="text-xs text-red-400 font-mono">
          {error ?? "Job failed. Check logs for details."}
        </p>
      )}
      {error && !isFailed && (
        <p className="text-xs text-amber-400 font-mono">{error}</p>
      )}

      {/* Cancel button — only shown while job is in progress */}
      {status === "running" && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => void cancel()}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all duration-150",
              "border-red-500/40 text-red-400",
              "hover:border-red-500/70 hover:bg-red-500/10 hover:text-red-300",
            )}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
