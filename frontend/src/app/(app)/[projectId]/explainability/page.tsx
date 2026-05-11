"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Brain,
  Sliders,
  ShieldCheck,
  FileText,
  ChevronLeft,
  ChevronRight,
  Download,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import dynamic from "next/dynamic";
import { explainApi } from "@/lib/api/endpoints";
import type {
  SHAPRequest,
  SHAPResponse,
  WhatIfRequest,
  WhatIfResponse,
  FairnessRequest,
  FairnessReport,
  ModelCardResponse,
} from "@/lib/api/types";
import { useJobProgress } from "@/lib/hooks/useJobProgress";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { COSMIC_PLOTLY_LAYOUT } from "@/lib/plotly-theme";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// ─── SHAP Tab ────────────────────────────────────────────────────────────────

function ShapJobTracker({
  jobId,
  onComplete,
}: {
  jobId: string;
  onComplete: (data: SHAPResponse) => void;
}) {
  const { status, progress, message, data, error } = useJobProgress(jobId);

  if (data && status === "completed") {
    onComplete(data as unknown as SHAPResponse);
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-white/2 p-8 backdrop-blur-sm">
      <div className="mx-auto max-w-md text-center">
        <div className="mb-4 flex justify-center">
          {error || status === "failed" ? (
            <XCircle className="h-10 w-10 text-red-400" />
          ) : status === "completed" ? (
            <CheckCircle2 className="h-10 w-10 text-green-400" />
          ) : (
            <Loader2 className="h-10 w-10 animate-spin text-violet-400" />
          )}
        </div>
        <p className="mb-2 font-medium text-white">
          {error ? "SHAP computation failed" : message || "Computing SHAP values…"}
        </p>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-white/40">{progress}%</p>
      </div>
    </div>
  );
}

