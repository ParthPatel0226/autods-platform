"""
─────────────────────────────────────────────────────────────────────
Example: Integrating the AutoDS theme into your Streamlit app
─────────────────────────────────────────────────────────────────────

Use this as a reference for how to apply the theme to your existing
AutoDS app. Don't replace your real app.py with this — just copy the
relevant lines.
"""

import streamlit as st
from theme import apply_theme, back_to_landing, section_label

# ─────────────────────────────────────────────────────────────────────
# 1. Page config — must be the FIRST Streamlit call
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AutoDS — Autonomous Data Science",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-username/autods",
        "Report a bug": "https://github.com/your-username/autods/issues",
        "About": "AutoDS — Autonomous Data Science Platform v1.0.0",
    },
)

# ─────────────────────────────────────────────────────────────────────
# 2. Apply the cosmic theme — must come right after set_page_config
# ─────────────────────────────────────────────────────────────────────
apply_theme()

# ─────────────────────────────────────────────────────────────────────
# 3. Check if user came from the landing page
# ─────────────────────────────────────────────────────────────────────
query_params = st.query_params
source = query_params.get("source", "direct")
default_mode = query_params.get("mode", "auto")

if source == "landing":
    st.toast("Welcome from the landing page! Let's get started.", icon="✦")

# ─────────────────────────────────────────────────────────────────────
# 4. Sidebar with back-link and your existing nav
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Replace with your actual landing page URL
    back_to_landing("https://autods.vercel.app")
    st.divider()

    # Status badge
    st.markdown(
        """
        <div style="display: inline-flex; align-items: center; gap: 8px;
                    padding: 4px 10px; border-radius: 999px;
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.14);
                    font-family: 'JetBrains Mono', monospace; font-size: 11px;
                    color: #C4C7E8; margin-bottom: 12px;">
            <span style="width: 6px; height: 6px; background: #10B981;
                         border-radius: 50%;"></span>
            v1.0.0 · 8 agents
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Your existing nav — use st.navigation (Streamlit 1.32+) or radio
    page = st.radio(
        "Workflow",
        [
            "🏠 Home",
            "📤 Upload",
            "⚙️ Configure",
            "📊 EDA",
            "✦ Features",
            "◆ Modeling",
            "◐ Explainability",
            "↗ Predict",
            "💬 Chat",
            "⬇ Download",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Branding footer
    st.caption("© 2026 AutoDS · Built by Parth")


# ─────────────────────────────────────────────────────────────────────
# 5. Main content area — use section_label for consistent headers
# ─────────────────────────────────────────────────────────────────────

if page == "🏠 Home":
    section_label("WELCOME")
    st.title("From raw data to *production models*.")
    st.markdown(
        "Drop a dataset on the next page to start your first analysis.",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Agents", "8", "Ready")
    with col2:
        st.metric("Domains", "7", "Auto-detect")
    with col3:
        st.metric("Connectors", "30+", "")
    with col4:
        st.metric("Output formats", "4", "")

elif page == "📤 Upload":
    section_label("DATA UPLOAD")
    st.title("Drop a file. Connect a source.")
    uploaded = st.file_uploader(
        "Drop your dataset here",
        type=["csv", "xlsx", "json", "parquet"],
    )
    if uploaded:
        st.success(f"Loaded {uploaded.name}")

elif page == "⚙️ Configure":
    section_label("CONFIGURATION")
    st.title("Three modes for three users.")
    mode = st.radio("Mode", ["Auto", "Guided", "Expert"], index=0)
    st.info(f"Selected mode: **{mode}**")

# ... add the rest of your existing pages

# ─────────────────────────────────────────────────────────────────────
# That's it! Your app now matches the landing page aesthetic.
# ─────────────────────────────────────────────────────────────────────
