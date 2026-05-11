"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Trophy, Clock, BarChart3, CheckCircle2 } from "lucide-react";
import dynamic from "next/dynamic";
import { modelingApi } from "@/lib/api/endpoints";
import type { ModelingConfig, Leaderboard } from "@/lib/api/types";
import { useJobProgress } from "@/lib/hooks/useJobProgress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// ─── Constants ────────────────────────────────────────────────────────────────

const ALGORITHMS = [
  { id: "xgboost", label: "XGBoost" },
  { id: "lightgbm", label: "LightGBM" },
  { id: "random_forest", label: "Random Forest" },
  { id: "logistic_regression", label: "Logistic / Linear Regression" },
  { id: "svm", label: "SVM" },
  { id: "knn", label: "KNN" },
  { id: "catboost", label: "CatBoost" },
  { id: "extra_trees", label: "Extra Trees" },
];

const SEARCH_STRATEGIES = [
  { value: "random", label: "Random Search" },
  { value: "grid", label: "Grid Search" },
  { value: "bayesian", label: "Bayesian Optimization" },
];

const PRIMARY_METRICS = [
  { value: "accuracy", label: "Accuracy" },
  { value: "f1_weighted", label: "F1 (Weighted)" },
  { value: "roc_auc", label: "ROC AUC" },
  { value: "precision", label: "Precision" },
  { value: "recall", label: "Recall" },
  { value: "r2", label: "R² Score" },
  { value: "rmse", label: "RMSE" },
  { value: "mae", label: "MAE" },
];

// ─── Types ────────────────────────────────────────────────────────────────────

type PageState = "config" | "running" | "results";

// ─── Sub-components ───────────────────────────────────────────────────────────

function AlgoGrid({
  selected,
  onToggle,
}: {
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {ALGORITHMS.map((algo) => {
        const active = selected.includes(algo.id);
        return (
          <button
            key={algo.id}
            type="button"
            onClick={() => onToggle(algo.id)}
            className={cn(
              "rounded-xl border px-4 py-2.5 text-left text-sm font-medium transition-all",
              active
                ? "border-accent-violet/60 bg-accent-violet/10 text-foreground"
                : "border-white/10 bg-white/2 text-muted-foreground hover:border-white/20 hover:text-foreground",
            )}
          >
            {algo.label}
          </button>
        );
      })}
    </div>
  );
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-sm font-mono text-accent-violet">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#A855F7] h-1.5 rounded-full bg-white/10 cursor-pointer"
      />
    </div>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
      <div
        className="h-full rounded-full bg-accent-violet transition-all duration-500"
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  );
}

// ─── Training progress inner component (uses hook) ─────────────────────────