function ShapResults({ result }: { result: SHAPResponse }) {
  const features = Object.keys(result.global_importance);
  const values = features.map((f) => result.global_importance[f]);

  // Sort descending
  const sorted = features
    .map((f, i) => ({ f, v: values[i] }))
    .sort((a, b) => b.v - a.v);

  const globalBar = {
    type: "bar" as const,
    orientation: "h" as const,
    x: sorted.map((d) => d.v),
    y: sorted.map((d) => d.f),
    marker: {
      color: sorted.map((_, i) =>
        i < 3 ? "rgba(168,85,247,0.85)" : "rgba(99,102,241,0.6)"
      ),
    },
  };

  // Waterfall: first local example if available
  const firstEx = result.local_examples[0] ?? {};
  const wfFeatures = Object.keys(firstEx).filter((k) => k !== "prediction");
  const wfValues = wfFeatures.map((k) => Number(firstEx[k]) || 0);

  const waterfall = {
    type: "waterfall" as const,
    x: wfFeatures,
    y: wfValues,
    connector: { line: { color: "rgba(255,255,255,0.15)" } },
    increasing: { marker: { color: "rgba(16,185,129,0.8)" } },
    decreasing: { marker: { color: "rgba(239,68,68,0.8)" } },
  };

  // Interactions heatmap
  const hasInteractions =
    result.interactions && Object.keys(result.interactions).length > 0;
  const intKeys = hasInteractions ? Object.keys(result.interactions!) : [];
  const heatmapZ = intKeys.map((k) => {
    const row = result.interactions![k] as Record<string, number>;
    return intKeys.map((k2) => row[k2] ?? 0);
  });

  const heatmap = hasInteractions
    ? {
        type: "heatmap" as const,
        z: heatmapZ,
        x: intKeys,
        y: intKeys,
        colorscale: "Portland" as const,
      }
    : null;

  const cosmicLayout = {
    ...COSMIC_PLOTLY_LAYOUT,
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "rgba(255,255,255,0.7)", family: "Inter Tight, sans-serif" },
  };

  return (
    <div className="space-y-6">
      {/* Global importance */}
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
          Global Feature Importance
        </h3>
        <Plot
          data={[globalBar]}
          layout={{
            ...cosmicLayout,
            height: 360,
            margin: { l: 160, r: 20, t: 10, b: 40 },
            xaxis: { title: { text: "Mean |SHAP|" }, gridcolor: "rgba(255,255,255,0.06)" },
            yaxis: { automargin: true },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </div>

      {/* Local waterfall */}
      {wfFeatures.length > 0 && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
            Local Explanation — First Example
          </h3>
          <Plot
            data={[waterfall]}
            layout={{
              ...cosmicLayout,
              height: 300,
              margin: { l: 20, r: 20, t: 10, b: 80 },
              xaxis: { tickangle: -40 },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {/* Interactions heatmap */}
      {heatmap && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
            Feature Interactions
          </h3>
          <Plot
            data={[heatmap]}
            layout={{
              ...cosmicLayout,
              height: 400,
              margin: { l: 140, r: 20, t: 10, b: 140 },
              xaxis: { tickangle: -45 },
              yaxis: { automargin: true },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}
    </div>
  );
}

function ShapTab({ projectId }: { projectId: string }) {
  const [sampleSize, setSampleSize] = useState(100);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<SHAPResponse | null>(null);

  const handleCompute = useCallback(async () => {
    setLoading(true);
    setJobId(null);
    setResult(null);
    try {
      const body: SHAPRequest = { project_id: projectId, sample_size: sampleSize };
      const res = await explainApi.shap(body) as unknown as { job_id?: string } & SHAPResponse;
      if (res.job_id) {
        setJobId(res.job_id);
      } else {
        setResult(res as SHAPResponse);
      }
    } catch (e: unknown) {
      toast.error((e as Error).message ?? "SHAP computation failed");
    } finally {
      setLoading(false);
    }
  }, [projectId, sampleSize]);

  return (
    <div className="space-y-6">
      {/* Config card */}
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
          SHAP Configuration
        </h3>
        <div className="flex flex-wrap items-end gap-6">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-white/50">Sample Size</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={10}
                max={5000}
                value={sampleSize}
                onChange={(e) => setSampleSize(Number(e.target.value))}
                className="w-28 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/60 focus:outline-none"
              />
              <span className="text-xs text-white/30">rows</span>
            </div>
            {sampleSize > 50 && (
              <p className="text-xs text-amber-400/80">
                &gt;50 rows → async job tracking
              </p>
            )}
          </div>
          <button
            onClick={handleCompute}
            disabled={loading || !!jobId}
            className="btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Compute SHAP
          </button>
        </div>
      </div>

      {/* Async tracker */}
      {jobId && !result && (
        <ShapJobTracker jobId={jobId} onComplete={(d) => { setResult(d); setJobId(null); }} />
      )}

      {/* Results */}
      {result && <ShapResults result={result} />}
    </div>
  );
}

// ─── What-If Tab ─────────────────────────────────────────────────────────────

function WhatIfTab({ projectId }: { projectId: string }) {
  const [baseRow, setBaseRow] = useState<Record<string, string>>({});
  const [modifications, setModifications] = useState<Record<string, string>>({});
  const [newFeatureKey, setNewFeatureKey] = useState("");
  const [newFeatureVal, setNewFeatureVal] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhatIfResponse | null>(null);

  const addFeature = () => {
    if (!newFeatureKey.trim()) return;
    setBaseRow((prev) => ({ ...prev, [newFeatureKey]: newFeatureVal }));
    setModifications((prev) => ({ ...prev, [newFeatureKey]: newFeatureVal }));
    setNewFeatureKey("");
    setNewFeatureVal("");
  };

  const handlePredict = useCallback(async () => {
    if (Object.keys(baseRow).length === 0) {
      toast.error("Add at least one feature first");
      return;
    }
    setLoading(true);
    try {
      const body: WhatIfRequest = {
        project_id: projectId,
        base_row: Object.fromEntries(
          Object.entries(baseRow).map(([k, v]) => [k, isNaN(Number(v)) ? v : Number(v)])
        ),
        modifications: Object.fromEntries(
          Object.entries(modifications).map(([k, v]) => [k, isNaN(Number(v)) ? v : Number(v)])
        ),
      };
      const res = await explainApi.whatif(body);
      setResult(res as WhatIfResponse);
    } catch (e: unknown) {
      toast.error((e as Error).message ?? "What-If prediction failed");
    } finally {
      setLoading(false);
    }
  }, [projectId, baseRow, modifications]);

  const features = Object.keys(baseRow);

  const cosmicLayout = {
    ...COSMIC_PLOTLY_LAYOUT,
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "rgba(255,255,255,0.7)", family: "Inter Tight, sans-serif" },
  };

  return (
    <div className="space-y-6">
      {/* Feature inputs */}
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
          Feature Values
        </h3>

        {/* Add new feature row */}
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Feature name"
            value={newFeatureKey}
            onChange={(e) => setNewFeatureKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addFeature()}
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-violet-500/60 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Value"
            value={newFeatureVal}
            onChange={(e) => setNewFeatureVal(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addFeature()}
            className="w-28 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-violet-500/60 focus:outline-none"
          />
          <button
            onClick={addFeature}
            className="rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-sm text-violet-300 hover:bg-violet-500/20"
          >
            + Add
          </button>
        </div>

        {/* Feature grid */}
        {features.length > 0 && (
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {features.map((f) => (
              <div key={f} className="flex flex-col gap-1">
                <label className="truncate text-xs text-white/50">{f}</label>
                <input
                  type="text"
                  value={modifications[f] ?? ""}
                  onChange={(e) =>
                    setModifications((prev) => ({ ...prev, [f]: e.target.value }))
                  }
                  className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/60 focus:outline-none"
                />
              </div>
            ))}
          </div>
        )}

        <button
          onClick={handlePredict}
          disabled={loading || features.length === 0}
          className="btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Predict
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Prediction comparison */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Original", val: result.original_prediction },
              { label: "Modified", val: result.new_prediction },
              {
                label: "Delta",
                val:
                  result.delta != null
                    ? (result.delta > 0 ? "+" : "") + result.delta.toFixed(4)
                    : "—",
                highlight: true,
              },
            ].map(({ label, val, highlight }) => (
              <div
                key={label}
                className={cn(
                  "rounded-2xl border p-5 text-center backdrop-blur-sm",
                  highlight
                    ? "border-violet-500/30 bg-violet-500/8"
                    : "border-white/8 bg-white/2"
                )}
              >
                <p className="mb-1 text-xs text-white/40">{label}</p>
                <p className="text-2xl font-bold text-white">{String(val)}</p>
              </div>
            ))}
          </div>

          {/* Per-feature contributions */}
          {Object.keys(result.feature_contributions).length > 0 && (
            <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
                Feature Contributions
              </h3>
              <Plot
                data={[
                  {
                    type: "bar",
                    x: Object.keys(result.feature_contributions),
                    y: Object.values(result.feature_contributions),
                    marker: {
                      color: Object.values(result.feature_contributions).map((v) =>
                        v >= 0 ? "rgba(16,185,129,0.8)" : "rgba(239,68,68,0.8)"
                      ),
                    },
                  },
                ]}
                layout={{
                  ...cosmicLayout,
                  height: 300,
                  margin: { l: 20, r: 20, t: 10, b: 100 },
                  xaxis: { tickangle: -40, gridcolor: "rgba(255,255,255,0.06)" },
                  yaxis: { gridcolor: "rgba(255,255,255,0.06)" },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Fairness Tab ─────────────────────────────────────────────────────────────

const COMMON_ATTRIBUTES = [
  "gender",
  "race",
  "age_group",
  "ethnicity",
  "income_bracket",
  "education_level",
];

function FairnessJobTracker({
  jobId,
  onComplete,
}: {
  jobId: string;
  onComplete: (data: FairnessReport) => void;
}) {
  const { status, progress, message, data, error } = useJobProgress(jobId);

  if (data && status === "completed") {
    onComplete(data as unknown as FairnessReport);
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-white/2 p-8 backdrop-blur-sm">
      <div className="mx-auto max-w-md text-center">
        <div className="mb-4 flex justify-center">
          {error || status === "failed" ? (
            <XCircle className="h-10 w-10 text-red-400" />
          ) : status === "completed" ? (
            <CheckCircle2 className="h-10 w-10 text-green-400" />
          ) : (
            <Loader2 className="h-10 w-10 animate-spin text-violet-400" />
          )}
        </div>
        <p className="mb-2 font-medium text-white">
          {error ? "Fairness audit failed" : message || "Running fairness audit…"}
        </p>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-pink-500 to-violet-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-white/40">{progress}%</p>
      </div>
    </div>
  );
}

function FairnessResults({ report }: { report: FairnessReport }) {
  const disparityKeys = Object.keys(report.disparities);
  const disparityValues = disparityKeys.map((k) => {
    const v = report.disparities[k];
    return typeof v === "number" ? v : 0;
  });

  const cosmicLayout = {
    ...COSMIC_PLOTLY_LAYOUT,
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "rgba(255,255,255,0.7)", family: "Inter Tight, sans-serif" },
  };

  return (
    <div className="space-y-6">
      {/* Metrics table */}
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
          Fairness Metrics
        </h3>
        <Table>
          <TableHeader>
            <TableRow className="border-white/8">
              <TableHead className="text-white/50">Metric</TableHead>
              <TableHead className="text-right text-white/50">Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(report.metrics).map(([k, v]) => (
              <TableRow key={k} className="border-white/8">
                <TableCell className="text-white/80">{k}</TableCell>
                <TableCell className="text-right font-mono text-white">
                  {typeof v === "number" ? v.toFixed(4) : String(v)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Disparity chart */}
      {disparityKeys.length > 0 && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
            Disparities
          </h3>
          <Plot
            data={[
              {
                type: "bar",
                x: disparityKeys,
                y: disparityValues,
                marker: {
                  color: disparityValues.map((v) =>
                    Math.abs(v) > 0.1
                      ? "rgba(239,68,68,0.8)"
                      : "rgba(16,185,129,0.8)"
                  ),
                },
              },
            ]}
            layout={{
              ...cosmicLayout,
              height: 280,
              margin: { l: 20, r: 20, t: 10, b: 80 },
              xaxis: { tickangle: -30, gridcolor: "rgba(255,255,255,0.06)" },
              yaxis: {
                title: { text: "Disparity" },
                gridcolor: "rgba(255,255,255,0.06)",
                zeroline: true,
                zerolinecolor: "rgba(255,255,255,0.2)",
              },
              shapes: [
                {
                  type: "line",
                  x0: -0.5,
                  x1: disparityKeys.length - 0.5,
                  y0: 0.1,
                  y1: 0.1,
                  line: { dash: "dot", color: "rgba(245,158,11,0.6)", width: 1 },
                },
                {
                  type: "line",
                  x0: -0.5,
                  x1: disparityKeys.length - 0.5,
                  y0: -0.1,
                  y1: -0.1,
                  line: { dash: "dot", color: "rgba(245,158,11,0.6)", width: 1 },
                },
              ],
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
            Recommendations
          </h3>
          <ul className="space-y-2">
            {report.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-3 text-sm text-white/70">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/20 text-xs font-bold text-violet-400">
                  {i + 1}
                </span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function FairnessTab({ projectId }: { projectId: string }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [customAttr, setCustomAttr] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [report, setReport] = useState<FairnessReport | null>(null);

  const toggleAttr = (attr: string) => {
    setSelected((prev) =>
      prev.includes(attr) ? prev.filter((a) => a !== attr) : [...prev, attr]
    );
  };

  const addCustom = () => {
    if (!customAttr.trim() || selected.includes(customAttr)) return;
    setSelected((prev) => [...prev, customAttr.trim()]);
    setCustomAttr("");
  };

  const handleAudit = useCallback(async () => {
    if (selected.length === 0) {
      toast.error("Select at least one protected attribute");
      return;
    }
    setLoading(true);
    setJobId(null);
    setReport(null);
    try {
      const body: FairnessRequest = {
        project_id: projectId,
        protected_attributes: selected,
      };
      const res = await explainApi.fairness(body) as unknown as { job_id?: string } & FairnessReport;
      if (res.job_id) {
        setJobId(res.job_id);
      } else {
        setReport(res as FairnessReport);
      }
    } catch (e: unknown) {
      toast.error((e as Error).message ?? "Fairness audit failed");
    } finally {
      setLoading(false);
    }
  }, [projectId, selected]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/50">
          Protected Attributes
        </h3>

        {/* Quick select chips */}
        <div className="mb-4 flex flex-wrap gap-2">
          {COMMON_ATTRIBUTES.map((attr) => (
            <button
              key={attr}
              onClick={() => toggleAttr(attr)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors",
                selected.includes(attr)
                  ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
                  : "border-white/15 bg-white/5 text-white/60 hover:border-white/30"
              )}
            >
              {attr}
            </button>
          ))}
        </div>

        {/* Custom attr */}
        <div className="mb-5 flex gap-2">
          <input
            type="text"
            placeholder="Custom attribute…"
            value={customAttr}
            onChange={(e) => setCustomAttr(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCustom()}
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 focus:border-violet-500/60 focus:outline-none"
          />
          <button
            onClick={addCustom}
            className="rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-sm text-violet-300 hover:bg-violet-500/20"
          >
            + Add
          </button>
        </div>

        {selected.length > 0 && (
          <p className="mb-4 text-xs text-white/40">
            Selected: {selected.join(", ")}
          </p>
        )}

        <button
          onClick={handleAudit}
          disabled={loading || !!jobId}
          className="btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ShieldCheck className="h-4 w-4" />
          )}
          Run Audit
        </button>
      </div>

      {jobId && !report && (
        <FairnessJobTracker jobId={jobId} onComplete={(d) => { setReport(d); setJobId(null); }} />
      )}

      {report && <FairnessResults report={report} />}
    </div>
  );
}

// ─── Model Card Tab ───────────────────────────────────────────────────────────

const MODEL_CARD_SECTIONS: { key: string; label: string }[] = [
  { key: "model_details", label: "Model Details" },
  { key: "intended_use", label: "Intended Use" },
  { key: "training_data", label: "Training Data" },
  { key: "metrics", label: "Evaluation Metrics" },
  { key: "ethical_considerations", label: "Ethical Considerations" },
  { key: "limitations", label: "Limitations & Risks" },
];

function renderCardValue(value: unknown, depth = 0): React.ReactNode {
  if (value === null || value === undefined) return <span className="text-white/30">—</span>;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <span className="text-white/80">{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <ul className="space-y-1">
        {value.map((item, i) => (
          <li key={i} className="flex gap-2 text-white/70">
            <span className="text-violet-400">•</span>
            {renderCardValue(item, depth + 1)}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <dl className={cn("space-y-1", depth > 0 && "ml-3")}>
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="flex flex-wrap gap-x-2">
            <dt className="text-xs font-medium text-white/40">{k}:</dt>
            <dd className="text-sm">{renderCardValue(v, depth + 1)}</dd>
          </div>
        ))}
      </dl>
    );
  }
  return null;
}

function ModelCardTab({ projectId }: { projectId: string }) {
  const [loading, setLoading] = useState(false);
  const [card, setCard] = useState<ModelCardResponse | null>(null);

  const fetchCard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await explainApi.modelCard(projectId);
      setCard(res as ModelCardResponse);
    } catch (e: unknown) {
      toast.error((e as Error).message ?? "Failed to load model card");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const downloadCard = () => {
    if (!card) return;
    const blob = new Blob([JSON.stringify(card.model_card, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `model-card-${projectId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!card && !loading) {
    return (
      <div className="rounded-2xl border border-white/8 bg-white/2 p-12 backdrop-blur-sm text-center">
        <FileText className="mx-auto mb-4 h-10 w-10 text-white/20" />
        <p className="mb-6 text-white/50">Generate a structured model card documenting your model.</p>
        <button
          onClick={fetchCard}
          className="btn-glow inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white"
        >
          <FileText className="h-4 w-4" />
          Generate Model Card
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-white/8 bg-white/2 p-12 backdrop-blur-sm text-center">
        <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-violet-400" />
        <p className="text-white/50">Generating model card…</p>
      </div>
    );
  }

  const mc = card!.model_card;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={downloadCard}
          className="flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 hover:border-white/30 hover:text-white"
        >
          <Download className="h-4 w-4" />
          Download JSON
        </button>
      </div>

      {MODEL_CARD_SECTIONS.map(({ key, label }) => {
        const val = mc[key];
        if (val === undefined) return null;
        return (
          <div
            key={key}
            className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm"
          >
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/50">
              {label}
            </h3>
            <div className="text-sm">{renderCardValue(val)}</div>
          </div>
        );
      })}

      {/* Render any extra top-level keys not in our known list */}
      {Object.keys(mc)
        .filter((k) => !MODEL_CARD_SECTIONS.some((s) => s.key === k))
        .map((key) => (
          <div
            key={key}
            className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm"
          >
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/50">
              {key.replace(/_/g, " ")}
            </h3>
            <div className="text-sm">{renderCardValue(mc[key])}</div>
          </div>
        ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ExplainabilityPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-8">
      {/* Header */}
      <div>
        <h1 className="mb-1 text-2xl font-bold tracking-tight text-white">
          Model Explainability
        </h1>
        <p className="text-sm text-white/50">
          Understand, audit, and document your trained model.
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="shap" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 rounded-xl border border-white/8 bg-white/4 p-1">
          {[
            { value: "shap", icon: Brain, label: "SHAP Analysis" },
            { value: "whatif", icon: Sliders, label: "What-If" },
            { value: "fairness", icon: ShieldCheck, label: "Fairness Audit" },
            { value: "modelcard", icon: FileText, label: "Model Card" },
          ].map(({ value, icon: Icon, label }) => (
            <TabsTrigger
              key={value}
              value={value}
              className="flex items-center gap-2 rounded-lg data-[state=active]:bg-violet-500/20 data-[state=active]:text-violet-300"
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="shap">
          <ShapTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="whatif">
          <WhatIfTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="fairness">
          <FairnessTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="modelcard">
          <ModelCardTab projectId={projectId} />
        </TabsContent>
      </Tabs>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={() => router.push(`/${projectId}/modeling`)}
          className="flex items-center gap-2 rounded-xl border border-white/15 px-5 py-3 text-sm text-white/70 transition-colors hover:border-white/30 hover:text-white"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Modeling
        </button>
        <button
          onClick={() => router.push(`/${projectId}/predict`)}
          className="btn-glow flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium text-white"
        >
          Continue to Predict
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
