"""Top insights summary card with LLM-generated takeaways."""
from __future__ import annotations
import streamlit as st


def render() -> None:
    insights = st.session_state.get("eda_insights", [])
    n_charts = len(st.session_state.get("eda_charts", []))

    if not insights:
        return

    insights_html = ""
    for i, ins in enumerate(insights, start=1):
        text = _html_escape(ins.get("text", ""))
        # Allow simple <strong> from agent-generated text — escape everything else
        text = text.replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")
        text = text.replace("&lt;code&gt;", '<code style="font-family:var(--font-mono);font-size:11px;color:var(--violet);">').replace("&lt;/code&gt;", "</code>")

        confidence = ins.get("confidence", "high")
        conf_class = "high" if confidence == "high" else "medium"
        meta = ins.get("evidence", "")  # e.g., "p<0.001, n=24,380"

        insights_html += (
            f'<div class="ed-insight-card">'
            f'  <div class="ed-insight-num">{i:02d}</div>'
            f'  <div class="ed-insight-body">'
            f'    <div class="ed-insight-text">{text}</div>'
            f'    <div class="ed-insight-meta">'
            f'      <span class="ed-insight-conf {conf_class}">{confidence.title()} confidence</span>'
            f'      {"<span style=\"color:var(--text-muted);\">·</span><span style=\"color:var(--text-muted);\">" + _html_escape(meta) + "</span>" if meta else ""}'
            f'      <span class="ed-insight-drill">Drill into this →</span>'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )

    st.markdown(
        f'<section class="ed-insights-summary">'
        f'  <h2>Key <em>insights</em></h2>'
        f'  <div class="ed-insights-meta">'
        f'    <span>{len(insights)} takeaways · LLM-summarized · {n_charts} charts run</span>'
        f'  </div>'
        f'  {insights_html}'
        f'</section>',
        unsafe_allow_html=True,
    )


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
