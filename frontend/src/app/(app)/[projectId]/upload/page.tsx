"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, GitMerge, ArrowRight } from "lucide-react";
import { toast } from "sonner";

import { uploadApi } from "@/lib/api/endpoints";
import { useAppStore } from "@/lib/store";
import { useQueryClient } from "@tanstack/react-query";
import type { UploadFileResponse, SampleDatasetInfo, JoinPlan } from "@/lib/api/types";

import { FileDropzone } from "@/components/pipeline/file-dropzone";
import { MetricCards } from "@/components/pipeline/metric-cards";
import { DataPreviewTable } from "@/components/pipeline/data-preview-table";
import { DataTable } from "@/components/pipeline/data-table";
import { SampleDatasetChips } from "@/components/pipeline/sample-dataset-chips";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ColumnInfo {
  name: string;
  type: string;
  missing_pct: number;
  unique: number;
  sample: unknown;
}

interface LoadedSource {
  source_id: string;
  label: string;
  response: UploadFileResponse;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseSchema(schema: Record<string, unknown>): ColumnInfo[] {
  return Object.entries(schema).map(([name, meta]) => {
    const m = (meta ?? {}) as Record<string, unknown>;
    return {
      name,
      type: String(m.dtype ?? m.type ?? "unknown"),
      missing_pct: Number(m.missing_pct ?? m.null_pct ?? 0),
      unique: Number(m.n_unique ?? m.unique ?? 0),
      sample: m.sample ?? null,
    };
  });
}

function estimateMemoryKb(n_rows: number, n_cols: number): number {
  return Math.round((n_rows * n_cols * 8) / 1024);
}

// ─── Connector options ────────────────────────────────────────────────────────

const CONNECTOR_TYPES = [
  { value: "postgresql", label: "PostgreSQL" },
  { value: "mysql", label: "MySQL" },
  { value: "bigquery", label: "BigQuery" },
  { value: "snowflake", label: "Snowflake" },
  { value: "s3", label: "AWS S3" },
  { value: "gcs", label: "Google Cloud Storage" },
  { value: "rest_api", label: "REST API" },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setCurrentProject } = useAppStore();

