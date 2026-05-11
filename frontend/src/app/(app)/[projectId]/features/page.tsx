"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { ChevronDown, Layers, Trash2, Zap } from "lucide-react";
import { feApi } from "@/lib/api/endpoints";
import type { FESuggestion, FEResults } from "@/lib/api/types";
import type { ApprovalDecision } from "@/components/pipeline/approval-widget";
import { ApprovalWidget } from "@/components/pipeline/approval-widget";
import { JobProgress } from "@/components/pipeline/job-progress";
import { PageSkeleton } from "@/components/shared/page-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type PageState = "suggest" | "running" | "results";

// ─── Sub-components ───────────────────────────────────────────────────────────

function ResultCard({
  icon,
  label,
  count,
  items,
  expanded,
  onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  items: string[];
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/2 p-5 backdrop-blur-sm flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium text-foreground">{label}</span>
      </div>
      <p className="text-3xl font-bold font-mono text-foreground">{count}</p>
      {items.length > 0 && (
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors w-fit"
        >
          <ChevronDown
            className={cn(
              "h-3 w-3 transition-transform duration-200",
              expanded && "rotate-180",
            )}
          />
          {expanded ? "Hide" : "Show"} list
        </button>
      )}
      {expanded && items.length > 0 && (
        <ul className="flex flex-col gap-1 max-h-48 overflow-y-auto">
          {items.map((item) => (
            <li
              key={item}
              className="text-xs font-mono text-muted-foreground truncate py-0.5"
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FeaturesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>("suggest");
  const [suggestions, setSuggestions] = useState<FESuggestion[]>([]);
  const [loadingSuggest, setLoadingSuggest] = useState(true);
  const [applying, setApplying] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [results, setResults] = useState<FEResults | null>(null);
  const [loadingResults, setLoadingResults] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>(
    {},
  );

  // ── Load suggestions on mount ──────────────────────────────────────────────

  useEffect(() => {
    async function fetchSuggestions() {
      try {
        const data = await feApi.suggest({ project_id: projectId });
        setSuggestions(data.suggestions ?? []);
      } catch (err) {
        toast.error("Failed to load feature engineering suggestions");
        console.error(err);
      } finally {
        setLoadingSuggest(false);
      }
    }
    fetchSuggestions();
  }, [projectId]);

  // ── Derived data ───────────────────────────────────────────────────────────

  // Map each suggestion column → one ApprovalDecision row
  const decisions: ApprovalDecision[] = suggestions.map((s) => ({
    label: s.column,
    value: Object.entries(s.decisions as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", "),
    alternatives: [],
  }));

  const reasoning = suggestions
    .map((s) => `• ${s.column}: ${s.recommendation_reason}`)
    .join("\n");

  // ── Build decision map for API ─────────────────────────────────────────────

  const buildDecisionMap = useCallback(
    () =>
      Object.fromEntries(
        suggestions.map((s) => [s.column, s.decisions as Record<string, unknown>]),
      ),
    [suggestions],
  );

  // ── Apply decisions → start job ────────────────────────────────────────────

  const startJob = useCallback(async () => {
    setApplying(true);
    try {
      const result = await feApi.apply({
        project_id: projectId,
        decisions: buildDecisionMap(),
      });
      const jid = (result as { job_id?: string }).job_id ?? null;
      setJobId(jid);
      setPageState("running");
    } catch (err) {
      toast.error("Failed to start feature engineering");
      console.error(err);
    } finally {
      setApplying(false);
    }
  }, [projectId, buildDecisionMap]);

  const handleApprove = useCallback(() => startJob(), [startJob]);

  // Modified values are display strings; apply original decisions (no alternatives)
  const handleModify = useCallback(
    (_modified: Record<string, string>) => startJob(),
    [startJob],
  );

  // ── Load results after job completes ──────────────────────────────────────

  const handleJobComplete = useCallback(async () => {
    setLoadingResults(true);
    try {
      const data = await feApi.results(projectId);
      setResults(data);
      setPageState("results");
    } catch (err) {
      toast.error("Failed to load feature engineering results");
      console.error(err);
    } finally {
      setLoadingResults(false);
    }
  }, [projectId]);

  const toggleCard = (key: string) =>
    setExpandedCards((prev) => ({ ...prev, [key]: !prev[key] }));

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="container max-w-4xl mx-auto px-4 py-10 flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">
          Feature Engineering
        </h1>
        <p className="text-sm text-muted-foreground">
          Review and approve AI-suggested transformations for your dataset.
        </p>
      </div>

      {/* ── STATE 1: Approval widget ──────────────────────────────────────── */}

      {pageState === "suggest" && (
        <>
          {loadingSuggest ? (
            <PageSkeleton rows={3} />
          ) : suggestions.length === 0 ? (
            <EmptyState
              icon={Layers}
              title="No suggestions available"
              description="No feature engineering transformations were recommended. Proceed to modeling."
            />
          ) : (
            <ApprovalWidget
              title="Approve: Feature Engineering"
              decisions={decisions}
              reasoning={reasoning}
              onApprove={handleApprove}
              onModify={handleModify}
              loading={applying}
            />
          )}

          {/* Back nav */}
          {!loadingSuggest && (
            <div className="flex items-center pt-2">
              <button
                type="button"
                onClick={() => router.push(`/${projectId}/eda`)}
                className="rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-foreground hover:bg-white/5 transition-colors"
              >
                ← Back to EDA
              </button>
            </div>
          )}
        </>
      )}

      {/* ── STATE 2: Job running ──────────────────────────────────────────── */}

      {pageState === "running" && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-8 backdrop-blur-sm flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold text-foreground">
              Applying Transformations
            </h2>
            <p className="text-sm text-muted-foreground">
              Feature engineering pipeline is executing. This may take a moment.
            </p>
          </div>

          <JobProgress jobId={jobId} onComplete={handleJobComplete} />

          {loadingResults && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="h-4 w-4 rounded-full border-2 border-white/40 border-t-transparent animate-spin" />
              Loading results…
            </div>
          )}
        </div>
      )}

      {/* ── STATE 3: Results ──────────────────────────────────────────────── */}

      {pageState === "results" && results && (
        <>
          {/* Three result cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <ResultCard
              icon={<Layers className="h-5 w-5 text-accent-violet" />}
              label="Features Created"
              count={results.final_features.length}
              items={results.final_features}
              expanded={expandedCards["features"] ?? false}
              onToggle={() => toggleCard("features")}
            />
            <ResultCard
              icon={<Trash2 className="h-5 w-5 text-red-400" />}
              label="Features Dropped"
              count={results.dropped.length}
              items={results.dropped}
              expanded={expandedCards["dropped"] ?? false}
              onToggle={() => toggleCard("dropped")}
            />
            <ResultCard
              icon={<Zap className="h-5 w-5 text-amber-400" />}
              label="Transformations Applied"
              count={Object.keys(results.transformations).length}
              items={Object.keys(results.transformations)}
              expanded={expandedCards["transforms"] ?? false}
              onToggle={() => toggleCard("transforms")}
            />
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/eda`)}
              className="rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-foreground hover:bg-white/5 transition-colors"
            >
              ← Back to EDA
            </button>
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/modeling`)}
              className="btn-glow rounded-xl px-6 py-3 text-sm font-semibold"
            >
              Proceed to Modeling →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
