# AutoDS Streamlit Theme

Drop-in theme module that makes any Streamlit app match the AutoDS landing page aesthetic — same fonts, colors, glass cards, gradient buttons, and aurora background.

## ⚡ Setup (3 steps)

### 1. Copy these files into your Streamlit project

```
your-streamlit-project/
├── .streamlit/
│   └── config.toml          ← copy from streamlit/.streamlit/
├── theme.py                 ← copy from streamlit/
├── app.py                   ← your existing app
└── ...
```

### 2. Apply the theme in `app.py`

At the very top, right after `st.set_page_config()`:

```python
import streamlit as st
from theme import apply_theme

st.set_page_config(
    page_title="AutoDS",
    page_icon="✦",
    layout="wide",
)

apply_theme()  # ← add this one line

# ... your existing code
```

### 3. Run as normal

```bash
streamlit run app.py
```

Your app now has the cosmic dark theme.

---

## 🎨 What it themes

| Element | Style |
|---|---|
| Background | Deep navy `#07091A` with violet/cyan/pink aurora gradients + subtle starfield |
| Sidebar | Glass surface, violet pill hover states, gradient on active item |
| Headings | Instrument Serif (italic) with gradient text on `<h1>` |
| Body | Inter Tight |
| Code | JetBrains Mono on dark glass |
| Primary buttons | Violet→purple gradient with glow |
| Secondary buttons | Glass pill with violet hover border |
| File uploader | Violet dashed border drop zone |
| Metrics | Glass cards with gradient values |
| Tabs | Pill-style with active gradient highlight |
| Expanders | Glass cards |
| Alerts | Color-coded glass panels |
| DataFrames | Glass border with violet headers |
| Sliders | Violet thumb with glow ring |
| Progress bars | Violet→cyan gradient |
| Plotly charts | Glass card wrapper |

## 🧩 Helpers

The module exports three functions:

### `apply_theme()`

Injects all the CSS. Call once after `st.set_page_config()`.

### `back_to_landing(landing_url: str = "/")`

Renders a styled "← Back to landing" pill link. Use in your sidebar:

```python
with st.sidebar:
    back_to_landing("https://my-landing.vercel.app")
```

### `section_label(text: str)`

Renders a small uppercase mono label like `✦ DATA UPLOAD` — the same style used as section headers on the landing page.

```python
from theme import section_label

section_label("MODEL TRAINING")
st.title("Pick an algorithm.")
```

## 🎨 Customization

The CSS variables are at the top of `apply_theme()` in `theme.py`. Edit them to retune the palette:

```python
:root {
  --bg: #07091A;
  --violet: #8B5CF6;
  --purple: #A855F7;
  ...
}
```

Keep these in sync with `landing/index.html` so the two surfaces stay matched.

## 🐛 Troubleshooting

**Background still white**
→ `apply_theme()` must come AFTER `st.set_page_config()`. Also check `.streamlit/config.toml` is in project root.

**Sidebar buttons look default**
→ Streamlit's sidebar DOM varies by version. Inspect element, find the actual selector, add a CSS rule to `theme.py`.

**Custom components (st_aggrid, plotly, etc.) don't match theme**
→ Some third-party components use isolated iframes. You may need to pass theme colors directly to those components.

**Fonts not loading on enterprise networks**
→ Default Streamlit Cloud allows Google Fonts. If your network blocks them, self-host the fonts and update the `<link>` URLs in `apply_theme()`.

---

Theme file is ~16KB, all CSS, no extra dependencies.
