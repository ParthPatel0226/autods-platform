"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

import { configureApi, metaApi } from "@/lib/api/endpoints";
import type {
  DomainDetectionResponse,
  DomainConfig,
  ConfigureRequest,
} from "@/lib/api/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const DOMAIN_EMOJI: Record<string, string> = {
  healthcare: "🏥",
  finance: "💰",
  ecommerce: "🛒",
  marketing: "📊",
  hr: "👥",
  manufacturing: "🏭",
  generic: "📈",
};

const MODES = [
  {
    value: "auto" as const,
    label: "Auto",
    subtitle: "Fully Autonomous",
    desc: "System makes all decisions. Zero configuration required.",
    recommended: false,
  },
  {
    value: "guided" as const,
    label: "Guided",
    subtitle: "Interactive",
    desc: "System recommends, you approve at each step.",
    recommended: true,
  },
  {
    value: "expert" as const,
    label: "Expert",
    subtitle: "Full Control",
    desc: "Specify every parameter and decision yourself.",
    recommended: false,
  },
];

const PROBLEM_TYPES = [
  { value: "classification", label: "Classification" },
  { value: "regression", label: "Regression" },
  { value: "clustering", label: "Clustering" },
  { value: "time_series", label: "Time Series" },
];

const GOALS_BY_DOMAIN: Record<string, string[]> = {
  healthcare: [
    "Predict patient readmission",
    "Predict mortality risk",
    "Analyze patient outcomes",
    "Predict length of stay",
    "Identify high-risk patients",
  ],
  finance: [
    "Credit risk scoring",
    "Fraud detection",
    "Predict loan default",
    "Customer churn prediction",
    "Revenue forecasting",
  ],
  ecommerce: [
    "Customer churn prediction",
    "Customer lifetime value estimation",
    "Product recommendation",
    "Demand forecasting",
    "Cart abandonment prediction",
  ],
  marketing: [
    "Campaign response prediction",
    "Customer segmentation",
    "Churn prediction",
    "Attribution modeling",
    "Lead scoring",
  ],
  hr: [
    "Employee attrition prediction",
    "Compensation equity analysis",
    "Performance prediction",
    "Hiring success prediction",
    "Engagement analysis",
  ],
  manufacturing: [
    "Predictive maintenance",
    "Quality defect detection",
    "OEE optimization",
    "Supply chain forecasting",
    "Energy consumption optimization",
  ],
  generic: [
    "Binary classification",
    "Multi-class classification",
    "Regression / value prediction",
    "Clustering / segmentation",
    "Anomaly detection",
    "Time series forecasting",
  ],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

interface ColumnInfo {
  name: string;
  dtype: string;
}

function parseStoredSchema(raw: string): ColumnInfo[] {
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    return Object.entries(obj).map(([name, meta]) => {
      const m = (meta ?? {}) as Record<string, unknown>;
      return { name, dtype: String(m.dtype ?? m.type ?? "unknown") };
    });
  } catch {
    return [];
  }
}

