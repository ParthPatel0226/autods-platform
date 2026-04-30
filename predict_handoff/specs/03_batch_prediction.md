# Spec 03 — Batch Prediction

## Backend reuse

- `serving/model_loader.py` — load trained model
- `serving/schemas.py` — `BatchPredictionRequest` / `BatchPredictionResponse` Pydantic models
- `validation/schema_validator.py` — `validate_prediction_input(df, training_schema)` checks columns match

## File: `dashboard/components/pr_batch_upload.py`

```python
"""Batch prediction — upload CSV/Excel, validate schema, run predictions."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render(training_columns: list[str], on_predict) -> None:
    """Render batch upload UI.

    Args:
        training_columns: expected feature columns from training
        on_predict(df) — called with validated DataFrame when user clicks Run
    """
    st.markdown(
        '<div class="pr-form-header">'
        '<h3 class="pr-form-title">Upload data for batch predictions</h3>'
        '<p class="pr-form-sub">Upload a CSV or Excel file with the same columns used for training.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Schema preview — show expected columns
    st.markdown(
        f'<div class="pr-schema-preview">'
        f'  <div class="pr-schema-title">Expected columns ({len(training_columns)})</div>'
        f'  <div class="pr-schema-cols">'
        + " ".join(f'<span class="pr-schema-col">{c}</span>' for c in training_columns[:20])
        + (f'<span class="pr-schema-col pr-schema-more">+{len(training_columns) - 20} more</span>' if len(training_columns) > 20 else "")
        + f'</div></div>',
        unsafe_allow_html=True,
    )

    # File upload
    uploaded = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
        key="pr_batch_file",
        label_visibility="collapsed",
    )

    if uploaded is None:
        return

    # Parse
    try:
        if uploaded.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Failed to parse file: {e}")
        return

    # Schema validation
    missing = [c for c in training_columns if c not in df.columns]
    extra = [c for c in df.columns if c not in training_columns]

    st.markdown(
        f'<div class="pr-validation-summary">'
        f'  <div class="pr-val-item"><span class="pr-val-label">Rows</span><span class="pr-val-value">{len(df):,}</span></div>'
        f'  <div class="pr-val-item"><span class="pr-val-label">Columns</span><span class="pr-val-value">{len(df.columns)}</span></div>'
        f'  <div class="pr-val-item"><span class="pr-val-label">Missing cols</span>'
        f'    <span class="pr-val-value" style="color:{"var(--red)" if missing else "var(--green)"};">'
        f'      {len(missing)}</span></div>'
        f'  <div class="pr-val-item"><span class="pr-val-label">Extra cols</span>'
        f'    <span class="pr-val-value" style="color:var(--text-muted);">{len(extra)}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if missing:
        st.error(f"Missing required columns: {', '.join(missing[:10])}")
        return

    # Preview
    st.dataframe(df.head(5), use_container_width=True)

    if st.button("🚀 Run batch predictions", key="pr_batch_run",
                 type="primary", use_container_width=True):
        on_predict(df[training_columns])
```

## File: `dashboard/components/pr_batch_results.py`

```python
"""Batch results — table + download + risk stratification chart."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from dashboard.components import project_service


def render(results_df: pd.DataFrame) -> None:
    """Render batch prediction results.

    Args:
        results_df: original df with added 'prediction' and optionally 'risk_level' columns
    """
    if results_df is None or results_df.empty:
        return

    project = project_service.get_active()
    problem_type = project.problem_type if project else "classification"
    n_rows = len(results_df)

    st.markdown(
        f'<div class="pr-batch-header">'
        f'  <h3>Batch results — {n_rows:,} predictions</h3>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Risk stratification (classification only)
    if problem_type == "classification" and "prediction" in results_df.columns:
        preds = results_df["prediction"]
        n_high = int((preds > 0.6).sum())
        n_med = int(((preds > 0.35) & (preds <= 0.6)).sum())
        n_low = int((preds <= 0.35).sum())

        st.markdown(
            f'<div class="pr-risk-strat">'
            f'  <div class="pr-risk-card pr-risk-high">'
            f'    <div class="pr-risk-count">{n_high}</div>'
            f'    <div class="pr-risk-label">High risk (&gt;60%)</div>'
            f'    <div class="pr-risk-pct">{n_high/n_rows*100:.1f}%</div></div>'
            f'  <div class="pr-risk-card pr-risk-med">'
            f'    <div class="pr-risk-count">{n_med}</div>'
            f'    <div class="pr-risk-label">Medium (35–60%)</div>'
            f'    <div class="pr-risk-pct">{n_med/n_rows*100:.1f}%</div></div>'
            f'  <div class="pr-risk-card pr-risk-low">'
            f'    <div class="pr-risk-count">{n_low}</div>'
            f'    <div class="pr-risk-label">Low risk (&lt;35%)</div>'
            f'    <div class="pr-risk-pct">{n_low/n_rows*100:.1f}%</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Results table
    st.dataframe(
        results_df.style.background_gradient(subset=["prediction"], cmap="RdYlGn_r")
        if "prediction" in results_df.columns else results_df,
        use_container_width=True,
        height=400,
    )

    # Download
    csv = results_df.to_csv(index=False)
    st.download_button(
        "⬇ Download predictions as CSV",
        data=csv,
        file_name="autods_predictions.csv",
        mime="text/csv",
        key="pr_batch_download",
        use_container_width=True,
    )
```

## CSS additions

```css
/* ============ Batch prediction ============ */
.pr-schema-preview { padding: 14px 18px; background: rgba(139,92,246,0.04);
  border: 1px solid var(--border-subtle); border-radius: 12px; margin-bottom: 18px; }
.pr-schema-title { font-family: var(--font-mono); font-size: 10px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.pr-schema-cols { display: flex; flex-wrap: wrap; gap: 6px; }
.pr-schema-col { font-family: var(--font-mono); font-size: 11px; padding: 3px 8px;
  background: rgba(139,92,246,0.08); border: 1px solid var(--border-subtle);
  border-radius: 6px; color: var(--violet); }
.pr-schema-more { color: var(--text-muted); background: transparent; border-style: dashed; }

.pr-validation-summary { display: flex; gap: 18px; padding: 14px 18px;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 12px; margin: 14px 0; }
.pr-val-item { display: flex; flex-direction: column; gap: 2px; }
.pr-val-label { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-faint);
  letter-spacing: 1px; text-transform: uppercase; }
.pr-val-value { font-family: var(--font-display); font-size: 22px; color: var(--text-primary); }

.pr-batch-header h3 { font-family: var(--font-display); font-size: 24px; margin-bottom: 18px; }

.pr-risk-strat { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 22px; }
@media (max-width: 700px) { .pr-risk-strat { grid-template-columns: 1fr; } }
.pr-risk-card { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 14px; padding: 18px; text-align: center; backdrop-filter: blur(14px); }
.pr-risk-count { font-family: var(--font-display); font-size: 36px; line-height: 1; margin-bottom: 4px; }
.pr-risk-label { font-size: 12px; color: var(--text-muted); margin-bottom: 2px; }
.pr-risk-pct { font-family: var(--font-mono); font-size: 11px; color: var(--text-faint); }
.pr-risk-high .pr-risk-count { color: var(--red); }
.pr-risk-high { border-color: rgba(248,113,113,0.3); }
.pr-risk-med .pr-risk-count { color: var(--amber); }
.pr-risk-med { border-color: rgba(251,191,36,0.3); }
.pr-risk-low .pr-risk-count { color: var(--green); }
.pr-risk-low { border-color: rgba(52,211,153,0.3); }
```
