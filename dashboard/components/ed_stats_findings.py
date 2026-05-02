"""Statistical findings table with color-coded p-values."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    stats = st.session_state.get("eda_stats", [])
    if not stats:
        return

    sig_threshold = st.session_state.get("ed_filter_significance", 0.05)
    # Show all if threshold is relaxed to 0.10; otherwise filter
    if sig_threshold >= 0.10:
        visible = stats
    else:
        visible = [s for s in stats if s.get("p_value", 1.0) <= sig_threshold]

    n_sig = sum(1 for s in stats if s.get("p_value", 1.0) < 0.05)

    rows_html = ""
    for s in visible:
        p = s.get("p_value", 1.0)
        if p < 0.001:
            pclass, ptext = "signif", "&lt; 0.001"
        elif p < 0.05:
            pclass, ptext = "signif", f"{p:.3f}"
        elif p < 0.10:
            pclass, ptext = "weak", f"{p:.3f}"
        else:
            pclass, ptext = "ns", f"{p:.3f}"

        rows_html += (
            f'<tr>'
            f'  <td>'
            f'    <div class="ed-test-name">{_html_escape(s.get("test", "—"))}</div>'
            f'    <div class="ed-test-cols">{_html_escape(s.get("columns", ""))}</div>'
            f'  </td>'
            f'  <td><span class="ed-pval {pclass}">{ptext}</span></td>'
            f'  <td class="ed-effect">{_html_escape(str(s.get("effect_size", "—")))}</td>'
            f'  <td class="ed-interp">{_html_escape(s.get("interpretation", ""))}</td>'
            f'</tr>'
        )

    if not rows_html:
        return

    st.markdown(
        f'<section>'
        f'  <div class="ed-sec">'
        f'    <h3>Statistical <em>findings</em></h3>'
        f'    <span class="ed-sec-meta">{len(stats)} tests · {n_sig} significant at p &lt; 0.05</span>'
        f'  </div>'
        f'  <div class="ed-stats-wrap">'
        f'    <table class="ed-stats">'
        f'      <thead><tr><th>Test</th><th>p-value</th><th>Effect size</th><th>Interpretation</th></tr></thead>'
        f'      <tbody>{rows_html}</tbody>'
        f'    </table>'
        f'  </div>'
        f'</section>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
