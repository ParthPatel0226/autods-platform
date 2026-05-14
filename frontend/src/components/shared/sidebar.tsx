"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Settings, Menu } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { projectsApi, metaApi } from "@/lib/api/endpoints";
import { PipelineStepper } from "@/components/pipeline/pipeline-stepper";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";

// ─── Props ────────────────────────────────────────────────────────────────────

interface SidebarProps {
  projectId: string | null;
  currentStep: string;
  completedSteps: string[];
}

// ─── Cost display ─────────────────────────────────────────────────────────────

function CostDisplay({ projectId }: { projectId: string }) {
  const { data } = useQuery({
    queryKey: ["meta", "costs", projectId],
    queryFn: () => metaApi.costs(projectId),
    refetchInterval: 30_000,
    enabled: !!projectId,
  });

  if (!data) return null;

  // Estimate cost: ~$0.003 per 1K input tokens (rough Gemini/Claude blended)
  const tokens = data.api_token_count ?? 0;
  const estimatedCost = ((tokens * 0.003) / 1000).toFixed(3);

  return (
    <p className="text-xs text-muted-foreground font-mono tabular-nums">
      Tokens: {tokens.toLocaleString()} | ${estimatedCost}
    </p>
  );
}

// ─── New Project Dialog ───────────────────────────────────────────────────────

function NewProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setCurrentProject } = useAppStore();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    if (!name.trim()) return;
    setLoading(true);
    try {
      const project = await projectsApi.create({ name: name.trim() });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCurrentProject(project.project_id);
      onOpenChange(false);
      router.push(`/${project.project_id}/upload`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create project");
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
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
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

// ─── Sidebar inner content ────────────────────────────────────────────────────

function SidebarContent({ projectId, currentStep, completedSteps }: SidebarProps) {
  const router = useRouter();
  const { setCurrentProject } = useAppStore();
  const [newProjectOpen, setNewProjectOpen] = useState(false);

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  const selectedProject = projects.find((p) => p.project_id === projectId);

  function handleProjectChange(value: string | null) {
    if (!value) return;
    if (value === "__new__") {
      setNewProjectOpen(true);
      return;
    }
    setCurrentProject(value);
    const project = projects.find((p) => p.project_id === value);
    const step = project?.current_step ?? "upload";
    router.push(`/${value}/${step}`);
  }

  return (
    <div className="flex h-full flex-col gap-0">
      {/* ── Top: project selector ── */}
      <div className="flex flex-col gap-2 p-3 border-b border-white/8">
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground px-0.5">
          Project
        </p>
        <Select
          value={selectedProject ? projectId! : ""}
          onValueChange={handleProjectChange}
        >
          <SelectTrigger
            className="w-full bg-white/5 border-white/10 text-sm"
            size="default"
          >
            <span className="truncate">
              {selectedProject
                ? selectedProject.name
                : projectsLoading
                  ? "Loading…"
                  : "Select a project…"}
            </span>
          </SelectTrigger>
          <SelectContent align="start" alignItemWithTrigger={false}>
            {projects.map((p) => (
              <SelectItem key={p.project_id} value={p.project_id}>
                {p.name}
              </SelectItem>
            ))}
            <Separator className="my-1" />
            <SelectItem value="__new__">
              <Plus className="h-3.5 w-3.5 shrink-0" />
              New project
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Middle: pipeline stepper ── */}
      <div className="flex-1 overflow-y-auto py-2">
        {projectId ? (
          <PipelineStepper
            projectId={projectId}
            currentStep={currentStep}
            completedSteps={completedSteps}
          />
        ) : (
          <p className="px-4 py-6 text-xs text-muted-foreground text-center">
            Select or create a project to begin.
          </p>
        )}
      </div>

      {/* ── Bottom: cost + settings ── */}
      <div className="flex flex-col gap-2 p-3 border-t border-white/8">
        {projectId && <CostDisplay projectId={projectId} />}
        <Separator className="opacity-50" />
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-muted-foreground",
            "transition-colors hover:bg-white/5 hover:text-foreground",
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          Settings
        </Link>
      </div>

      <NewProjectDialog
        open={newProjectOpen}
        onOpenChange={setNewProjectOpen}
      />
    </div>
  );
}

// ─── Desktop sidebar ──────────────────────────────────────────────────────────

export function DesktopSidebar(props: SidebarProps) {
  const { sidebarOpen } = useAppStore();

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col shrink-0 w-56",
        "bg-cosmic-800/50 backdrop-blur-xl border-r border-white/10",
        "transition-all duration-200",
        !sidebarOpen && "w-0 overflow-hidden",
      )}
    >
      <SidebarContent {...props} />
    </aside>
  );
}

// ─── Mobile sidebar (Sheet) ───────────────────────────────────────────────────

export function MobileSidebar(props: SidebarProps) {
  return (
    <Sheet>
      <SheetTrigger
        className="md:hidden inline-flex h-8 w-8 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Open navigation"
      >
        <Menu className="h-4 w-4" />
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-56 p-0 bg-cosmic-800/80 backdrop-blur-xl border-r border-white/10"
      >
        <SidebarContent {...props} />
      </SheetContent>
    </Sheet>
  );
}

// ─── Public export ────────────────────────────────────────────────────────────

export function Sidebar(props: SidebarProps) {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...props} />
    </>
  );
}
