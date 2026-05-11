"use client";

import { useQuery } from "@tanstack/react-query";
import { User, Coins, Plug } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/hooks/useAuth";
import { metaApi } from "@/lib/api/endpoints";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { CostSummary } from "@/lib/api/types";

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-accent-violet/10 p-2.5">
          <Icon className="h-5 w-5 text-accent-violet" strokeWidth={1.5} />
        </div>
        <h2 className="font-display italic text-lg font-semibold text-foreground">
          {title}
        </h2>
      </div>
      <Separator className="opacity-30" />
      {children}
    </section>
  );
}

// ─── Row ──────────────────────────────────────────────────────────────────────

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm text-foreground font-mono">{value}</span>
    </div>
  );
}

// ─── Usage section ────────────────────────────────────────────────────────────

function UsageSection() {
  const { currentProjectId } = useAppStore();

  const { data, isLoading } = useQuery<CostSummary>({
    queryKey: ["meta", "costs", currentProjectId],
    queryFn: () => metaApi.costs(currentProjectId!),
    enabled: !!currentProjectId,
  });

  if (!currentProjectId) {
    return (
      <p className="text-sm text-muted-foreground">
        Select a project in the sidebar to see usage stats.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex justify-between">
            <Skeleton className="h-4 w-32 bg-white/6 rounded-md" />
            <Skeleton className="h-4 w-20 bg-white/4 rounded-md" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <p className="text-sm text-muted-foreground">No usage data yet.</p>
    );
  }

  const tokens = data.api_token_count ?? 0;
  const calls = data.api_call_count ?? 0;
  const estimatedCost = ((tokens * 0.003) / 1000).toFixed(4);

  return (
    <div className="flex flex-col gap-3">
      <Row label="API calls" value={calls.toLocaleString()} />
      <Row label="Total tokens" value={tokens.toLocaleString()} />
      <Row label="Estimated cost" value={`$${estimatedCost}`} />

      {data.completed_steps && data.completed_steps.length > 0 && (
        <>
          <Separator className="opacity-20 my-1" />
          <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
            Completed steps
          </p>
          <div className="flex flex-wrap gap-2">
            {data.completed_steps.map((step) => (
              <span
                key={step}
                className="rounded-full bg-white/6 border border-white/10 px-3 py-1 text-xs font-mono text-foreground"
              >
                {step}
              </span>
            ))}
          </div>
        </>
      )}

      {data.step_breakdown && data.step_breakdown.length > 0 && (
        <>
          <Separator className="opacity-20 my-1" />
          <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
            Token breakdown by step
          </p>
          <div className="flex flex-col gap-1.5">
            {data.step_breakdown.map((row, i) => {
              const step = Object.keys(row)[0];
              const val = step ? row[step] : null;
              if (!step || val == null) return null;
              return (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground font-mono capitalize">
                    {step.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs font-mono text-foreground tabular-nums">
                    {typeof val === "number" ? val.toLocaleString() : String(val)}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { user, isLoading: authLoading } = useAuth();

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-white/8 px-6 py-4">
        <h1 className="font-display italic text-2xl font-bold text-foreground">
          Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage your account and view project usage.
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="flex flex-col gap-5 max-w-2xl mx-auto">
          {/* ── Account ── */}
          <Section icon={User} title="Account">
            {authLoading ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-4 w-48 bg-white/6 rounded-md" />
                <Skeleton className="h-4 w-64 bg-white/4 rounded-md" />
              </div>
            ) : user ? (
              <div className="flex flex-col gap-3">
                <Row label="Name" value={user.full_name || "—"} />
                <Row label="Email" value={user.email} />
                <Row
                  label="Member since"
                  value={new Date(user.created_at).toLocaleDateString(
                    undefined,
                    { year: "numeric", month: "long" },
                  )}
                />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not signed in.</p>
            )}
          </Section>

          {/* ── Usage ── */}
          <Section icon={Coins} title="Usage">
            <UsageSection />
          </Section>

          {/* ── Connectors ── */}
          <Section icon={Plug} title="Connectors">
            <div
              className={cn(
                "rounded-xl border border-dashed border-white/10 px-5 py-8",
                "flex flex-col items-center gap-2 text-center",
              )}
            >
              <p className="text-sm font-medium text-muted-foreground">
                Coming soon
              </p>
              <p className="text-xs text-muted-foreground/60 max-w-xs">
                Manage external data source connections — databases, cloud
                storage, and APIs — directly from here.
              </p>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
