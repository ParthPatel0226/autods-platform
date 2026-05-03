export const COSMIC_PLOTLY_LAYOUT = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: {
    family: "Inter Tight, sans-serif",
    color: "#f1f5f9",
    size: 12,
  },
  colorway: [
    "#a855f7",
    "#6366f1",
    "#22d3ee",
    "#ec4899",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#38bdf8",
  ],
  xaxis: {
    gridcolor: "rgba(255,255,255,0.06)",
    linecolor: "rgba(255,255,255,0.12)",
    tickcolor: "rgba(255,255,255,0.12)",
    tickfont: { color: "#94a3b8" },
    title: { font: { color: "#94a3b8" } },
    zerolinecolor: "rgba(255,255,255,0.08)",
  },
  yaxis: {
    gridcolor: "rgba(255,255,255,0.06)",
    linecolor: "rgba(255,255,255,0.12)",
    tickcolor: "rgba(255,255,255,0.12)",
    tickfont: { color: "#94a3b8" },
    title: { font: { color: "#94a3b8" } },
    zerolinecolor: "rgba(255,255,255,0.08)",
  },
  legend: {
    bgcolor: "rgba(12,15,45,0.7)",
    bordercolor: "rgba(255,255,255,0.08)",
    borderwidth: 1,
    font: { color: "#f1f5f9" },
  },
  hoverlabel: {
    bgcolor: "#0c0f2d",
    bordercolor: "rgba(168,85,247,0.4)",
    font: { color: "#f1f5f9", family: "Inter Tight, sans-serif" },
  },
  margin: { t: 40, r: 20, b: 40, l: 50 },
};

export function mergeCosmicLayout(userLayout: Record<string, unknown> = {}) {
  return {
    ...COSMIC_PLOTLY_LAYOUT,
    ...userLayout,
    xaxis: { ...COSMIC_PLOTLY_LAYOUT.xaxis, ...(userLayout.xaxis as object | undefined) },
    yaxis: { ...COSMIC_PLOTLY_LAYOUT.yaxis, ...(userLayout.yaxis as object | undefined) },
    legend: { ...COSMIC_PLOTLY_LAYOUT.legend, ...(userLayout.legend as object | undefined) },
    hoverlabel: {
      ...COSMIC_PLOTLY_LAYOUT.hoverlabel,
      ...(userLayout.hoverlabel as object | undefined),
    },
    margin: { ...COSMIC_PLOTLY_LAYOUT.margin, ...(userLayout.margin as object | undefined) },
  };
}
