# AutoDS — Landing Page ↔ Streamlit Integration Guide

Wire your marketing landing page to your Streamlit app and make both look identical.

---

## 📦 What's in this bundle

```
autods-bundle/
├── CLAUDE.md                         # Brief for Claude Code
├── INTEGRATION_GUIDE.md              # This file
│
├── landing/                          # Marketing page
│   ├── index.html                    # The page (single file, CDN-loaded React)
│   ├── package.json                  # Optional vite dev setup
│   ├── vercel.json                   # Vercel deploy config
│   ├── netlify.toml                  # Netlify deploy config
│   └── README.md
│
└── streamlit/                        # Drop-ins for your existing app
    ├── theme.py                      # CSS theme module
    ├── .streamlit/
    │   └── config.toml               # Streamlit base theme
    └── README.md
```

---

## 🚀 Step 1 — Update the landing page URLs

Open `landing/index.html` and find the CONFIG block near the top of the `<script>` section:

```js
// =================== CONFIG ===================
const APP_URL = "http://localhost:8501";
const GITHUB_URL = "https://github.com/your-username/autods";
const DOCS_URL = "#docs";
```

Replace with your actual deployed URLs:

```js
const APP_URL = "https://autods-yourname.streamlit.app";
const GITHUB_URL = "https://github.com/parth/autods";
const DOCS_URL = "https://github.com/parth/autods#readme";
```

Now every "Launch App", "Launch Platform", and "View on GitHub" button routes correctly.

---

## 🎨 Step 2 — Apply matching theme to your Streamlit app

### A) Drop the config in

Copy `streamlit/.streamlit/config.toml` to your Streamlit project's `.streamlit/` folder.

If your project already has a `.streamlit/config.toml`, merge the `[theme]` section from the new file into the existing one:

```toml
[theme]
base = "dark"
primaryColor = "#A855F7"
backgroundColor = "#07091A"
secondaryBackgroundColor = "#11173D"
textColor = "#F4F5FF"
font = "sans-serif"
```

### B) Drop in `theme.py`

Copy `streamlit/theme.py` to your Streamlit project root (same folder as `app.py`).

### C) Apply it in your app

Open your main Streamlit file and add at the top, **right after** `st.set_page_config()`:

```python
import streamlit as st
from theme import apply_theme, back_to_landing, section_label

st.set_page_config(
    page_title="AutoDS — Autonomous Data Science",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply the AutoDS cosmic theme
apply_theme()

# Optional: add a "back to landing" link in the sidebar
with st.sidebar:
    back_to_landing("https://your-landing.vercel.app")
    st.divider()
    # ... rest of your sidebar
```

That's it. Your Streamlit app now uses the same fonts, colors, glass cards, gradient buttons, and aurora background as the landing page.

---

## 🧩 Step 3 — Pass context from landing to app (optional)

If you want the landing page to pre-select a mode in the app (e.g., "auto" vs "guided"), use URL query parameters.

### In `landing/index.html`:

```js
const APP_URL = "https://your-app.streamlit.app";
const launchUrl = (mode = 'auto') => `${APP_URL}?source=landing&mode=${mode}`;
```

Then update button hrefs:

```jsx
<motion.a href={launchUrl('auto')} ...>Launch the Platform</motion.a>
```

### In your Streamlit `app.py`:

```python
query_params = st.query_params
source = query_params.get("source", "direct")
default_mode = query_params.get("mode", "auto")

if source == "landing":
    st.toast("Welcome from the landing page! Let's get started.", icon="✦")
```

---

## 🌐 Step 4 — Deployment (all free tiers)

### Landing page

#### Option A: Vercel (recommended, fastest CDN)

```bash
cd landing/
npx vercel --prod
```

Drop `index.html` in a folder, run the command, follow the prompts. Custom domain free.

#### Option B: Netlify Drop

Drag-and-drop the `landing/` folder at https://netlify.com/drop. Instant URL.

#### Option C: GitHub Pages

Push `landing/index.html` to a repo as `index.html` in the root, then:
**Settings → Pages → Source: main branch → /(root)**

### Streamlit app

#### Streamlit Community Cloud (free)

1. Push your project to GitHub (with `.streamlit/config.toml`, `theme.py`, `requirements.txt`, `app.py`)
2. Go to https://share.streamlit.io → **New app** → connect repo
3. App deploys to `https://your-app.streamlit.app`
4. Update `APP_URL` in `landing/index.html` to that URL
5. Redeploy landing page

#### Hugging Face Spaces (also free, more memory)

Better if you're hitting Streamlit Cloud's resource limits with LangGraph + ML models running together.

```bash
huggingface-cli repo create autods --type space --space_sdk streamlit
```

Then push your code.

---

## 🎯 Optional polish

### Add a status badge in the Streamlit sidebar

```python
st.sidebar.markdown(
    """
    <div style="display: inline-flex; align-items: center; gap: 8px;
                padding: 4px 10px; border-radius: 999px;
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.14);
                font-family: 'JetBrains Mono', monospace; font-size: 11px;
                color: #C4C7E8;">
        <span style="width: 6px; height: 6px; background: #10B981; border-radius: 50%;"></span>
        v1.0.0 · 8 agents
    </div>
    """,
    unsafe_allow_html=True,
)
```

### Use the `section_label` helper for consistent headings

```python
from theme import section_label

section_label("DATA UPLOAD")
st.title("Drop a file. Connect a source.")
```

This renders the same `✦ DATA UPLOAD` mini-label from the landing page.

---

## ✅ Final checklist

- [ ] Updated `APP_URL` and `GITHUB_URL` in `landing/index.html`
- [ ] Copied `theme.py` to your Streamlit project root
- [ ] Copied `.streamlit/config.toml` to your Streamlit project's `.streamlit/`
- [ ] Called `apply_theme()` after `st.set_page_config()` in `app.py`
- [ ] Deployed Streamlit app, copied URL into `landing/index.html`
- [ ] Deployed landing page (Vercel/Netlify)
- [ ] Tested: open landing → click "Launch App" → themed Streamlit loads in new tab

---

## 🐛 Troubleshooting

**Streamlit app still has white background**
→ `apply_theme()` must be called after `st.set_page_config()`. `.streamlit/config.toml` must be in the project root, not nested.

**Fonts not loading**
→ Default Streamlit Cloud allows Google Fonts. If self-hosting with strict CSP, allow `fonts.googleapis.com` and `fonts.gstatic.com`.

**Sidebar buttons look default**
→ Streamlit's sidebar DOM changed across versions. Inspect element, find the actual selector, and add a CSS rule to `theme.py`.

**Landing page is blank**
→ Open browser DevTools → Console. Babel may have a syntax error from a manual edit. The script tag is `text/babel` (transpiled in-browser).

**Theme toggle doesn't appear**
→ Look at top-right of nav bar (between page links and "Launch App") AND bottom-right floating button. Both exist for redundancy.

**Architecture diagram not animating**
→ Make sure Framer Motion CDN script loaded. Check Network tab for `framer-motion@10.18.0`.
