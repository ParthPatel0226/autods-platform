"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, HelpCircle } from "lucide-react";
import { edaApi } from "@/lib/api/endpoints";
import type { EDAQuestion, EDAResults } from "@/lib/api/types";
import { QuestionRenderer } from "@/components/pipeline/question-renderer";
import { ChartCard } from "@/components/pipeline/chart-card";
import { JobProgress } from "@/components/pipeline/job-progress";
import { PageSkeleton } from "@/components/shared/page-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type PageState = "questions" | "running" | "results";

// ─── Page ────────────────────────────────────────────────────────────────────

export default function EdaPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>("questions");
  const [questions, setQuestions] = useState<EDAQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [results, setResults] = useState<EDAResults | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);

  // ── Load questions on mount ────────────────────────────────────────────────

  useEffect(() => {
    async function fetchQuestions() {
      try {
        const data = await edaApi.generateQuestions(projectId);
        const qs = data.questions ?? [];
        setQuestions(qs);
        // Seed answers with recommended values where available
        const initial: Record<string, unknown> = {};
        for (const q of qs) {
          const rec = q.options?.find((o) => o.recommended);
          if (rec) initial[q.id] = rec.value;
        }
        setAnswers(initial);
      } catch (err) {
        toast.error("Failed to load EDA questions");
        console.error(err);
      } finally {
        setLoadingQuestions(false);
      }
    }
    fetchQuestions();
  }, [projectId]);

  // ── Submit answers + start job ─────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    try {
      await edaApi.answerQuestions({ project_id: projectId, answers });
      const runResult = await edaApi.run({ project_id: projectId });
      const jid = (runResult as { job_id?: string }).job_id ?? null;
      setJobId(jid);
      setPageState("running");
    } catch (err) {
      toast.error("Failed to start EDA analysis");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }, [projectId, answers]);

  // ── Load results after job completes ──────────────────────────────────────

  const handleJobComplete = useCallback(async () => {
    setLoadingResults(true);
    try {
      const data = await edaApi.results(projectId);
      setResults(data);
      setPageState("results");
    } catch (err) {
      toast.error("Failed to load EDA results");
      console.error(err);
    } finally {
      setLoadingResults(false);
    }
  }, [projectId]);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="container max-w-4xl mx-auto px-4 py-10 flex flex-col gap-8">
      {/* Back navigation */}
      <button
        onClick={() => router.push(`/${projectId}/configure`)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors self-start -mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Configure
      </button>

      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">
          Exploratory Data Analysis
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure and run domain-aware EDA on your dataset.
        </p>
      </div>

      {/* ── STATE 1: Questions ─────────────────────────────────────────────── */}

      {pageState === "questions" && (
        <>
          {loadingQuestions ? (
            <PageSkeleton rows={3} />
          ) : questions.length === 0 ? (
            <EmptyState
              icon={HelpCircle}
              title="No questions available"
              description="Proceed to run the EDA analysis with default settings."
            />
          ) : (
            <div className="flex flex-col gap-4">
              {questions.map((q) => (
                <QuestionRenderer
                  key={q.id}
                  question={q}
                  value={answers[q.id]}
                  onChange={(val) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: val }))
                  }
                />
              ))}
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              disabled={loadingQuestions || submitting}
              onClick={handleSubmit}
              className={cn(
                "btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold",
                (loadingQuestions || submitting) && "opacity-50 cursor-not-allowed",
              )}
            >
              {submitting && (
                <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              {submitting ? "Starting Analysis…" : "Run EDA Analysis"}
            </button>
          </div>
        </>
      )}

      {/* ── STATE 2: Job Running ───────────────────────────────────────────── */}

      {pageState === "running" && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-8 backdrop-blur-sm flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold text-foreground">
              Running Analysis
            </h2>
            <p className="text-sm text-muted-foreground">
              Your EDA pipeline is executing. This may take a moment.
            </p>
          </div>

          <JobProgress
            jobId={jobId}
            onComplete={handleJobComplete}
          />

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
          {/* AI Summary */}
          {results.summary && (
            <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-3">
              <h2 className="text-base font-semibold text-foreground">
                Analysis Summary
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                {results.summary}
              </p>
            </div>
          )}

          {/* Key Insights */}
          {results.insights && results.insights.length > 0 && (
            <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
              <h2 className="text-base font-semibold text-foreground">
                Key Insights
              </h2>
              <ul className="flex flex-col gap-2">
                {results.insights.map((insight, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-accent-violet/20 text-accent-violet flex items-center justify-center text-[10px] font-bold">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground leading-relaxed">
                      {insight}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Charts Grid */}
          {results.charts && Object.keys(results.charts).length > 0 && (
            <div className="flex flex-col gap-4">
              <h2 className="text-base font-semibold text-foreground">
                Visualizations
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {Object.entries(results.charts).map(([key, chart]) => {
                  const plotData = chart?.data ?? (Array.isArray(chart) ? chart : []);
                  const plotLayout = chart?.layout ?? {};
                  const title =
                    plotLayout?.title?.text ??
                    key.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
                  return (
                    <ChartCard
                      key={key}
                      title={title}
                      plotlyData={plotData}
                      plotlyLayout={plotLayout}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Statistical Tests */}
          {results.statistical_tests &&
            Object.keys(results.statistical_tests).length > 0 && (
              <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
                <h2 className="text-base font-semibold text-foreground">
                  Statistical Tests
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/8 text-left">
                        <th className="pb-2 pr-4 font-mono text-muted-foreground uppercase tracking-wider">
                          Test
                        </th>
                        <th className="pb-2 pr-4 font-mono text-muted-foreground uppercase tracking-wider">
                          Statistic
                        </th>
                        <th className="pb-2 pr-4 font-mono text-muted-foreground uppercase tracking-wider">
                          p-value
                        </th>
                        <th className="pb-2 font-mono text-muted-foreground uppercase tracking-wider">
                          Interpretation
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {Object.entries(results.statistical_tests).map(
                        ([testName, result]) => {
                          const r = result as Record<string, unknown>;
                          const statistic =
                            r?.statistic ?? r?.test_statistic ?? r?.f_statistic ?? "—";
                          const pValue = r?.p_value ?? r?.pvalue ?? "—";
                          const interpretation =
                            r?.interpretation ?? (
                              typeof pValue === "number" && pValue < 0.05
                                ? "Significant"
                                : "Not significant"
                            );
                          return (
                            <tr key={testName} className="hover:bg-white/3">
                              <td className="py-2 pr-4 font-mono text-foreground">
                                {testName.replace(/_/g, " ")}
                              </td>
                              <td className="py-2 pr-4 font-mono text-muted-foreground">
                                {typeof statistic === "number"
                                  ? statistic.toFixed(4)
                                  : String(statistic)}
                              </td>
                              <td className="py-2 pr-4 font-mono text-muted-foreground">
                                {typeof pValue === "number"
                                  ? pValue.toFixed(4)
                                  : String(pValue)}
                              </td>
                              <td className="py-2 text-muted-foreground">
                                {String(interpretation)}
                              </td>
                            </tr>
                          );
                        },
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          {/* Continue */}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/feature-engineering`)}
              className="btn-glow rounded-xl px-6 py-3 text-sm font-semibold"
            >
              Continue to Feature Engineering →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