  // Primary source state
  const [primarySource, setPrimarySource] = useState<LoadedSource | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);

  // Sample datasets
  const [samples, setSamples] = useState<SampleDatasetInfo[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [loadingSampleName, setLoadingSampleName] = useState<string | undefined>();

  // Connector tab
  const [connectorType, setConnectorType] = useState("postgresql");
  const [connectingSource, setConnectingSource] = useState(false);

  // Multi-source join (secondary)
  const [joinOpen, setJoinOpen] = useState(false);
  const [secondarySource, setSecondarySource] = useState<LoadedSource | null>(null);
  const [uploadingSecondary, setUploadingSecondary] = useState(false);
  const [joinPlan, setJoinPlan] = useState<JoinPlan | null>(null);
  const [suggestingJoin, setSuggestingJoin] = useState(false);
  const [applyingJoin, setApplyingJoin] = useState(false);

  // Fetch sample datasets on mount
  useEffect(() => {
    uploadApi
      .listSamples()
      .then(setSamples)
      .catch(() => toast.error("Failed to load sample datasets"))
      .finally(() => setSamplesLoading(false));
  }, []);

  // Sync project id into store
  useEffect(() => {
    if (projectId) setCurrentProject(projectId);
  }, [projectId, setCurrentProject]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleFileDrop = useCallback(
    async (file: File) => {
      setUploadingFile(true);
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("project_id", projectId);
        const res = await uploadApi.file(form);
        setPrimarySource({ source_id: res.source_id, label: file.name, response: res });
        queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
        toast.success(`Uploaded ${file.name}`);
      } catch {
        toast.error("Upload failed. Please try again.");
      } finally {
        setUploadingFile(false);
      }
    },
    [projectId, queryClient],
  );

  const handleSampleSelect = useCallback(
    async (name: string) => {
      setLoadingSampleName(name);
      try {
        const res = await uploadApi.loadSample({ dataset_name: name });
        const ds = samples.find((s) => s.name === name);
        setPrimarySource({
          source_id: res.source_id,
          label: ds?.display_name ?? name,
          response: res,
        });
        queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
        toast.success(`Loaded ${ds?.display_name ?? name}`);
      } catch {
        toast.error("Failed to load sample dataset.");
      } finally {
        setLoadingSampleName(undefined);
      }
    },
    [samples, projectId, queryClient],
  );

  const handleConnectorSubmit = useCallback(async () => {
    setConnectingSource(true);
    try {
      const res = await uploadApi.connector({
        connector_type: connectorType,
        config: {},
      });
      setPrimarySource({
        source_id: res.source_id,
        label: connectorType,
        response: res,
      });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
      toast.success("Source connected");
    } catch {
      toast.error("Failed to connect source.");
    } finally {
      setConnectingSource(false);
    }
  }, [connectorType, projectId, queryClient]);

  const handleSecondaryDrop = useCallback(
    async (file: File) => {
      setUploadingSecondary(true);
      try {
        const form = new FormData();
        form.append("file", file);
        form.append("project_id", projectId);
        const res = await uploadApi.file(form);
        setSecondarySource({ source_id: res.source_id, label: file.name, response: res });
        setJoinPlan(null);
        toast.success(`Uploaded ${file.name}`);
      } catch {
        toast.error("Secondary upload failed.");
      } finally {
        setUploadingSecondary(false);
      }
    },
    [projectId],
  );

  const handleSuggestJoin = useCallback(async () => {
    if (!primarySource || !secondarySource) return;
    setSuggestingJoin(true);
    try {
      const res = await uploadApi.suggestJoin({
        project_id: projectId,
        left_source_id: primarySource.source_id,
        right_source_id: secondarySource.source_id,
      });
      setJoinPlan(res.plan);
      toast.success(`Join suggested (confidence: ${(res.confidence * 100).toFixed(0)}%)`);
    } catch {
      toast.error("Could not suggest join.");
    } finally {
      setSuggestingJoin(false);
    }
  }, [primarySource, secondarySource, projectId]);

  const handleApplyJoin = useCallback(async () => {
    if (!joinPlan) return;
    setApplyingJoin(true);
    try {
      const res = await uploadApi.applyJoin(joinPlan);
      // Replace primary source with joined result
      setPrimarySource((prev) =>
        prev
          ? {
              source_id: res.joined_source_id,
              label: `${prev.label} ⋈ ${secondarySource?.label ?? "secondary"}`,
              response: {
                ...prev.response,
                source_id: res.joined_source_id,
                n_rows: res.n_rows,
                n_cols: res.n_cols,
              },
            }
          : null,
      );
      setSecondarySource(null);
      setJoinPlan(null);
      setJoinOpen(false);
      toast.success(`Joined → ${res.n_rows.toLocaleString()} rows × ${res.n_cols} cols`);
    } catch {
      toast.error("Join failed.");
    } finally {
      setApplyingJoin(false);
    }
  }, [joinPlan, secondarySource]);

  const handleProceed = useCallback(() => {
    router.push(`/${projectId}/configure`);
  }, [router, projectId]);

  // ── Derived ─────────────────────────────────────────────────────────────────

  const columns = primarySource ? parseSchema(primarySource.response.schema) : [];
  const memoryKb = primarySource
    ? estimateMemoryKb(primarySource.response.n_rows, primarySource.response.n_cols)
    : 0;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="container max-w-4xl mx-auto px-4 py-10 flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Upload dataset</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Add your data via file, sample dataset, or an external connector.
        </p>
      </div>

      {/* ── Upload card ────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm">
        <Tabs defaultValue="file">
          <TabsList className="mb-6">
            <TabsTrigger value="file">File upload</TabsTrigger>
            <TabsTrigger value="samples">Sample datasets</TabsTrigger>
            <TabsTrigger value="connector">Connect to source</TabsTrigger>
          </TabsList>

          {/* Tab 1 – File */}
          <TabsContent value="file">
            <FileDropzone onFileAccepted={handleFileDrop} loading={uploadingFile} />
          </TabsContent>

          {/* Tab 2 – Samples */}
          <TabsContent value="samples">
            {samplesLoading ? (
              <div className="flex justify-center py-12">
                <div className="h-8 w-8 rounded-full border-2 border-accent-violet border-t-transparent animate-spin" />
              </div>
            ) : samples.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No sample datasets available.
              </p>
            ) : (
              <SampleDatasetChips
                datasets={samples}
                onSelect={handleSampleSelect}
                loading={!!loadingSampleName}
                loadingName={loadingSampleName}
              />
            )}
          </TabsContent>

          {/* Tab 3 – Connector */}
          <TabsContent value="connector">
            <div className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Connect directly to a database or cloud storage bucket.
              </p>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-foreground">
                  Connector type
                </label>
                <select
                  value={connectorType}
                  onChange={(e) => setConnectorType(e.target.value)}
                  className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent-violet"
                >
                  {CONNECTOR_TYPES.map((c) => (
                    <option key={c.value} value={c.value} className="bg-cosmic-900">
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-muted-foreground">
                Full connector configuration will be available after backend integration.
              </p>
              <Button
                onClick={handleConnectorSubmit}
                disabled={connectingSource}
                className="btn-glow self-start"
              >
                {connectingSource ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    Connecting…
                  </span>
                ) : (
                  "Connect"
                )}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* ── Post-upload section ────────────────────────────────────────────── */}
      {primarySource && (
        <>
          {/* Source label */}
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-accent-green animate-pulse" />
            <span className="text-sm font-mono text-muted-foreground">
              {primarySource.label}
            </span>
          </div>

          {/* Metric cards */}
          <MetricCards
            rows={primarySource.response.n_rows}
            columns={primarySource.response.n_cols}
            memoryKb={memoryKb}
          />

          {/* Column schema preview */}
          {columns.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-foreground">
                Column schema
              </h2>
              <DataPreviewTable columns={columns} />
            </div>
          )}

          {/* Raw data preview */}
          {primarySource.response.preview.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-foreground">
                Data preview
              </h2>
              <DataTable data={primarySource.response.preview} defaultRows={20} />
            </div>
          )}

          {/* ── Multi-source join ─────────────────────────────────────────── */}
          <Collapsible open={joinOpen} onOpenChange={setJoinOpen}>
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-xl border border-white/8 bg-white/2 px-5 py-3 text-left text-sm font-medium text-foreground transition-colors hover:bg-white/5">
              <GitMerge className="h-4 w-4 text-muted-foreground" />
              <span className="flex-1">Add another data source &amp; join</span>
              {joinOpen ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </CollapsibleTrigger>

            <CollapsibleContent className="mt-4 flex flex-col gap-4">
              <FileDropzone
                onFileAccepted={handleSecondaryDrop}
                loading={uploadingSecondary}
              />

              {secondarySource && (
                <div className="flex flex-col gap-3">
                  <p className="text-xs text-muted-foreground font-mono">
                    Secondary: {secondarySource.label} — {secondarySource.response.n_rows.toLocaleString()} rows ×{" "}
                    {secondarySource.response.n_cols} cols
                  </p>

                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={handleSuggestJoin}
                      disabled={suggestingJoin || applyingJoin}
                    >
                      {suggestingJoin ? (
                        <span className="flex items-center gap-2">
                          <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                          Analyzing…
                        </span>
                      ) : (
                        "Suggest join"
                      )}
                    </Button>

                    {joinPlan && (
                      <Button
                        className="btn-glow"
                        onClick={handleApplyJoin}
                        disabled={applyingJoin}
                      >
                        {applyingJoin ? (
                          <span className="flex items-center gap-2">
                            <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                            Joining…
                          </span>
                        ) : (
                          "Apply join"
                        )}
                      </Button>
                    )}
                  </div>

                  {joinPlan && (
                    <pre className="rounded-lg border border-white/8 bg-white/3 px-4 py-3 text-xs font-mono text-muted-foreground overflow-x-auto">
                      {JSON.stringify(joinPlan, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>

          {/* ── Proceed button ────────────────────────────────────────────── */}
          <div className="flex justify-end pt-2">
            <Button onClick={handleProceed} className="btn-glow gap-2 px-8">
              Proceed to configuration
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
