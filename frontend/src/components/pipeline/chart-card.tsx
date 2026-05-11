"use client";

import dynamic from "next/dynamic";
import { Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { mergeCosmicLayout } from "@/lib/plotly-theme";

// ─── Dynamic import (no SSR — Plotly is browser-only) ─────────────────────────

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChartCardProps {
  title: string;
  plotlyData: Plotly.Data[];
  plotlyLayout?: Record<string, unknown>;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ChartCard({
  title,
  plotlyData,
  plotlyLayout = {},
  className,
}: ChartCardProps) {
  const layout = mergeCosmicLayout(plotlyLayout);

  function handleDownload() {
    // Plotly.downloadImage requires a div id or PlotlyHTMLElement reference.
    // We use the global Plotly object injected by react-plotly.js at runtime.
    if (typeof window === "undefined") return;

    // Sanitise the title into a safe filename
    const filename = title.toLowerCase().replace(/[^a-z0-9]+/g, "_");

    const graphDivs = document.querySelectorAll<HTMLDivElement>(
      `[data-chart-title="${CSS.escape(title)}"]`,
    );
    const div = graphDivs[0];
    if (!div) return;

    const Plotly = (window as Window & { Plotly?: typeof import("plotly.js") }).Plotly;
    if (Plotly?.downloadImage) {
      Plotly.downloadImage(div, {
        format: "png",
        filename,
        width: 1200,
        height: 600,
      });
    }
  }

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border border-white/10",
        "bg-white/3 backdrop-blur-sm overflow-hidden",
        className,
      )}
    >
      {/* Card header */}
      <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        <button
          type="button"
          onClick={handleDownload}
          title="Download PNG"
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5",
            "text-xs text-muted-foreground border border-white/10",
            "hover:border-accent-violet/40 hover:text-accent-violet hover:bg-accent-violet/8",
            "transition-all duration-150",
          )}
        >
          <Download className="h-3.5 w-3.5" />
          PNG
        </button>
      </div>

      {/* Chart body */}
      <div
        className="min-h-[300px] w-full"
        data-chart-title={title}
      >
        <Plot
          data={plotlyData}
          layout={layout as Partial<Plotly.Layout>}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%", minHeight: "300px" }}
          useResizeHandler
        />
      </div>
    </div>
  );
}
