"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, BarChart3, Layers, Brain, Clock } from "lucide-react";
import { projectsApi } from "@/lib/api/endpoints";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ProjectListItem } from "@/lib/api/types";

// ─── Domain badge colors ───────────────────────────────────────────────────────

const DOMAIN_COLORS: Record<string, string> = {
  healthcare: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  finance: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  ecommerce: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  marketing: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  hr: "bg-green-500/10 text-green-400 border-green-500/20",
  manufacturing: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  generic: "bg-white/10 text-white/60 border-white/10",
};

// ─── New Project Dialog ────────────────────────────────────────────────────────

function NewProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const router = useRouter();
  const { setCurrentProject } = useAppStore();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    if (!name.trim()) return;
    setLoading(true);
    try {
      sessionStorage.setItem("autods_new_project_name", name.trim());
      setCurrentProject(null);
      onOpenChange(false);
      router.push("/upload");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          autoFocus
        />
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={!name.trim() || loading}>
            {loading ? "Creating…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Project Card ─────────────────────────────────────────────────────────────

function ProjectCard({ project }: { project: ProjectListItem }) {
  const router = useRouter();
  const { setCurrentProject } = useAppStore();

  const domain = project.detected_domain ?? "generic";
  const badgeClass = DOMAIN_COLORS[domain] ?? DOMAIN_COLORS.generic;
  const step = project.current_step ?? "upload";
  const savedAt = project.saved_at
    ? new Date(project.saved_at).toLocaleDateString()
    : null;

  function handleOpen() {
    setCurrentProject(project.project_id);
    router.push(`/${project.project_id}/${step}`);
  }

  return (
    <button
      onClick={handleOpen}
      className={cn(
        "group text-left w-full rounded-xl border border-white/8 bg-white/3",
        "p-5 flex flex-col gap-3 transition-all duration-200",
        "hover:bg-white/6 hover:border-white/15 hover:shadow-lg",
      )}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-foreground truncate text-sm leading-snug">
          {project.name}
        </h3>
        {domain !== "generic" && (
          <span
            className={cn(
              "shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded-full border uppercase tracking-wide",
              badgeClass,
            )}
          >
            {domain}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {project.row_count != null && (
          <span className="flex items-center gap-1">
            <BarChart3 className="h-3 w-3" />
            {project.row_count.toLocaleString()} rows
          </span>
        )}
        {project.problem_type && (
          <span className="flex items-center gap-1">
            <Brain className="h-3 w-3 shrink-0" />
            {project.problem_type}
          </span>
        )}
        {project.best_model && (
          <span className="flex items-center gap-1">
            <Layers className="h-3 w-3 shrink-0" />
            {project.best_model}
          </span>
        )}
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-accent-violet/10 text-accent-violet border border-accent-violet/20 capitalize">
          {step}
        </span>
        {savedAt && (
          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            {savedAt}
          </span>
        )}
      </div>
    </button>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <div className="h-14 w-14 rounded-2xl bg-accent-violet/10 border border-accent-violet/20 flex items-center justify-center">
        <BarChart3 className="h-7 w-7 text-accent-violet" />
      </div>
      <div className="space-y-1">
        <p className="font-semibold text-foreground">No projects yet</p>
        <p className="text-sm text-muted-foreground">
          Upload a dataset to start your first analysis.
        </p>
      </div>
      <Button onClick={onNew} className="btn-glow mt-2">
        <Plus className="h-4 w-4 mr-2" />
        New project
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const [newOpen, setNewOpen] = useState(false);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
    staleTime: 30_000,
  });

  return (
    <div className="container max-w-5xl mx-auto px-4 py-8">
      {/* Header row */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {projects.length > 0
              ? `${projects.length} project${projects.length !== 1 ? "s" : ""}`
              : "Start a new analysis"}
          </p>
        </div>
        {projects.length > 0 && (
          <Button onClick={() => setNewOpen(true)} className="btn-glow">
            <Plus className="h-4 w-4 mr-2" />
            New project
          </Button>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-36 rounded-xl bg-white/5 animate-pulse border border-white/5"
            />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState onNew={() => setNewOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <ProjectCard key={p.project_id} project={p} />
          ))}
        </div>
      )}

      <NewProjectDialog open={newOpen} onOpenChange={setNewOpen} />
    </div>
  );
}
