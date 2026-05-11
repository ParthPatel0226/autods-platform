"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ─── Variants ─────────────────────────────────────────────────────────────────

interface PageSkeletonProps {
  /** Number of card rows to render. Default: 3 */
  rows?: number;
  /** Additional class on the wrapper */
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function PageSkeleton({ rows = 3, className }: PageSkeletonProps) {
  return (
    <div className={cn("flex h-full flex-col overflow-hidden", className)}>
      {/* Header skeleton */}
      <div className="flex-shrink-0 border-b border-white/8 px-6 py-4 flex flex-col gap-2">
        <Skeleton className="h-7 w-48 rounded-lg bg-white/6" />
        <Skeleton className="h-4 w-72 rounded-md bg-white/4" />
      </div>

      {/* Body skeleton */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="flex flex-col gap-4 max-w-4xl mx-auto">
          {Array.from({ length: rows }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4"
            >
              {/* Card header row */}
              <div className="flex items-center gap-3">
                <Skeleton className="h-11 w-11 rounded-xl bg-white/6 flex-shrink-0" />
                <div className="flex flex-col gap-1.5 flex-1">
                  <Skeleton className="h-4 w-36 rounded-md bg-white/6" />
                  <Skeleton className="h-3 w-52 rounded-md bg-white/4" />
                </div>
              </div>
              {/* Card body lines */}
              <div className="flex flex-col gap-2 pl-14">
                <Skeleton className="h-3 w-full rounded-md bg-white/4" />
                <Skeleton className="h-3 w-4/5 rounded-md bg-white/4" />
              </div>
              {/* Card action */}
              <div className="pl-14">
                <Skeleton className="h-9 w-28 rounded-lg bg-white/6" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
