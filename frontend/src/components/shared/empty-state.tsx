"use client";

import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex h-full items-center justify-center px-6",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-5 text-center max-w-sm">
        {/* Icon */}
        <div className="rounded-2xl border border-white/8 bg-white/4 p-5 backdrop-blur-sm">
          <Icon
            className="h-10 w-10 text-accent-violet"
            strokeWidth={1.5}
          />
        </div>

        {/* Text */}
        <div className="flex flex-col gap-1.5">
          <p className="font-display italic text-xl font-semibold text-foreground">
            {title}
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
        </div>

        {/* Action */}
        {actionLabel && onAction && (
          <Button onClick={onAction} className="btn-glow">
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
