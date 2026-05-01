"""API & Web connector panel."""
from __future__ import annotations
import streamlit as st


PROVIDERS = [
    ("kaggle",      "Kaggle",        "\U0001f4c8"),
    ("huggingface", "HuggingFace",   "\U0001f917"),
    ("sheets",      "Google Sheets", "\U0001f4d1"),
    ("rest",        "REST API",      "\U0001f310"),
    ("worldbank",   "World Bank",    "\U0001f30e"),
    ("fred",        "FRED",          "\U0001f4b5"),
    ("yahoo",       "Yahoo Finance", "\U0001f4ca"),
    ("census",      "US Census",     "\U0001f1fa\U0001f1f8"),
]


def render(on_loaded) -> None:
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown('<div class="up-conn-card">', unsafe_allow_html=True)
        st.markdown(
            '<h3 class="up-conn-title">Fetch from an <em>API or web source</em></h3>'
            '<p class="up-conn-sub">Pull data from public APIs, open datasets, and web services.</p>',
            unsafe_allow_html=True,
        )

        provider = _render_provider_tiles("up_api_prov", PROVIDERS, default="kaggle")

        # Provider-specific fields
        if provider == "rest":
            st.text_input("Endpoint URL", placeholder="https://api.example.com/data",
                          key="up_api_url")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("Method", ["GET", "POST"], key="up_api_method")
            with c2:
                st.selectbox("Auth type", ["None", "Bearer token", "API key header"],
                             key="up_api_auth")
            st.text_input("Token / API key", type="password", key="up_api_token")
            st.text_input("Response root path (e.g. data.results)", key="up_api_root")

        elif provider == "kaggle":
            st.text_input("Dataset (owner/dataset-name)",
                          placeholder="uciml/iris",
                          key="up_api_kaggle_ds")
            st.text_input("Kaggle API token", type="password",
                          placeholder="Paste JSON token or leave blank to use ~/.kaggle/kaggle.json",
                          key="up_api_kaggle_tok")

        elif provider == "huggingface":
            st.text_input("Dataset repo", placeholder="datasets/owner/dataset-name",
                          key="up_api_hf_repo")
            st.text_input("Split", value="train", key="up_api_hf_split")

        elif provider == "sheets":
            st.text_input("Sheet URL or ID", placeholder="https://docs.google.com/spreadsheets/...",
                          key="up_api_sheet_url")
            st.text_input("Sheet tab name (optional)", key="up_api_sheet_tab")

        else:
            # Generic: just show info
            st.info(f"Configure and load {provider.replace('_',' ').title()} data sources "
                    "through the settings panel (coming soon).")

        b1, b2 = st.columns(2)
        with b1:
            test_clicked = st.button("Test / preview", key="up_api_test")
        with b2:
            st.button("Load data", type="primary", key="up_api_load", disabled=True)

        if test_clicked:
            st.info("API connector not yet configured in this environment. "
                    "Use Manual upload or a sample dataset instead.")

        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        st.markdown(
            '<div class="up-info-panel">'
            '  <h4>\U0001f4d6 Pagination</h4>'
            '  <p>AutoDS handles paginated responses automatically for supported APIs.</p>'
            '</div>'
            '<div class="up-info-panel">'
            '  <h4>\u23f1 Rate limits</h4>'
            '  <p>Large fetches are rate-limited to respect API quotas. Check the source documentation.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_provider_tiles(state_key: str, providers, default: str) -> str:
    selected = st.session_state.get(state_key, default)
    st.markdown('<div class="up-providers">', unsafe_allow_html=True)
    # 4 cols per row
    for i in range(0, len(providers), 4):
        row = providers[i:i + 4]
        cols = st.columns(4)
        for col, (key, label, icon) in zip(cols, row):
            with col:
                if st.button(f"{icon}\n{label}", key=f"{state_key}_{key}",
                             use_container_width=True):
                    st.session_state[state_key] = key
                    st.rerun()
                st.markdown(
                    f'<div data-up-prov="{key}" data-selected="{1 if key == selected else 0}"></div>',
                    unsafe_allow_html=True,
                )
    st.markdown('</div>', unsafe_allow_html=True)
    return selected
