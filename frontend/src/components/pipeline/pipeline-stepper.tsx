"use client";

import Link from "next/link";
import {
  Upload,
  Settings,
  BarChart3,
  Layers,
  Brain,
  Lightbulb,
  Target,
  MessageSquare,
  Download,
  Check,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// ─── Step definitions ─────────────────────────────────────────────────────────

interface StepDef {
  name: string;
  path: string;
  icon: LucideIcon;
  prerequisite?: string;
}

const STEPS: StepDef[] = [
  { name: "Upload", path: "upload", icon: Upload },
  { name: "Configure", path: "configure", icon: Settings, prerequisite: "upload" },
  { name: "EDA", path: "eda", icon: BarChart3, prerequisite: "configure" },
  { name: "Features", path: "features", icon: Layers, prerequisite: "eda" },
  { name: "Modeling", path: "modeling", icon: Brain, prerequisite: "features" },
  { name: "Explain", path: "explain", icon: Lightbulb, prerequisite: "modeling" },
  { name: "Predict", path: "predict", icon: Target, prerequisite: "modeling" },
  { name: "Chat", path: "chat", icon: MessageSquare, prerequisite: "modeling" },
  { name: "Download", path: "download", icon: Download, prerequisite: "modeling" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface PipelineStepperProps {
  currentStep: string;
  completedSteps: string[];
  projectId: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function PipelineStepper({
  currentStep,
  completedSteps,
  projectId,
}: PipelineStepperProps) {
  return (
    <nav aria-label="Pipeline steps" className="relative px-2 py-1">
      {/* Vertical connecting line */}
      <div
        className="absolute left-[1.625rem] top-4 bottom-4 w-px"
        style={{ background: "rgba(255,255,255,0.08)" }}
        aria-hidden
      />

      <ol className="flex flex-col gap-1">
        {STEPS.map((step) => {
          const isCompleted = completedSteps.includes(step.path);
          const isActive = currentStep === step.path;
          const isDisabled =
            !isCompleted &&
            !isActive &&
            step.prerequisite &&
            !completedSteps.includes(step.prerequisite);

          const Icon = step.icon;

          const circleClass = cn(
            "relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs transition-all",
            isCompleted &&
              "border-accent-green bg-accent-green/20 text-accent-green",
            isActive &&
              "border-accent-violet bg-accent-violet/20 text-accent-violet animate-pulse",
            !isCompleted && !isActive && !isDisabled &&
              "border-white/20 bg-white/5 text-muted-foreground",
            isDisabled &&
              "border-white/10 bg-transparent text-white/20 cursor-not-allowed",
          );

          const labelClass = cn(
            "text-sm font-medium transition-colors",
            isCompleted && "text-foreground",
            isActive && "text-accent-violet",
            !isCompleted && !isActive && !isDisabled && "text-muted-foreground",
            isDisabled && "text-white/20",
          );

          const statusBadge = isCompleted ? (
            <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-accent-green/10 text-accent-green border border-accent-green/20">
              done
            </span>
          ) : isActive ? (
            <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-accent-violet/10 text-accent-violet border border-accent-violet/20">
              active
            </span>
          ) : null;

          const inner = (
            <li key={step.path}>
              <Link
                href={isDisabled ? "#" : `/${projectId}/${step.path}`}
                aria-current={isActive ? "step" : undefined}
                aria-disabled={isDisabled ? true : undefined}
                onClick={isDisabled ? (e) => e.preventDefault() : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors",
                  !isDisabled && "hover:bg-white/5",
                  isDisabled && "pointer-events-none",
                )}
              >
                <span className={circleClass}>
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                </span>
                <span className={labelClass}>{step.name}</span>
                {statusBadge}
              </Link>
            </li>
          );

          if (isDisabled) {
            return (
              <Tooltip key={step.path}>
                <TooltipTrigger>{inner}</TooltipTrigger>
                <TooltipContent side="right" className="text-xs">
                  Complete{" "}
                  <span className="capitalize font-semibold">
                    {step.prerequisite}
                  </span>{" "}
                  first
                </TooltipContent>
              </Tooltip>
            );
          }

          return inner;
        })}
      </ol>
    </nav>
  );
}
