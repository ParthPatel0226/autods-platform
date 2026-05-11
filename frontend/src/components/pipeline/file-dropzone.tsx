"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FileDropzoneProps {
  onFileAccepted: (file: File) => void;
  maxSizeMb?: number;
  acceptedFormats?: string[];
  loading?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DEFAULT_FORMATS = ["csv", "xlsx", "xls", "parquet", "json", "tsv"];

function buildAccept(formats: string[]): Record<string, string[]> {
  const map: Record<string, string[]> = {
    "text/csv": [".csv", ".tsv"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/vnd.ms-excel": [".xls"],
    "application/octet-stream": [".parquet"],
    "application/json": [".json"],
    "text/tab-separated-values": [".tsv"],
  };

  // filter to only requested formats
  const exts = formats.map((f) => `.${f.toLowerCase()}`);
  const filtered: Record<string, string[]> = {};
  for (const [mime, mimeExts] of Object.entries(map)) {
    const matched = mimeExts.filter((e) => exts.includes(e));
    if (matched.length > 0) filtered[mime] = matched;
  }
  return filtered;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FileDropzone({
  onFileAccepted,
  maxSizeMb = 200,
  acceptedFormats = DEFAULT_FORMATS,
  loading = false,
}: FileDropzoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFileAccepted(accepted[0]);
    },
    [onFileAccepted],
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      accept: buildAccept(acceptedFormats),
      maxSize: maxSizeMb * 1024 * 1024,
      multiple: false,
      disabled: loading,
    });

  const formatList = acceptedFormats.map((f) => f.toUpperCase()).join(", ");
  const rejection = fileRejections[0]?.errors[0]?.message;

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative flex cursor-pointer flex-col items-center justify-center gap-4",
        "rounded-xl border-2 border-dashed px-8 py-16 text-center transition-all duration-200",
        isDragActive
          ? "border-accent-violet bg-accent-violet/5 shadow-[0_0_24px_rgba(139,92,246,0.25)]"
          : "border-white/20 hover:border-accent-violet hover:bg-white/3",
        loading && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />

      {loading ? (
        <>
          <div className="h-12 w-12 rounded-full border-2 border-accent-violet border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">Uploading…</p>
        </>
      ) : (
        <>
          <UploadCloud
            className={cn(
              "h-12 w-12 transition-colors",
              isDragActive ? "text-accent-violet" : "text-white/40",
            )}
            strokeWidth={1.5}
          />

          <div className="space-y-1">
            <p
              className={cn(
                "font-display italic text-xl font-semibold transition-colors",
                isDragActive ? "text-accent-violet" : "text-foreground",
              )}
            >
              {isDragActive ? "Drop it!" : "Drop your dataset to begin"}
            </p>
            {!isDragActive && (
              <p className="text-sm text-muted-foreground">
                or click to browse
              </p>
            )}
          </div>

          <p className="text-xs text-white/30 font-mono">
            {maxSizeMb}MB per file • {formatList}
          </p>

          {rejection && (
            <p className="text-xs text-destructive mt-1">{rejection}</p>
          )}
        </>
      )}
    </div>
  );
}
