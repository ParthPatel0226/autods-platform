"""Database connector panel — Postgres, MySQL, DuckDB, etc."""
from __future__ import annotations
import streamlit as st


PROVIDERS = [
    ("postgres",  "PostgreSQL",   "\U0001f418"),
    ("mysql",     "MySQL",        "\U0001f42c"),
    ("duckdb",    "DuckDB",       "\U0001f986"),
    ("bigquery",  "BigQuery",     "\U0001f4ca"),
    ("snowflake", "Snowflake",    "\u2744\ufe0f"),
]


def render(on_loaded) -> None:
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown('<div class="up-conn-card">', unsafe_allow_html=True)
        st.markdown(
            '<h3 class="up-conn-title">Connect to a <em>database</em></h3>'
            '<p class="up-conn-sub">Run a query and load the result directly into AutoDS.</p>',
            unsafe_allow_html=True,
        )

        provider = _render_provider_tiles("up_db_prov", PROVIDERS, default="postgres")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Host", placeholder="db.example.com", key="up_db_host")
        with c2:
            st.text_input("Port", value="5432", key="up_db_port")

        c3, c4 = st.columns(2)
        with c3:
            st.text_input("Database", placeholder="my_database", key="up_db_name")
        with c4:
            st.text_input("Schema (optional)", placeholder="public", key="up_db_schema")

        c5, c6 = st.columns(2)
        with c5:
            st.text_input("Username", key="up_db_user")
        with c6:
            st.text_input("Password", type="password", placeholder="\u2022" * 8, key="up_db_pass")

        st.text_area("Query or table name", placeholder="SELECT * FROM orders LIMIT 50000",
                     key="up_db_query", height=100)

        b1, b2, b3 = st.columns(3)
        with b1:
            test_clicked = st.button("Test connection", key="up_db_test")
        with b2:
            st.button("Preview rows", key="up_db_preview", disabled=True)
        with b3:
            st.button("Load data", type="primary", key="up_db_load", disabled=True)

        if test_clicked:
            st.info("Database connector not yet configured in this environment. "
                    "Use Manual upload or a sample dataset instead.")

        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        st.markdown(
            '<div class="up-info-panel">'
            '  <h4>\U0001f4dd Query best practices</h4>'
            '  <ul>'
            '    <li>Add a LIMIT clause to avoid loading huge tables</li>'
            '    <li>Use WHERE to filter to the rows you need</li>'
            '    <li>Select only the columns required for your analysis</li>'
            '  </ul>'
            '</div>'
            '<div class="up-info-panel">'
            '  <h4>\U0001f512 SSL note</h4>'
            '  <p>Connections use SSL by default when supported by the database engine.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_provider_tiles(state_key: str, providers, default: str) -> str:
    selected = st.session_state.get(state_key, default)
    st.markdown('<div class="up-providers">', unsafe_allow_html=True)
    cols = st.columns(len(providers))
    for col, (key, label, icon) in zip(cols, providers):
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
