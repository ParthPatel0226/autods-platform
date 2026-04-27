# AutoDS Landing Page + Streamlit Theme — Claude Code Brief

## What this is

You're integrating a marketing landing page with an existing Streamlit app called **AutoDS** (an autonomous data science platform with 8 LangGraph agents). The landing page sits at the project's marketing surface; the Streamlit app is the product. Both must look and feel like one cohesive brand.

## Project structure

```
autods-bundle/
├── landing/                          # Marketing page (deploys separately)
│   ├── index.html                    # Single-file landing page (React + Framer Motion via CDN)
│   ├── package.json                  # Optional — for local dev with vite
│   ├── vercel.json                   # Vercel deployment config
│   ├── netlify.toml                  # Netlify deployment config
│   └── README.md
├── streamlit/                        # Files to drop into your existing AutoDS Streamlit project
│   ├── .streamlit/
│   │   └── config.toml               # Base Streamlit theme (cosmic dark)
│   ├── theme.py                      # CSS injection module — call apply_theme() in your app.py
│   └── README.md
├── INTEGRATION_GUIDE.md              # End-to-end integration walkthrough
└── CLAUDE.md                         # This file
```

## The aesthetic (must stay consistent)

- **Background:** deep cosmic navy `#07091A` with violet/cyan/pink aurora gradient overlays
- **Primary accent:** violet `#A855F7` and indigo `#6366F1`
- **Secondary accents:** cyan `#22D3EE`, pink `#EC4899`, green `#10B981`, amber `#F59E0B`
- **Typography:**
  - **Inter Tight** for body / UI
  - **Instrument Serif** (italic) for hero headlines and accent words
  - **JetBrains Mono** for terminal output, badges, technical labels
- **Surfaces:** glass-morphism (translucent white with backdrop blur)
- **Motion:** Framer Motion springs and continuous loops (especially the orchestrator pulse, particle flow, and shimmer sweeps)

## Tasks to complete

### 1. Update URLs in the landing page

Open `landing/index.html`, find the CONFIG block near the top of the `<script>` section (around line 280):

```js
const APP_URL = "http://localhost:8501";
const GITHUB_URL = "https://github.com/your-username/autods";
```

Replace with the user's real URLs.

### 2. Wire the Streamlit theme into the existing app

Drop these files into the user's existing AutoDS Streamlit project root:

- `theme.py` → project root
- `.streamlit/config.toml` → if a `.streamlit/` folder doesn't exist, create it; if a `config.toml` already exists, merge the `[theme]` section from the new one into it

Then in the user's main Streamlit entry file (likely `app.py` or `main.py`), add right after `st.set_page_config(...)`:

```python
from theme import apply_theme, back_to_landing, section_label

apply_theme()  # call once, immediately after set_page_config

# Optional: in the sidebar, add a "back to landing" link
with st.sidebar:
    back_to_landing("https://landing-url.vercel.app")
```

### 3. Sidebar tab matching

The user's app already has these sidebar tabs (visible in their screenshot):
`app · upload · configure · eda interactive · feature engineering · modeling · explainability · predict · chat · download`

These ARE the same tabs as the landing page's "Platform" section. The naming should stay in sync. If you rename a tab in the Streamlit app, also update the corresponding label in `landing/index.html` inside the `PlatformTabs` component's `tabs` array.

### 4. Deploy

**Landing page** → Vercel (recommended) or Netlify or GitHub Pages. Single static file, no build step required (CDN-loaded React).

**Streamlit app** → Streamlit Community Cloud or Hugging Face Spaces. Make sure `requirements.txt` includes everything the app needs and `theme.py` is committed alongside `app.py`.

## Important constraints

- **Do NOT change the typography** unless the user explicitly asks. The Inter Tight + Instrument Serif + JetBrains Mono trio is core to the brand identity.
- **Do NOT change the color palette** without checking the integration guide. The CSS variables in both files (`landing/index.html` and `streamlit/theme.py`) must stay synchronized so the two surfaces match.
- **Do NOT remove the Framer Motion animations** in the landing page. The orchestrator pulse, particle flow visualization, and shimmer sweeps are deliberate — they signal "live system" to recruiters and visitors.
- **The two theme toggles** (top-right of nav AND bottom-right floating button) are intentionally redundant. Keep both.

## Files the user needs to provide before deploying

- [ ] Streamlit app URL (for the landing page's `APP_URL`)
- [ ] GitHub repo URL (for the `GITHUB_URL`)
- [ ] LinkedIn / Portfolio / Email links (for footer — currently `href="#"` placeholders)
- [ ] Any custom logo asset (the current logo is an inline SVG — fine as-is, but a custom asset can replace it)

## Verification checklist

After deploy:

- [ ] Landing page loads at chosen URL (Vercel/Netlify)
- [ ] Both theme toggles (nav + floating) switch the page between dark/light
- [ ] All "Launch App" buttons open the Streamlit app in a new tab
- [ ] Streamlit app uses the cosmic dark theme (no white backgrounds visible)
- [ ] Streamlit sidebar tabs use the violet pill hover state
- [ ] Headers in Streamlit render in Instrument Serif
- [ ] Body text in Streamlit renders in Inter Tight
- [ ] Code blocks in Streamlit render in JetBrains Mono

## If something breaks

- **Landing page shows blank:** check browser console — Babel may have a syntax error from a manual edit. The script is `text/babel` and gets transpiled in-browser.
- **Streamlit theme not applying:** confirm `apply_theme()` is called AFTER `st.set_page_config()`, and `theme.py` imports correctly.
- **Sidebar buttons look wrong:** Streamlit's sidebar nav DOM structure varies by version. Inspect element and add the right selector to `theme.py` if needed.
- **Fonts not loading:** check `Content-Security-Policy` — Google Fonts must be allowed.

---

**Read `INTEGRATION_GUIDE.md` for the full step-by-step walkthrough including deployment commands.**
