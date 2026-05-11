"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/hooks/useAuth";
import { useAppStore } from "@/lib/store";
import { projectsApi } from "@/lib/api/endpoints";
import { Header } from "@/components/shared/header";
import { DesktopSidebar, MobileSidebar } from "@/components/shared/sidebar";
import { PageTransition } from "@/components/shared/page-transition";
import { ErrorBoundary } from "@/components/shared/error-boundary";

// ─── App Shell Layout ─────────────────────────────────────────────────────────

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading } = useAuth();
  const { currentProjectId, setCurrentProject } = useAppStore();

  // Derive projectId and currentStep from URL
  // Possible patterns:
  //   /projects           → no projectId
  //   /upload             → no projectId (new project flow)
  //   /{projectId}/{step} → projectId + step
  const segments = pathname.split("/").filter(Boolean);
  const isProjectRoute = segments.length >= 2 && segments[0] !== "projects" && segments[0] !== "upload";
  const urlProjectId = isProjectRoute ? segments[0] : null;
  const currentStep = isProjectRoute ? segments[1] : segments[0] ?? "projects";

  // Active project: URL takes priority over Zustand store
  const activeProjectId = urlProjectId ?? currentProjectId;

  // Sync URL project into Zustand so sidebar picker stays in sync
  useEffect(() => {
    if (urlProjectId && urlProjectId !== currentProjectId) {
      setCurrentProject(urlProjectId);
    }
  }, [urlProjectId, currentProjectId, setCurrentProject]);

  // Auth guard
  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  // Fetch active project for name + completed steps
  const { data: project } = useQuery({
    queryKey: ["projects", activeProjectId],
    queryFn: () => projectsApi.get(activeProjectId!),
    enabled: !!activeProjectId,
    staleTime: 30_000,
  });

  const completedSteps: string[] = project?.completed_steps ?? [];
  const projectName = project?.name;

  if (isLoading) {
    return (
      <div className="aurora-bg min-h-screen flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-accent-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  const sidebarProps = {
    projectId: activeProjectId,
    currentStep,
    completedSteps,
  };

  return (
    <div className="flex h-screen overflow-hidden bg-cosmic-900">
      {/* Desktop sidebar */}
      <DesktopSidebar {...sidebarProps} />

      {/* Right panel: header + page content */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header
          projectName={projectName}
          leftSlot={<MobileSidebar {...sidebarProps} />}
        />
        <main className="flex-1 overflow-y-auto">
          <ErrorBoundary>
            <PageTransition>
              {children}
            </PageTransition>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
