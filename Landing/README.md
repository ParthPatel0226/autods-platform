# AutoDS — Landing Page + Streamlit Theme Bundle

Complete bundle to ship a marketing landing page that hands off seamlessly to your existing AutoDS Streamlit app — both surfaces share one cohesive cosmic aesthetic.

## 📁 What's here

```
autods-bundle/
├── CLAUDE.md                        # Brief for Claude Code (read first)
├── INTEGRATION_GUIDE.md             # Full step-by-step guide
├── README.md                        # This file
│
├── landing/                         # → Deploy to Vercel/Netlify
│   ├── index.html                   # The landing page (single file)
│   ├── package.json                 # Optional dev server
│   ├── vercel.json                  # Vercel config
│   ├── netlify.toml                 # Netlify config
│   └── README.md
│
└── streamlit/                       # → Drop into existing Streamlit project
    ├── theme.py                     # CSS theme module
    ├── .streamlit/
    │   └── config.toml              # Base Streamlit theme
    └── README.md
```

## 🚀 60-second quick start

```bash
# 1. Update URLs in landing/index.html
#    Find: const APP_URL = "http://localhost:8501";
#    Replace with your deployed Streamlit URL

# 2. Copy files into your Streamlit project
cp streamlit/theme.py /path/to/your/streamlit-app/
cp streamlit/.streamlit/config.toml /path/to/your/streamlit-app/.streamlit/

# 3. Add ONE line to your Streamlit app.py (after st.set_page_config)
#    from theme import apply_theme
#    apply_theme()

# 4. Deploy landing page
cd landing && npx vercel --prod

# 5. Test the flow
#    Open landing → click "Launch App" → themed Streamlit loads
```

## 📚 Documentation

- **`CLAUDE.md`** — Brief specifically for Claude Code agents working on this project
- **`INTEGRATION_GUIDE.md`** — Full walkthrough with deployment options and troubleshooting
- **`landing/README.md`** — Landing page details, customization, deployment
- **`streamlit/README.md`** — Theme module details and helper functions

## 🎨 Design system

| Token | Value |
|---|---|
| Primary BG | `#07091A` (cosmic navy) |
| Primary accent | `#A855F7` (violet) |
| Secondary accent | `#22D3EE` (cyan) |
| Tertiary accent | `#EC4899` (pink) |
| Font: display | Instrument Serif (italic) |
| Font: body | Inter Tight |
| Font: mono | JetBrains Mono |

## ✨ Highlights

- Animated multi-agent orchestration visualization (matches LangGraph architecture)
- Light/dark theme toggle (top-right + floating)
- 9 interactive platform tabs (mirrors Streamlit sidebar)
- 8 agent cards with hover states
- Live terminal demo with streaming output
- Architecture diagram with continuous animations
- All CTAs wired to the Streamlit app

## 🔗 Links to fill in

Before deploying, search for these placeholders and replace:

- `APP_URL` → your deployed Streamlit URL
- `GITHUB_URL` → your GitHub repo
- Footer links: GitHub, LinkedIn, Portfolio, Email

## 📄 License

MIT — built by Parth.
