# Spec 03 — Feature Interaction Network (THE CRAZY ONE)

## Goal

Render a **force-directed network graph** where nodes = features (sized by SHAP importance), edges = pairwise interaction strength (thickness + glow intensity). This is the FAANG portfolio showpiece — no standard AutoML tool has this.

## Backend

`explainability/shap_explainer.py` may expose `compute_shap_interaction_values(model, X)` which returns an (n_samples × n_features × n_features) tensor. If this function doesn't exist or is too slow, fall back to computing pairwise feature correlations from the SHAP values matrix as a proxy.

## File: `dashboard/components/ex_interaction_network.py`

```python
"""Force-directed feature interaction network rendered as SVG via st.markdown."""
from __future__ import annotations
import math
import streamlit as st
import numpy as np


def render(interaction_data: dict) -> None:
    """Render the interaction network SVG.

    Args:
        interaction_data: dict with:
            nodes: list[{"name": str, "importance": float}]  — sorted desc
            edges: list[{"source": int, "target": int, "strength": float}]
            — indices into nodes list, strength 0..1
    """
    if not interaction_data or not interaction_data.get("nodes"):
        st.info("Interaction values not computed. Requires tree-based model with SHAP interaction support.")
        return

    nodes = interaction_data["nodes"][:8]  # limit to top 8 for clarity
    edges = interaction_data.get("edges", [])
    max_importance = max(n["importance"] for n in nodes) if nodes else 1.0

    st.markdown(
        '<div class="ex-sec-header">'
        '<h3>Feature <em>interaction network</em></h3>'
        '<span class="ex-sec-meta">SHAP interaction values · pairwise</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Compute positions in a circle layout
    n = len(nodes)
    cx, cy = 400, 200
    radius = 160
    positions = []
    for i in range(n):
        angle = (2 * math.pi * i / n) - math.pi / 2
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        positions.append((x, y))

    # Build SVG
    width, height = 800, 420

    # Edges
    edges_svg = ""
    for edge in edges:
        s, t = edge["source"], edge["target"]
        if s >= n or t >= n:
            continue
        strength = min(edge["strength"], 1.0)
        w = max(1, int(strength * 5))
        opacity = max(0.15, strength * 0.8)
        grad = "url(#exEdgeGrad1)" if strength > 0.5 else "url(#exEdgeGrad2)" if strength > 0.2 else "rgba(139,92,246,0.15)"
        x1, y1 = positions[s]
        x2, y2 = positions[t]
        edges_svg += f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{grad}" stroke-width="{w}" opacity="{opacity:.2f}"/>'

    # Nodes
    nodes_svg = ""
    for i, node in enumerate(nodes):
        x, y = positions[i]
        size = max(28, int(node["importance"] / max_importance * 60))
        r = size // 2
        # Color gradient based on rank
        colors = [
            ("#6366F1", "#A855F7"), ("#6366F1", "#8B5CF6"), ("#8B5CF6", "#A855F7"),
            ("#A855F7", "#EC4899"), ("#EC4899", "#A855F7"), ("#22D3EE", "#6366F1"),
            ("#34D399", "#22D3EE"), ("#FBBF24", "#EC4899"),
        ]
        c1, c2 = colors[i % len(colors)]
        glow_intensity = max(0.2, node["importance"] / max_importance * 0.6)
        val_text = f'{node["importance"]:.3f}'
        name_short = node["name"][:10] + ("…" if len(node["name"]) > 10 else "")

        nodes_svg += (
            f'<g transform="translate({x:.0f},{y:.0f})">'
            f'  <circle r="{r}" fill="url(#exNodeGrad{i})" '
            f'    style="filter: drop-shadow(0 0 {int(glow_intensity * 20)}px {c1});">'
            f'    <animate attributeName="cy" values="0;-3;0" dur="{3 + i * 0.4}s" repeatCount="indefinite"/>'
            f'  </circle>'
            f'  <text y="4" text-anchor="middle" fill="white" '
            f'    font-family="JetBrains Mono" font-size="{max(8, 11 - i)}" font-weight="600">'
            f'    {val_text}</text>'
            f'  <text y="{r + 14}" text-anchor="middle" fill="var(--text-secondary)" '
            f'    font-family="JetBrains Mono" font-size="10">'
            f'    {_html_escape(name_short)}</text>'
            f'</g>'
        )
        # Node gradient def
        nodes_svg = (
            f'<defs><linearGradient id="exNodeGrad{i}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
            f'</linearGradient></defs>' + nodes_svg
        )

    svg = (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;height:{height}px;">'
        f'<defs>'
        f'<linearGradient id="exEdgeGrad1" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="#6366F1"/><stop offset="100%" stop-color="#A855F7"/></linearGradient>'
        f'<linearGradient id="exEdgeGrad2" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="#A855F7"/><stop offset="100%" stop-color="#EC4899"/></linearGradient>'
        f'</defs>'
        f'{edges_svg}'
        f'{nodes_svg}'
        f'</svg>'
    )

    st.markdown(
        f'<div class="ex-interaction-network">'
        f'  <div style="font-size:13px;color:var(--text-muted);margin-bottom:14px;">'
        f'    Features connected by interaction strength. Thicker, brighter lines = stronger synergistic effect.</div>'
        f'  {svg}'
        f'  <div class="ex-network-legend">'
        f'    <span><span class="ex-legend-dot" style="background:var(--indigo);box-shadow:0 0 6px var(--indigo);"></span>Strong interaction (SHAP > 0.02)</span>'
        f'    <span><span class="ex-legend-dot" style="background:var(--purple);box-shadow:0 0 4px var(--purple);"></span>Medium (0.01–0.02)</span>'
        f'    <span><span class="ex-legend-dot" style="background:rgba(139,92,246,0.3);"></span>Weak (&lt; 0.01)</span>'
        f'    <span style="margin-left:auto;">Node size = SHAP importance</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def compute_interactions_from_shap(shap_values_matrix, feature_names: list[str], top_n: int = 8) -> dict:
    """Compute pairwise interactions from SHAP value correlations as a proxy.

    If the backend provides true SHAP interaction values, use those instead.
    This function exists as a fallback.
    """
    n_features = min(top_n, len(feature_names))

    # Mean |SHAP| per feature
    mean_abs = np.mean(np.abs(shap_values_matrix), axis=0)
    top_indices = np.argsort(mean_abs)[::-1][:n_features]

    nodes = [
        {"name": feature_names[i], "importance": float(mean_abs[i])}
        for i in top_indices
    ]

    # Pairwise: correlation of SHAP value columns
    sub_shap = shap_values_matrix[:, top_indices]
    corr = np.abs(np.corrcoef(sub_shap.T))
    np.fill_diagonal(corr, 0)

    edges = []
    for i in range(n_features):
        for j in range(i + 1, n_features):
            strength = float(corr[i, j])
            if strength > 0.05:
                edges.append({"source": i, "target": j, "strength": strength})

    edges.sort(key=lambda e: e["strength"], reverse=True)
    return {"nodes": nodes, "edges": edges[:20]}  # limit edges for clarity


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* ============ Interaction network ============ */
.ex-interaction-network {
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 18px; padding: 24px;
  backdrop-filter: blur(14px); margin-bottom: 28px;
  position: relative; overflow: hidden;
}
.ex-network-legend {
  display: flex; gap: 18px; margin-top: 14px; padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-muted);
  flex-wrap: wrap;
}
.ex-legend-dot {
  width: 10px; height: 10px; border-radius: 50%;
  display: inline-block; margin-right: 6px; vertical-align: middle;
}
```

## Implementation notes

- The SVG is rendered via `st.markdown(unsafe_allow_html=True)` — no external charting library needed. The positions use a simple circle layout. For a truly force-directed layout, you'd need a physics simulation (D3-style), but the circle layout is sufficient for a Streamlit context and looks clean.
- The `compute_interactions_from_shap` fallback uses correlation of SHAP value columns as a proxy for interaction strength. If the actual `shap_explainer.py` exposes `compute_shap_interaction_values()`, prefer that.
- Limit to top 8 nodes for visual clarity. More than 8 makes the graph cluttered.
- The floating animation on nodes (`animate attributeName="cy"`) is subtle — just 3px oscillation at different speeds per node, creating an organic "breathing" effect.