function TrainingProgress({
  jobId,
  onComplete,
}: {
  jobId: string | null;
  onComplete: () => void;
}) {
  const { status, progress, message, isComplete, isFailed, isCancelled } =
    useJobProgress(jobId);

  useEffect(() => {
    if (isComplete) onComplete();
  }, [isComplete, onComplete]);

  useEffect(() => {
    if (isFailed) toast.error("Training job failed");
  }, [isFailed]);

  return (
    <div className="flex flex-col gap-4">
      <ProgressBar value={progress} />
      <p className="text-sm text-muted-foreground">
        {isFailed
          ? "Training failed."
          : isCancelled
            ? "Training cancelled."
            : message || "Initializing…"}
      </p>
      {status && (
        <p className="text-xs font-mono text-muted-foreground/60">
          status: {status}
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ModelingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  const [pageState, setPageState] = useState<PageState>("config");

  // Config state
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>([
    "xgboost",
    "lightgbm",
    "random_forest",
  ]);
  const [cvFolds, setCvFolds] = useState(5);
  const [searchStrategy, setSearchStrategy] = useState("random");
  const [primaryMetric, setPrimaryMetric] = useState("accuracy");
  const [timeBudget, setTimeBudget] = useState(5); // minutes
  const [training, setTraining] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  // Results state
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
  const [loadingResults, setLoadingResults] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  // ── Toggle algorithm ────────────────────────────────────────────────────────

  const toggleAlgo = useCallback((id: string) => {
    setSelectedAlgos((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    );
  }, []);

  // ── Start training ──────────────────────────────────────────────────────────

  const handleTrain = useCallback(async () => {
    if (selectedAlgos.length === 0) {
      toast.error("Select at least one algorithm");
      return;
    }
    setTraining(true);
    try {
      const config: ModelingConfig = {
        algorithms: selectedAlgos,
        cv_folds: cvFolds,
        search_strategy: searchStrategy,
        primary_metric: primaryMetric,
        time_budget_seconds: timeBudget * 60,
      };
      const result = await modelingApi.train({ project_id: projectId, config });
      const jid = (result as { job_id?: string }).job_id ?? null;
      setJobId(jid);
      setPageState("running");
    } catch (err) {
      toast.error("Failed to start training");
      console.error(err);
    } finally {
      setTraining(false);
    }
  }, [projectId, selectedAlgos, cvFolds, searchStrategy, primaryMetric, timeBudget]);

  // ── Load results ────────────────────────────────────────────────────────────

  const handleJobComplete = useCallback(async () => {
    setLoadingResults(true);
    try {
      const data = await modelingApi.leaderboard(projectId);
      setLeaderboard(data);
      setSelectedModel(data.best_model ?? null);
      setPageState("results");
    } catch (err) {
      toast.error("Failed to load leaderboard");
      console.error(err);
    } finally {
      setLoadingResults(false);
    }
  }, [projectId]);

  // ── Select model ────────────────────────────────────────────────────────────

  const handleSelectModel = useCallback(
    async (modelName: string) => {
      setSelecting(modelName);
      try {
        await modelingApi.selectBest({ project_id: projectId, model_name: modelName });
        setSelectedModel(modelName);
        toast.success(`Selected ${modelName} as best model`);
      } catch (err) {
        toast.error("Failed to select model");
        console.error(err);
      } finally {
        setSelecting(null);
      }
    },
    [projectId],
  );

  // ─── Plotly data ─────────────────────────────────────────────────────────────

  const plotData = leaderboard
    ? [
        {
          type: "bar" as const,
          orientation: "h" as const,
          y: leaderboard.entries.map((e) => e.model_name),
          x: leaderboard.entries.map(
            (e) => e.metrics[primaryMetric] ?? Object.values(e.metrics)[0] ?? 0,
          ),
          marker: {
            color: leaderboard.entries.map((e) =>
              e.model_name === leaderboard.best_model
                ? "rgba(168, 85, 247, 0.8)"
                : "rgba(99, 102, 241, 0.5)",
            ),
          },
        },
      ]
    : [];

  const plotLayout = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "rgba(255,255,255,0.7)", size: 11 },
    margin: { t: 16, b: 40, l: 140, r: 24 },
    xaxis: {
      gridcolor: "rgba(255,255,255,0.06)",
      title: { text: primaryMetric },
    },
    yaxis: { gridcolor: "transparent" },
    height: 220,
  };

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="container max-w-4xl mx-auto px-4 py-10 flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Modeling</h1>
        <p className="text-sm text-muted-foreground">
          Select algorithms, configure training, and compare models.
        </p>
      </div>

      {/* ── STATE 1: Config ──────────────────────────────────────────────── */}

      {pageState === "config" && (
        <>
          <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-6">
            {/* Algorithms */}
            <div className="flex flex-col gap-3">
              <p className="text-sm font-medium text-foreground">Algorithms</p>
              <AlgoGrid selected={selectedAlgos} onToggle={toggleAlgo} />
            </div>

            {/* Sliders */}
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <SliderField
                label="CV Folds"
                value={cvFolds}
                min={2}
                max={10}
                step={1}
                format={(v) => `${v} folds`}
                onChange={setCvFolds}
              />
              <SliderField
                label="Time Budget"
                value={timeBudget}
                min={1}
                max={30}
                step={1}
                format={(v) => `${v} min`}
                onChange={setTimeBudget}
              />
            </div>

            {/* Selects */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label className="text-sm text-muted-foreground">Search Strategy</label>
                <Select
                  value={searchStrategy}
                  onValueChange={(v) => { if (v) setSearchStrategy(v); }}
                >
                  <SelectTrigger className="bg-white/5 border-white/15 hover:border-accent-violet/60 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEARCH_STRATEGIES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm text-muted-foreground">Primary Metric</label>
                <Select
                  value={primaryMetric}
                  onValueChange={(v) => { if (v) setPrimaryMetric(v); }}
                >
                  <SelectTrigger className="bg-white/5 border-white/15 hover:border-accent-violet/60 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIMARY_METRICS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/features`)}
              className="rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-foreground hover:bg-white/5 transition-colors"
            >
              ← Back to Features
            </button>
            <button
              type="button"
              disabled={training || selectedAlgos.length === 0}
              onClick={handleTrain}
              className={cn(
                "btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold",
                (training || selectedAlgos.length === 0) && "opacity-50 cursor-not-allowed",
              )}
            >
              {training && (
                <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              {training ? "Starting…" : "Train Models"}
            </button>
          </div>
        </>
      )}

      {/* ── STATE 2: Running ─────────────────────────────────────────────── */}

      {pageState === "running" && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-8 backdrop-blur-sm flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold text-foreground">Training Models</h2>
            <p className="text-sm text-muted-foreground">
              Running {selectedAlgos.length} algorithm
              {selectedAlgos.length !== 1 ? "s" : ""} with {cvFolds}-fold cross-validation.
            </p>
          </div>

          <TrainingProgress jobId={jobId} onComplete={handleJobComplete} />

          {/* Per-algo status chips */}
          <div className="flex flex-wrap gap-2">
            {selectedAlgos.map((id) => {
              const label = ALGORITHMS.find((a) => a.id === id)?.label ?? id;
              return (
                <span
                  key={id}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/3 px-3 py-1 text-xs text-muted-foreground"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-accent-violet/70 animate-pulse" />
                  {label}
                </span>
              );
            })}
          </div>

          {loadingResults && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="h-4 w-4 rounded-full border-2 border-white/40 border-t-transparent animate-spin" />
              Loading leaderboard…
            </div>
          )}
        </div>
      )}

      {/* ── STATE 3: Results ─────────────────────────────────────────────── */}

      {pageState === "results" && leaderboard && (
        <>
          {/* Leaderboard table */}
          <div className="rounded-2xl border border-white/8 bg-white/2 overflow-hidden backdrop-blur-sm">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-white/8">
              <Trophy className="h-4 w-4 text-amber-400" />
              <span className="text-sm font-semibold text-foreground">Leaderboard</span>
              {leaderboard.best_model && (
                <span className="ml-auto text-xs text-muted-foreground">
                  Best:{" "}
                  <span className="text-accent-violet font-mono">
                    {leaderboard.best_model}
                  </span>
                </span>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow className="border-white/8 bg-white/5">
                  <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground w-12">
                    Rank
                  </TableHead>
                  <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                    Model
                  </TableHead>
                  <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                    {primaryMetric}
                  </TableHead>
                  <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                    Train Time
                  </TableHead>
                  <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground w-24">
                    Action
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leaderboard.entries.map((entry) => {
                  const isBest = entry.model_name === leaderboard.best_model;
                  const isSelected = entry.model_name === selectedModel;
                  const metricVal =
                    entry.metrics[primaryMetric] ??
                    Object.values(entry.metrics)[0] ??
                    0;
                  return (
                    <TableRow
                      key={entry.model_name}
                      className={cn(
                        "border-white/5",
                        isBest
                          ? "bg-accent-violet/5 hover:bg-accent-violet/8"
                          : "hover:bg-white/3",
                      )}
                    >
                      <TableCell className="text-sm font-mono text-muted-foreground">
                        {entry.rank}
                      </TableCell>
                      <TableCell className="text-sm font-medium text-foreground">
                        <div className="flex items-center gap-2">
                          {isBest && (
                            <Trophy className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                          )}
                          {entry.model_name}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm font-mono text-accent-violet">
                        {typeof metricVal === "number"
                          ? metricVal.toFixed(4)
                          : metricVal}
                      </TableCell>
                      <TableCell className="text-sm font-mono text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {entry.train_time.toFixed(1)}s
                        </div>
                      </TableCell>
                      <TableCell>
                        {isSelected ? (
                          <span className="inline-flex items-center gap-1 text-xs text-green-400">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Selected
                          </span>
                        ) : (
                          <button
                            type="button"
                            disabled={selecting === entry.model_name}
                            onClick={() => handleSelectModel(entry.model_name)}
                            className="text-xs text-muted-foreground hover:text-accent-violet transition-colors disabled:opacity-50"
                          >
                            {selecting === entry.model_name ? "…" : "Select"}
                          </button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          {/* Plotly chart */}
          {leaderboard.entries.length > 0 && (
            <div className="rounded-2xl border border-white/8 bg-white/2 p-5 backdrop-blur-sm flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-accent-violet" />
                <span className="text-sm font-semibold text-foreground">
                  Model Comparison
                </span>
              </div>
              <Plot
                data={plotData}
                layout={plotLayout}
                config={{ displayModeBar: false, responsive: true }}
                className="w-full"
                style={{ width: "100%" }}
              />
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/features`)}
              className="rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-foreground hover:bg-white/5 transition-colors"
            >
              ← Back to Features
            </button>
            <button
              type="button"
              onClick={() => router.push(`/${projectId}/explainability`)}
              className="btn-glow rounded-xl px-6 py-3 text-sm font-semibold"
            >
              Continue to Explainability →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
