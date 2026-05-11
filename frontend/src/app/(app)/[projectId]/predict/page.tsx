"use client";

import { useState, useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  ArrowRight,
  Plus,
  Trash2,
  Zap,
  FileUp,
  Download,
  BarChart3,
  Target,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { FileDropzone } from "@/components/pipeline/file-dropzone";
import { JobProgress } from "@/components/pipeline/job-progress";
import { predictApi, uploadApi, jobsApi } from "@/lib/api/endpoints";
import type { PredictResponse } from "@/lib/api/types";
import { mergeCosmicLayout } from "@/lib/plotly-theme";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ─── Lazy Plotly ──────────────────────────────────────────────────────────────

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// ─── Types ────────────────────────────────────────────────────────────────────

interface FeatureRow {
  id: number;
  key: string;
  value: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

let _id = 0;
function nextId() {
  return ++_id;
}

function parseFeatures(rows: FeatureRow[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const { key, value } of rows) {
    if (!key.trim()) continue;
    const trimmed = value.trim();
    // Try numeric, bool, then fallback to string
    if (trimmed === "true") out[key.trim()] = true;
    else if (trimmed === "false") out[key.trim()] = false;
    else if (trimmed !== "" && !isNaN(Number(trimmed)))
      out[key.trim()] = Number(trimmed);
    else out[key.trim()] = trimmed;
  }
  return out;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionCard({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-6">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex-shrink-0 rounded-lg bg-accent-violet/10 p-2 text-accent-violet">
          {icon}
        </div>
        <div>
          <h2 className="font-display italic text-xl font-semibold text-foreground">
            {title}
          </h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

// ─── Single Prediction Tab ────────────────────────────────────────────────────

function SinglePredictionSection({ projectId }: { projectId: string }) {
  const [rows, setRows] = useState<FeatureRow[]>([
    { id: nextId(), key: "", value: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);

  const addRow = () =>
    setRows((prev) => [...prev, { id: nextId(), key: "", value: "" }]);

  const removeRow = (id: number) =>
    setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.id !== id) : prev));

  const updateRow = (id: number, field: "key" | "value", val: string) =>
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: val } : r)),
    );

  const handlePredict = async () => {
    const features = parseFeatures(rows);
    if (Object.keys(features).length === 0) {
      toast.error("Add at least one feature before predicting.");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await predictApi.single({ project_id: projectId, features });
      setResult(res as unknown as PredictResponse);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prediction failed.");
    } finally {
      setLoading(false);
    }
  };

  // Build SHAP horizontal bar chart
  const shapData = result?.shap;
  const shapChart =
    shapData && Object.keys(shapData).length > 0
      ? (() => {
          const entries = Object.entries(shapData).sort(
            ([, a], [, b]) => Math.abs(b) - Math.abs(a),
          );
          const features = entries.map(([k]) => k);
          const values = entries.map(([, v]) => v);
          return { features, values };
        })()
      : null;

  return (
    <SectionCard
      icon={<Zap className="h-5 w-5" />}
      title="Single Prediction"
      subtitle="Enter feature values to get an instant prediction with local SHAP explanation."
    >
      {/* Feature grid */}
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs font-mono text-muted-foreground px-1">
          <span>Feature name</span>
          <span>Value</span>
        </div>
        {rows.map((row) => (
          <div key={row.id} className="grid grid-cols-2 gap-4 items-center">
            <Input
              placeholder="e.g. age"
              value={row.key}
              onChange={(e) => updateRow(row.id, "key", e.target.value)}
              className="bg-white/4 border-white/10 text-sm"
            />
            <div className="flex gap-2">
              <Input
                placeholder="e.g. 42"
                value={row.value}
                onChange={(e) => updateRow(row.id, "value", e.target.value)}
                className="bg-white/4 border-white/10 text-sm"
              />
              <button
                type="button"
                onClick={() => removeRow(row.id)}
                disabled={rows.length === 1}
                className={cn(
                  "flex-shrink-0 rounded-lg p-2 transition-colors",
                  rows.length === 1
                    ? "text-white/20 cursor-not-allowed"
                    : "text-white/40 hover:text-red-400 hover:bg-red-500/10",
                )}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={addRow}
          className="flex items-center gap-2 w-fit text-sm text-accent-violet hover:text-purple-400 transition-colors mt-1"
        >
          <Plus className="h-4 w-4" />
          Add feature
        </button>
      </div>

      <Button
        onClick={() => void handlePredict()}
        disabled={loading}
        className="btn-glow w-full"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
            Predicting…
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Predict
          </span>
        )}
      </Button>

      {/* Result card */}
      {result && (
        <div className="mt-2 rounded-xl border border-accent-violet/20 bg-accent-violet/5 p-6 flex flex-col gap-5">
          {/* Prediction value */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <span className="text-sm text-muted-foreground font-mono uppercase tracking-wider">
              Prediction
            </span>
            <span className="font-display italic text-4xl font-bold text-accent-violet">
              {String(result.prediction)}
            </span>
          </div>

          {/* Probability bar */}
          {result.probability != null && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Probability</span>
                <span className="font-mono text-foreground tabular-nums">
                  {(result.probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2.5 w-full rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-violet to-purple-400 transition-all duration-700"
                  style={{ width: `${(result.probability * 100).toFixed(1)}%` }}
                />
              </div>
            </div>
          )}

          {/* Confidence interval */}
          {result.confidence_interval && (
            <div className="flex items-center gap-3 text-sm">
              <span className="text-muted-foreground">95% CI</span>
              <span className="font-mono text-foreground">
                [{result.confidence_interval.lower.toFixed(4)},&nbsp;
                {result.confidence_interval.upper.toFixed(4)}]
              </span>
            </div>
          )}

          {/* Local SHAP chart */}
          {shapChart && (
            <div>
              <p className="mb-3 text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                <BarChart3 className="h-4 w-4 text-accent-violet" />
                Feature contributions
              </p>
              <Plot
                data={[
                  {
                    type: "bar",
                    orientation: "h",
                    x: shapChart.values,
                    y: shapChart.features,
                    marker: {
                      color: shapChart.values.map((v) =>
                        v >= 0 ? "#10b981" : "#ec4899",
                      ),
                      opacity: 0.85,
                    },
                  },
                ]}
                layout={mergeCosmicLayout({
                  height: Math.max(180, shapChart.features.length * 28 + 60),
                  xaxis: { title: { text: "SHAP value" }, zeroline: true },
                  yaxis: { automargin: true, tickfont: { size: 11 } },
                  margin: { t: 20, r: 16, b: 40, l: 10 },
                })}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
              />
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}

// ─── Batch Prediction Section ─────────────────────────────────────────────────

function BatchPredictionSection({ projectId }: { projectId: string }) {
  const [uploadLoading, setUploadLoading] = useState(false);
  const [fileId, setFileId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [nRows, setNRows] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobComplete, setJobComplete] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [batchRunning, setBatchRunning] = useState(false);

  const handleFileAccepted = useCallback(
    async (file: File) => {
      setUploadLoading(true);
      setFileId(null);
      setFileName(file.name);
      setJobId(null);
      setJobComplete(false);
      setDownloadUrl(null);
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await uploadApi.file(form);
        setFileId(res.source_id);
        setNRows(res.n_rows);
        toast.success(`Uploaded ${file.name} — ${res.n_rows} rows`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Upload failed.");
      } finally {
        setUploadLoading(false);
      }
    },
    [],
  );

  const handleRunBatch = async () => {
    if (!fileId) return;
    setBatchRunning(true);
    try {
      const res = await predictApi.batch({
        project_id: projectId,
        file_id: fileId,
      });
      setJobId(res.job_id);
      toast.info(`Batch job started — ${res.n_rows} rows queued.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start batch job.");
      setBatchRunning(false);
    }
  };

  const handleJobComplete = useCallback(async () => {
    setJobComplete(true);
    setBatchRunning(false);
    if (!jobId) return;
    try {
      const res = await jobsApi.result(jobId);
      const url =
        (res.result as Record<string, unknown>).download_url as string | undefined;
      if (url) setDownloadUrl(url);
    } catch {
      // result may not have a download url — that's fine
    }
  }, [jobId]);

  return (
    <SectionCard
      icon={<Layers className="h-5 w-5" />}
      title="Batch Prediction"
      subtitle="Upload a CSV file to run predictions on thousands of rows in one job."
    >
      {/* Dropzone */}
      <FileDropzone
        onFileAccepted={(f) => void handleFileAccepted(f)}
        acceptedFormats={["csv"]}
        loading={uploadLoading}
      />

      {/* Uploaded file badge */}
      {fileId && fileName && (
        <div className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <FileUp className="h-4 w-4 text-emerald-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {fileName}
            </p>
            {nRows !== null && (
              <p className="text-xs text-muted-foreground font-mono">
                {nRows.toLocaleString()} rows ready
              </p>
            )}
          </div>
          <Badge
            variant="outline"
            className="border-emerald-500/30 text-emerald-400 text-xs flex-shrink-0"
          >
            Ready
          </Badge>
        </div>
      )}

      {/* Run button */}
      {fileId && !jobId && (
        <Button
          onClick={() => void handleRunBatch()}
          disabled={batchRunning}
          className="btn-glow w-full"
        >
          <span className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Run Batch Prediction
          </span>
        </Button>
      )}

      {/* Job progress */}
      {jobId && (
        <div className="rounded-xl border border-white/8 bg-white/2 p-4">
          <JobProgress
            jobId={jobId}
            onComplete={() => void handleJobComplete()}
          />
        </div>
      )}

      {/* Download button */}
      {jobComplete && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-accent-violet/20 bg-accent-violet/5 p-5 text-center">
          <p className="text-sm text-foreground font-medium">
            Batch predictions complete!
          </p>
          <p className="text-xs text-muted-foreground">
            {nRows != null
              ? `${nRows.toLocaleString()} predictions generated.`
              : "All rows processed."}
          </p>
          {downloadUrl ? (
            <a
              href={downloadUrl}
              download
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-4 py-2",
                "bg-accent-violet text-white text-sm font-medium",
                "hover:bg-accent-violet/80 transition-colors btn-glow",
              )}
            >
              <Download className="h-4 w-4" />
              Download Results
            </a>
          ) : (
            <p className="text-xs text-muted-foreground font-mono">
              Results stored in project output directory.
            </p>
          )}
        </div>
      )}
    </SectionCard>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PredictPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="font-display italic text-3xl font-bold text-foreground">
          Predict
        </h1>
        <p className="text-muted-foreground">
          Run single or batch predictions using the trained model.
        </p>
      </div>

      {/* Sections */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SinglePredictionSection projectId={projectId} />
        <BatchPredictionSection projectId={projectId} />
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-white/8">
        <Button
          variant="outline"
          className="border-white/10 hover:border-white/20"
          onClick={() => router.push(`/${projectId}/explainability`)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Explain
        </Button>

        <Button
          className="btn-glow"
          onClick={() => router.push(`/${projectId}/chat`)}
        >
          Continue to Chat
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
