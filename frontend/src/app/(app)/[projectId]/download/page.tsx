"use client";

import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  FileText,
  FileDown,
  BarChart2,
  Code,
  Download,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { JobProgress } from "@/components/pipeline/job-progress";
import { downloadApi, jobsApi } from "@/lib/api/endpoints";
import type { ReportResponse } from "@/lib/api/types";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

// ─── Types ────────────────────────────────────────────────────────────────────

type ReportFormat = "html" | "pdf" | "executive_summary" | "notebook";

interface CardState {
  jobId: string | null;
  generating: boolean;
  report: ReportResponse | null;
  error: string | null;
}

const INITIAL_CARD: CardState = {
  jobId: null,
  generating: false,
  report: null,
  error: null,
};

// ─── Format config ────────────────────────────────────────────────────────────

interface FormatConfig {
  key: ReportFormat;
  label: string;
  description: string;
  Icon: React.ElementType;
  colorClass: string;
  iconBg: string;
}

const FORMATS: FormatConfig[] = [
  {
    key: "html",
    label: "Interactive HTML Report",
    description: "Full analysis with interactive Plotly charts",
    Icon: FileText,
    colorClass: "text-accent-violet",
    iconBg: "bg-accent-violet/10",
  },
  {
    key: "pdf",
    label: "PDF Report",
    description: "Print-ready PDF document",
    Icon: FileDown,
    colorClass: "text-cyan-400",
    iconBg: "bg-cyan-400/10",
  },
  {
    key: "executive_summary",
    label: "Executive Summary",
    description: "One-page overview for stakeholders",
    Icon: BarChart2,
    colorClass: "text-pink-400",
    iconBg: "bg-pink-400/10",
  },
  {
    key: "notebook",
    label: "Jupyter Notebook",
    description: "Reproducible notebook with all code",
    Icon: Code,
    colorClass: "text-green-400",
    iconBg: "bg-green-400/10",
  },
];

// ─── Report card ──────────────────────────────────────────────────────────────

function ReportCard({
  config,
  state,
  onGenerate,
  onComplete,
}: {
  config: FormatConfig;
  state: CardState;
  onGenerate: (fmt: ReportFormat) => void;
  onComplete: (fmt: ReportFormat) => void;
}) {
  const { Icon, label, description, colorClass, iconBg, key } = config;
  const { jobId, generating, report, error } = state;

  return (
    <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className={cn("rounded-xl p-3 flex-shrink-0", iconBg)}>
          <Icon className={cn("h-6 w-6", colorClass)} strokeWidth={1.5} />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="font-display italic text-lg font-semibold text-foreground leading-tight">
            {label}
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
        </div>
      </div>

      {/* Progress */}
      {jobId && !report && (
        <JobProgress
          jobId={jobId}
          onComplete={() => onComplete(key)}
        />
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/8 px-3 py-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-400" />
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {/* Report ready */}
      {report && (
        <div className="rounded-xl border border-white/8 bg-white/4 px-4 py-3 flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground font-mono">
              Generated {format(new Date(report.generated_at), "MMM d, h:mm a")}
            </span>
            <a
              href={report.download_url}
              download
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                "border border-white/10 bg-white/6 text-foreground",
                "hover:border-white/20 hover:bg-white/10",
              )}
            >
              <Download className="h-3.5 w-3.5" />
              Download
            </a>
          </div>
        </div>
      )}

      {/* Generate button */}
      {!jobId && (
        <Button
          onClick={() => onGenerate(key)}
          disabled={generating}
          className={cn("btn-glow w-full mt-auto")}
        >
          {generating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Starting…
            </>
          ) : report ? (
            <>
              <Icon className="mr-2 h-4 w-4" />
              Regenerate
            </>
          ) : (
            <>
              <Icon className="mr-2 h-4 w-4" />
              Generate
            </>
          )}
        </Button>
      )}

      {/* Regenerate after done */}
      {jobId && report && (
        <Button
          variant="outline"
          onClick={() => onGenerate(key)}
          className="w-full border-white/10 hover:border-white/20"
        >
          <Icon className="mr-2 h-4 w-4" />
          Regenerate
        </Button>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DownloadPage() {
  const { projectId } = useParams<{ projectId: string }>();

  const [htmlState, setHtmlState] = useState<CardState>(INITIAL_CARD);
  const [pdfState, setPdfState] = useState<CardState>(INITIAL_CARD);
  const [execState, setExecState] = useState<CardState>(INITIAL_CARD);
  const [notebookState, setNotebookState] = useState<CardState>(INITIAL_CARD);

  const getState = (fmt: ReportFormat) => {
    if (fmt === "html") return htmlState;
    if (fmt === "pdf") return pdfState;
    if (fmt === "executive_summary") return execState;
    return notebookState;
  };

  const setState = useCallback(
    (fmt: ReportFormat, updater: (prev: CardState) => CardState) => {
      if (fmt === "html") setHtmlState(updater);
      else if (fmt === "pdf") setPdfState(updater);
      else if (fmt === "executive_summary") setExecState(updater);
      else setNotebookState(updater);
    },
    [],
  );

  const handleGenerate = useCallback(
    async (fmt: ReportFormat) => {
      setState(fmt, (prev) => ({
        ...prev,
        generating: true,
        jobId: null,
        error: null,
        report: null,
      }));
      try {
        const res = await downloadApi.generate({
          project_id: projectId,
          format: fmt,
        });
        setState(fmt, (prev) => ({
          ...prev,
          generating: false,
          jobId: res.job_id,
        }));
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to start report generation.";
        toast.error(msg);
        setState(fmt, (prev) => ({
          ...prev,
          generating: false,
          error: msg,
        }));
      }
    },
    [projectId, setState],
  );

  const handleComplete = useCallback(
    async (fmt: ReportFormat) => {
      const jobId = getState(fmt).jobId;
      if (!jobId) return;
      try {
        const result = await jobsApi.result(jobId);
        const payload = result.result as Record<string, string>;
        const report: ReportResponse = {
          report_id: payload.report_id ?? jobId,
          download_url: payload.download_url ?? payload.url ?? "",
          format: fmt,
          generated_at: payload.generated_at ?? new Date().toISOString(),
        };
        setState(fmt, (prev) => ({ ...prev, report }));
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to fetch report.";
        toast.error(msg);
        setState(fmt, (prev) => ({ ...prev, error: msg }));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setState, htmlState, pdfState, execState, notebookState],
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-white/8 px-6 py-4">
        <h1 className="font-display italic text-2xl font-bold text-foreground">
          Download Reports
        </h1>
        <p className="text-sm text-muted-foreground">
          Generate and download your analysis outputs in multiple formats.
        </p>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 max-w-4xl mx-auto">
          {FORMATS.map((config) => (
            <ReportCard
              key={config.key}
              config={config}
              state={getState(config.key)}
              onGenerate={handleGenerate}
              onComplete={handleComplete}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
