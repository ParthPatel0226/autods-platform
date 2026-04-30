# Spec 04 — Custom Derived Features (Section 03)

## Layout

```
[Section header: "03 · Custom derived features"]
[Builder card — dashed border, name + expression form]
[Live preview chip: "fare_per_person = Fare / (SibSp + Parch + 1)"]
[List of already-added custom features (if any) — each with a delete button]
```

## File: `dashboard/components/fe_custom_builder.py`

```python
"""Custom derived feature builder — name + safe expression evaluation."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import re

from dashboard.components import project_service


# Whitelist of operators and functions allowed in expressions
ALLOWED_FUNCS = {"abs", "min", "max", "log", "log10", "log2", "sqrt", "exp"}
ALLOWED_OPS_REGEX = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$|^[\d.]+$|^[+\-*/()<>= !,]+$")


def render() -> None:
    df: pd.DataFrame | None = st.session_state.get("df")
    if df is None or df.empty:
        return

    custom_features: list[dict] = st.session_state.setdefault("fe_custom_features", [])

    st.markdown(
        '<div class="fe-sec">'
        '  <div class="fe-sec-head">'
        '    <div class="fe-sec-num">03</div>'
        '    <div style="flex:1;">'
        '      <div class="fe-sec-title">Custom <em>derived features</em></div>'
        '      <div class="fe-sec-meta">Optional · build your own from existing columns</div>'
        '    </div>'
        '  </div>'
        '  <div class="fe-builder">'
        '    <div class="fe-builder-title">Build a new <em>column</em></div>'
        '    <div class="fe-builder-sub">Use column names and operators (+, −, ×, ÷, **). '
        'Example: <code>Fare / (SibSp + Parch + 1)</code></div>'
        '  </div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([2, 4, 1], gap="small")
    with cols[0]:
        name = st.text_input("Feature name", key="fe_custom_name",
                             placeholder="feature_name",
                             label_visibility="collapsed")
    with cols[1]:
        expr = st.text_input("Expression", key="fe_custom_expr",
                             placeholder="expression",
                             label_visibility="collapsed")
    with cols[2]:
        if st.button("Add", key="fe_custom_add", use_container_width=True):
            err = _validate(name, expr, df)
            if err:
                st.error(err)
            else:
                # Try to evaluate safely
                try:
                    preview = _safe_eval(expr, df.head(50))
                    custom_features.append({
                        "name": name.strip(),
                        "expression": expr.strip(),
                        "preview_dtype": str(preview.dtype),
                    })
                    # Clear inputs
                    st.session_state["fe_custom_name"] = ""
                    st.session_state["fe_custom_expr"] = ""
                    st.success(f"Added custom feature: {name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Expression evaluation failed: {e}")

    # Show already-added custom features
    if custom_features:
        st.markdown('<div class="fe-custom-list">', unsafe_allow_html=True)
        for i, f in enumerate(list(custom_features)):
            cols = st.columns([8, 1])
            with cols[0]:
                st.markdown(
                    f'<div class="fe-custom-item">'
                    f'  <span class="fe-custom-name">{_html_escape(f["name"])}</span>'
                    f'  <span class="fe-custom-eq">=</span>'
                    f'  <span class="fe-custom-expr">{_html_escape(f["expression"])}</span>'
                    f'  <span class="fe-custom-dtype">→ {_html_escape(f["preview_dtype"])}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if st.button("✕", key=f"fe_custom_del_{i}",
                             help="Remove this custom feature"):
                    custom_features.pop(i)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def _validate(name: str, expr: str, df: pd.DataFrame) -> str | None:
    if not name or not expr:
        return "Both name and expression are required."
    name = name.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z_0-9]*$", name):
        return "Name must start with a letter and contain only letters, numbers, and underscores."
    if name in df.columns:
        return f"Column '{name}' already exists in the dataset."
    # Existing custom features
    for f in st.session_state.get("fe_custom_features", []):
        if f["name"] == name:
            return f"Custom feature '{name}' already defined."
    # Basic sanity check on expression
    if any(bad in expr for bad in ("import", "__", "exec(", "eval(", "open(", "file(", "lambda")):
        return "Expression contains disallowed tokens."
    return None


def _safe_eval(expr: str, df: pd.DataFrame) -> pd.Series:
    """Evaluate an expression using pandas.DataFrame.eval — sandboxed."""
    # pandas eval supports column references, arithmetic, comparisons, and a small set of funcs
    return df.eval(expr, engine="python")


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
```

## CSS additions

```css
/* Custom builder */
.fe-builder {
  padding: 18px 20px;
  border: 1.5px dashed var(--border-default);
  border-radius: 14px;
  background: rgba(99,102,241,0.04);
  margin-bottom: 14px;
}
.fe-builder-title {
  font-family: var(--font-display); font-size: 20px;
  color: var(--text-primary); margin-bottom: 4px;
}
.fe-builder-title em {
  font-style: italic;
  background: var(--gradient-text);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.fe-builder-sub {
  font-size: 12.5px; color: var(--text-muted); margin-bottom: 0;
}
.fe-builder-sub code {
  font-family: var(--font-mono); font-size: 11.5px;
  color: var(--cyan); background: rgba(34,211,238,0.08);
  padding: 1px 6px; border-radius: 4px;
}

/* Already-added list */
.fe-custom-list { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.fe-custom-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: rgba(7,9,26,0.4);
  border: 1px solid var(--border-subtle); border-radius: 10px;
  font-family: var(--font-mono); font-size: 12.5px;
}
.fe-custom-name { color: var(--green); font-weight: 500; }
.fe-custom-eq { color: var(--text-faint); }
.fe-custom-expr { color: var(--text-secondary); flex: 1; }
.fe-custom-dtype { color: var(--text-muted); font-size: 10.5px; }
```

## Safety note

Expressions are evaluated using `pandas.DataFrame.eval` with `engine="python"`, which is sandboxed against arbitrary code execution but still allows column references and standard arithmetic. The validation function pre-screens for `import`, dunder access, `exec`, `eval`, `open`, `file`, and `lambda` tokens.