function inferProblemType(columns: ColumnInfo[], targetName: string): string {
  if (!targetName) return "clustering";
  const col = columns.find((c) => c.name === targetName);
  if (!col) return "classification";
  const d = col.dtype.toLowerCase();
  if (d.includes("float") || d.includes("int") || d === "numeric") return "regression";
  return "classification";
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ConfigurePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  // ── Domain
  const [detection, setDetection] = useState<DomainDetectionResponse | null>(null);
  const [detecting, setDetecting] = useState(true);
  const [domain, setDomain] = useState("");
  const [allDomains, setAllDomains] = useState<DomainConfig[]>([]);
  const [overriding, setOverriding] = useState(false);

  // ── Mode
  const [mode, setMode] = useState<"auto" | "guided" | "expert">("guided");

  // ── Target
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [targetColumn, setTargetColumn] = useState("");
  const [problemType, setProblemType] = useState("classification");
  const [problemOverride, setProblemOverride] = useState(false);

  // ── Goal
  const [goal, setGoal] = useState("");
  const [customGoal, setCustomGoal] = useState("");

  // ── Submit
  const [submitting, setSubmitting] = useState(false);

  // ── Init
  useEffect(() => {
    // Load schema columns from sessionStorage (stored by upload page)
    const stored = sessionStorage.getItem(`autods_schema_${projectId}`);
    if (stored) {
      setColumns(parseStoredSchema(stored));
    }

    // Load domain list for override dropdown
    metaApi
      .domains()
      .then((res) => setAllDomains(res.domains))
      .catch(() => null);

    // Detect domain
    configureApi
      .detectDomain({
        project_id: projectId,
        domain: "",
        problem_type: "classification",
        user_goal: "",
      })
      .then((res) => {
        setDetection(res);
        setDomain(res.detected_domain);
        const goals = GOALS_BY_DOMAIN[res.detected_domain] ?? GOALS_BY_DOMAIN.generic;
        setGoal(goals[0] ?? "");
      })
      .catch(() => {
        toast.error("Domain detection failed. Please select manually.");
        setDomain("generic");
        setGoal(GOALS_BY_DOMAIN.generic[0]);
      })
      .finally(() => setDetecting(false));
  }, [projectId]);

  // Auto-infer problem type when target column changes
  useEffect(() => {
    if (!problemOverride) {
      setProblemType(inferProblemType(columns, targetColumn));
    }
  }, [targetColumn, columns, problemOverride]);

  const handleDomainChange = useCallback(
    (newDomain: string) => {
      setDomain(newDomain);
      setOverriding(false);
      const goals = GOALS_BY_DOMAIN[newDomain] ?? GOALS_BY_DOMAIN.generic;
      setGoal(goals[0] ?? "");
    },
    [],
  );

  const handleStartPipeline = useCallback(async () => {
    setSubmitting(true);
    try {
      const body: ConfigureRequest = {
        project_id: projectId,
        domain,
        target_column: targetColumn || null,
        problem_type: problemType,
        user_mode: mode,
        user_goal: goal === "custom" ? customGoal : goal,
      };
      await configureApi.setTarget(body);
      await configureApi.startPipeline(body);
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
      router.push(`/${projectId}/eda`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start pipeline");
    } finally {
      setSubmitting(false);
    }
  }, [projectId, domain, targetColumn, problemType, mode, goal, customGoal, queryClient, router]);

  const domainEmoji = DOMAIN_EMOJI[domain] ?? "📊";
  const domainGoals = GOALS_BY_DOMAIN[domain] ?? GOALS_BY_DOMAIN.generic;

  return (
    <div className="container max-w-4xl mx-auto px-4 py-10 flex flex-col gap-8">
      {/* Heading */}
      <div>
        <h1 className="text-2xl font-display font-semibold tracking-tight">
          Configure Analysis
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Review the detected domain and set your analysis preferences.
        </p>
      </div>

      {/* ── Section 1: Domain Detection ───────────────────────────────────── */}
      <section className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Domain Detection
          </h2>
          {!overriding && !detecting && (
            <button
              onClick={() => setOverriding(true)}
              className="text-xs text-accent-violet hover:text-accent-purple transition-colors"
            >
              Override
            </button>
          )}
        </div>

        {detecting ? (
          <div className="flex items-center gap-3 py-2">
            <div className="h-5 w-5 rounded-full border-2 border-accent-violet border-t-transparent animate-spin" />
            <span className="text-sm text-muted-foreground">Detecting domain…</span>
          </div>
        ) : overriding ? (
          <div className="flex items-center gap-3">
            <select
              value={domain}
              onChange={(e) => handleDomainChange(e.target.value)}
              className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent-violet"
            >
              {allDomains.length > 0
                ? allDomains.map((d) => (
                    <option key={d.domain_name} value={d.domain_name} className="bg-cosmic-900">
                      {d.icon ?? DOMAIN_EMOJI[d.domain_name] ?? "📊"} {d.display_name}
                    </option>
                  ))
                : Object.entries(DOMAIN_EMOJI).map(([k, emoji]) => (
                    <option key={k} value={k} className="bg-cosmic-900">
                      {emoji} {k.charAt(0).toUpperCase() + k.slice(1)}
                    </option>
                  ))}
            </select>
            <button
              onClick={() => setOverriding(false)}
              className="px-3 py-2 text-xs rounded-lg border border-white/10 bg-white/5 hover:bg-white/8 transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{domainEmoji}</span>
              <div>
                <p className="text-base font-semibold capitalize">{domain}</p>
                {detection && (
                  <p className="text-xs text-muted-foreground font-mono">
                    {Math.round(detection.confidence * 100)}% confidence
                  </p>
                )}
              </div>
            </div>

            {detection && detection.evidence.length > 0 && (
              <ul className="flex flex-col gap-1 pl-1">
                {detection.evidence.slice(0, 4).map((e, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="mt-px text-accent-violet">•</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* ── Section 2: Analysis Mode ──────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Analysis Mode
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {MODES.map((m) => {
            const selected = mode === m.value;
            return (
              <div key={m.value} className="relative pt-3">
                {m.recommended && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-widest bg-accent-violet text-white shadow-[0_0_12px_rgba(168,85,247,0.5)]">
                      Recommended
                    </span>
                  </div>
                )}
                <button
                  onClick={() => setMode(m.value)}
                  className={`w-full flex flex-col gap-1.5 p-4 rounded-xl border transition-all duration-200 text-left ${
                    selected
                      ? "border-accent-violet bg-accent-violet/10 shadow-[0_0_20px_rgba(168,85,247,0.2)]"
                      : "border-white/8 bg-white/2 hover:border-white/20 hover:bg-white/4"
                  }`}
                >
                  <span
                    className={`text-sm font-semibold ${
                      selected ? "text-accent-violet" : "text-foreground"
                    }`}
                  >
                    {m.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{m.subtitle}</span>
                  <span className="text-xs text-muted-foreground/70 mt-1 leading-relaxed">
                    {m.desc}
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Section 3: Target & Problem Type ─────────────────────────────── */}
      <section className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Target &amp; Problem Type
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Target column */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-muted-foreground">Target Column</label>
            <select
              value={targetColumn}
              onChange={(e) => {
                setTargetColumn(e.target.value);
                setProblemOverride(false);
              }}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent-violet"
            >
              <option value="" className="bg-cosmic-900">
                (none — unsupervised)
              </option>
              {columns.map((c) => (
                <option key={c.name} value={c.name} className="bg-cosmic-900">
                  {c.name}
                </option>
              ))}
            </select>
            {columns.length === 0 && (
              <p className="text-xs text-muted-foreground/60">
                Upload a dataset first to see columns here.
              </p>
            )}
          </div>

          {/* Problem type */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-muted-foreground">Problem Type</label>
              {!problemOverride && (
                <span className="text-[10px] font-mono text-accent-cyan uppercase tracking-widest">
                  auto-detected
                </span>
              )}
            </div>
            <select
              value={problemType}
              onChange={(e) => {
                setProblemType(e.target.value);
                setProblemOverride(true);
              }}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent-violet"
            >
              {PROBLEM_TYPES.map((pt) => (
                <option key={pt.value} value={pt.value} className="bg-cosmic-900">
                  {pt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* ── Section 4: Analysis Goal ──────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Analysis Goal
        </h2>

        <div className="flex flex-col gap-3">
          <select
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent-violet"
          >
            {domainGoals.map((g) => (
              <option key={g} value={g} className="bg-cosmic-900">
                {g}
              </option>
            ))}
            <option value="custom" className="bg-cosmic-900">
              Custom — I&apos;ll describe what I want
            </option>
          </select>

          {goal === "custom" && (
            <textarea
              value={customGoal}
              onChange={(e) => setCustomGoal(e.target.value)}
              placeholder="Describe your analysis goal…"
              rows={3}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-accent-violet resize-none"
            />
          )}
        </div>
      </section>

      {/* ── Start Pipeline ────────────────────────────────────────────────── */}
      <button
        onClick={handleStartPipeline}
        disabled={submitting || detecting}
        className="btn-glow w-full flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? (
          <>
            <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
            Starting pipeline…
          </>
        ) : (
          <>
            Start Pipeline
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>
    </div>
  );
}
