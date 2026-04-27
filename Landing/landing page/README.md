# AutoDS Landing Page

Marketing surface for the AutoDS autonomous data science platform. Single-file static site that loads React, Framer Motion, and Tailwind via CDN — zero build step required.

## ⚡ Quick start

### Local preview

```bash
npx serve . -p 3000
# or
python3 -m http.server 3000
```

Open http://localhost:3000

### Edit the config

Open `index.html` and find the CONFIG block near the top of the `<script>` section:

```js
const APP_URL = "http://localhost:8501";          // your Streamlit app URL
const GITHUB_URL = "https://github.com/...";      // your GitHub repo
const DOCS_URL = "#docs";
```

## 🚀 Deploy

### Vercel (recommended)

```bash
npx vercel --prod
```

`vercel.json` is pre-configured — just answer the prompts.

### Netlify

```bash
npx netlify deploy --prod --dir=.
```

Or drag-and-drop this folder at https://netlify.com/drop.

`netlify.toml` is pre-configured.

### GitHub Pages

1. Push this folder's contents to a GitHub repo
2. Settings → Pages → Source: `main` branch → `/(root)`
3. URL: `https://<username>.github.io/<repo>/`

## 🎨 What's inside

- **Cosmic dark/light themes** with toggle (top-right nav + bottom-right floating button)
- **Animated hero** with data flow visualization (4 nodes connected by flowing particle paths)
- **9-tab Platform section** matching the Streamlit app's sidebar (upload, configure, eda, features, modeling, explainability, predict, chat, download)
- **Live LangGraph orchestrator** — pulsing block with shimmer sweeps and emanating rings
- **8 agent cards** with hover glow
- **Architecture diagram** with continuous animations (sequential agent activation, particle flow, state bar shimmer)
- **6 domain cards** (Healthcare, Finance, E-Commerce, HR, Manufacturing, Marketing)
- **Live terminal demo** with line-by-line streaming
- **Tech stack** (LangGraph, Polars, DuckDB, XGBoost, SHAP, etc.)
- **FAANG metrics framework**
- **CTA + footer** with all key links

## 🛠️ Tech

- React 18 (CDN)
- Framer Motion 10 (CDN)
- Tailwind CSS (CDN, Play mode)
- Babel Standalone (in-browser JSX transpiling)
- Google Fonts: Inter Tight, Instrument Serif, JetBrains Mono

## 📐 Customization

### Colors

Edit the CSS variables in the `<style>` block at the top of `index.html`:

```css
:root, [data-theme="dark"] {
  --bg: #07091A;
  --indigo: #6366F1;
  --violet: #8B5CF6;
  --purple: #A855F7;
  --pink: #EC4899;
  --cyan: #22D3EE;
  --green: #10B981;
}
```

The light theme variables are in `[data-theme="light"]` immediately after.

### Content

Each section is a function in the script. Search for these and edit the data arrays:

- `Hero()` — headline, subhead, stats
- `PlatformTabs()` — `tabs` array (mirrors your Streamlit sidebar)
- `Agents()` — `agents` array (8 agents)
- `Domains()` — `domains` array (6 industries)
- `Stack()` — `stacks` array (tech stack)
- `Metrics()` — `cats` array (FAANG metrics)
- `Footer()` — links

## 📄 License

MIT
