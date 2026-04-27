# Claude Code — Quick Reference

Fastest path through this bundle.

## File hierarchy (read in order)

1. `CLAUDE.md` — Brief and constraints
2. `INTEGRATION_GUIDE.md` — Full integration walkthrough
3. `landing/index.html` — The landing page
4. `streamlit/theme.py` — Theme module to apply

## Tasks Claude Code should do

### A) Update landing page URLs

```bash
# Edit landing/index.html
# Find lines starting with `const APP_URL` and `const GITHUB_URL`
# Replace with the user's actual URLs
```

### B) Integrate Streamlit theme

```bash
# Find the user's existing Streamlit project
# Typically: app.py, main.py, or streamlit_app.py

# Copy theme files
cp streamlit/theme.py <STREAMLIT_PROJECT>/
mkdir -p <STREAMLIT_PROJECT>/.streamlit
cp streamlit/.streamlit/config.toml <STREAMLIT_PROJECT>/.streamlit/

# Edit the user's main app file
# Add at top, after st.set_page_config():
#   from theme import apply_theme
#   apply_theme()
```

### C) Deploy landing page

```bash
cd landing/
npx vercel --prod
# Or: npx netlify deploy --prod
```

### D) Sync URL between landing and Streamlit

```bash
# After Streamlit deploy, copy the URL
# Edit landing/index.html APP_URL constant
# Redeploy landing
```

## Common commands

```bash
# Test landing locally
cd landing/ && npx serve . -p 3000

# Test Streamlit locally
cd <STREAMLIT_PROJECT>/ && streamlit run app.py

# Search/replace URL across files
grep -r "localhost:8501" .
```

## Constraints

- **Don't change typography** (Inter Tight + Instrument Serif + JetBrains Mono)
- **Don't change palette** (violet/cyan/pink on cosmic navy)
- **Don't remove animations** (orchestrator pulse, particle flow, shimmer)
- **Keep both theme toggles** (nav + floating)
- **Keep tab names in sync** between landing PlatformTabs and Streamlit sidebar

## When something breaks

| Issue | Fix |
|---|---|
| Landing blank | Check browser console — Babel syntax error |
| Streamlit white BG | `apply_theme()` must follow `set_page_config()` |
| Theme toggle missing | Look top-right nav AND bottom-right corner |
| Sidebar buttons default | Add CSS selector to `theme.py` for current Streamlit version |
| Animations frozen | Check Framer Motion CDN script loaded |
