"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { projectsApi, uploadApi } from "@/lib/api/endpoints";
import { useAppStore } from "@/lib/store";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

// ─── Upload Page (New Project) ────────────────────────────────────────────────

export default function UploadPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setCurrentProject } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pre-fill name from session storage (set by sidebar "New project" dialog)
  useEffect(() => {
    const stored = sessionStorage.getItem("autods_new_project_name");
    if (stored) {
      setName(stored);
      sessionStorage.removeItem("autods_new_project_name");
    }
  }, []);

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    if (picked) setFile(picked);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !file) return;

    setError(null);
    setLoading(true);

    try {
      // 1. Create the project record
      const project = await projectsApi.create({ name: name.trim() });

      // 2. Upload the file
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", project.project_id);
      await uploadApi.file(form);

      // 3. Sync Zustand + invalidate project list
      setCurrentProject(project.project_id);
      queryClient.invalidateQueries({ queryKey: ["projects"] });

      // 4. Navigate to configure step
      router.push(`/${project.project_id}/configure`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = name.trim().length > 0 && file !== null && !loading;

  return (
    <div className="container max-w-2xl mx-auto px-4 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground">New project</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Name your project and upload a dataset to begin.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {/* Project name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-foreground">
            Project name
          </label>
          <Input
            placeholder="e.g. Customer Churn Analysis"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
            autoFocus
          />
        </div>

        {/* File drop zone */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-foreground">Dataset</label>
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={cn(
              "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-all",
              dragging
                ? "border-accent-violet bg-accent-violet/10"
                : file
                ? "border-accent-green/40 bg-accent-green/5"
                : "border-white/15 hover:border-white/25 hover:bg-white/3",
            )}
          >
            {file ? (
              <>
                <FileText className="h-8 w-8 text-accent-green" />
                <div className="text-center">
                  <p className="text-sm font-medium text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Remove
                </button>
              </>
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div className="text-center">
                  <p className="text-sm font-medium text-foreground">
                    {dragging ? "Drop to upload" : "Drag & drop or click to browse"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    CSV, Excel, Parquet, JSON, and more
                  </p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv,.xlsx,.xls,.parquet,.json,.jsonl,.tsv,.txt"
            onChange={handleFileChange}
            disabled={loading}
          />
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* Submit */}
        <Button
          type="submit"
          disabled={!canSubmit}
          className={cn("btn-glow self-start px-8", loading && "opacity-70")}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
              Uploading…
            </span>
          ) : (
            "Create & Upload"
          )}
        </Button>
      </form>
    </div>
  );
}
