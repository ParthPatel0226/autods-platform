"use client";

import { Rows3, Columns3, HardDrive } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MetricCardsProps {
  rows: number;
  columns: number;
  memoryKb: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatMemory(kb: number): string {
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${kb} KB`;
}

// ─── Sub-component ────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  value,
  label,
  iconClass,
}: {
  icon: React.ElementType;
  value: string;
  label: string;
  iconClass?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-1 items-center gap-4 rounded-xl border border-white/8",
        "bg-white/3 px-5 py-4 backdrop-blur-sm",
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
          "bg-white/5",
          iconClass,
        )}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-3xl font-bold tabular-nums leading-none">
          {value}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MetricCards({ rows, columns, memoryKb }: MetricCardsProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row">
      <MetricCard
        icon={Rows3}
        value={rows.toLocaleString()}
        label="Rows"
        iconClass="text-accent-violet"
      />
      <MetricCard
        icon={Columns3}
        value={columns.toLocaleString()}
        label="Columns"
        iconClass="text-cyan-400"
      />
      <MetricCard
        icon={HardDrive}
        value={formatMemory(memoryKb)}
        label="Memory"
        iconClass="text-accent-green"
      />
    </div>
  );
}
