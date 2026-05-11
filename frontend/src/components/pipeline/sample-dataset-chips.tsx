"use client";

import {
  HeartPulse,
  TrendingUp,
  ShoppingCart,
  Megaphone,
  Users,
  Factory,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SampleDatasetInfo } from "@/lib/api/types";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SampleDatasetChipsProps {
  datasets: SampleDatasetInfo[];
  onSelect: (name: string) => void;
  loading: boolean;
  loadingName?: string;
}

// ─── Domain config ────────────────────────────────────────────────────────────

const DOMAIN_CONFIG: Record<
  string,
  { icon: React.ElementType; badge: string }
> = {
  healthcare: {
    icon: HeartPulse,
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  },
  finance: {
    icon: TrendingUp,
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  ecommerce: {
    icon: ShoppingCart,
    badge: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  },
  marketing: {
    icon: Megaphone,
    badge: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  },
  hr: {
    icon: Users,
    badge: "bg-green-500/10 text-green-400 border-green-500/20",
  },
  manufacturing: {
    icon: Factory,
    badge: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  },
};

function getDomainConfig(domain: string) {
  return DOMAIN_CONFIG[domain.toLowerCase()] ?? {
    icon: Database,
    badge: "bg-white/10 text-white/60 border-white/10",
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

export function SampleDatasetChips({
  datasets,
  onSelect,
  loading,
  loadingName,
}: SampleDatasetChipsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {datasets.map((ds) => {
        const { icon: Icon, badge } = getDomainConfig(ds.domain);
        const isLoading = loading && loadingName === ds.name;
        const isDisabled = loading;

        return (
          <button
            key={ds.name}
            onClick={() => !isDisabled && onSelect(ds.name)}
            disabled={isDisabled}
            className={cn(
              "group relative text-left rounded-xl border border-white/8 bg-white/3",
              "p-4 flex flex-col gap-2.5 transition-all duration-200",
              !isDisabled &&
                "hover:bg-white/6 hover:border-white/15 hover:shadow-lg cursor-pointer",
              isDisabled && "opacity-60 cursor-not-allowed",
            )}
          >
            {/* Header row */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                {isLoading ? (
                  <div className="h-5 w-5 rounded-full border-2 border-accent-violet border-t-transparent animate-spin shrink-0" />
                ) : (
                  <Icon className="h-5 w-5 shrink-0 text-muted-foreground group-hover:text-foreground transition-colors" />
                )}
                <span className="text-sm font-semibold leading-tight">
                  {ds.display_name}
                </span>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wide",
                  badge,
                )}
              >
                {ds.domain}
              </span>
            </div>

            {/* Stats */}
            <p className="text-xs text-muted-foreground font-mono tabular-nums">
              {ds.n_rows.toLocaleString()} rows × {ds.n_cols} cols
            </p>

            {/* Description */}
            <p className="text-xs text-muted-foreground line-clamp-2">
              {ds.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}
