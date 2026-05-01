"""Cloud storage connector panel — S3 / GCS / Azure Blob."""
from __future__ import annotations
import streamlit as st


PROVIDERS = [
    ("s3",    "AWS S3",       "\U0001fab3"),
    ("gcs",   "Google GCS",   "\u2601\ufe0f"),
    ("azure", "Azure Blob",   "\U0001f7e6"),
]


def render(on_loaded) -> None:
    cols = st.columns([2, 1], gap="medium")

    with cols[0]:
        st.markdown('<div class="up-conn-card">', unsafe_allow_html=True)
        st.markdown(
            '<h3 class="up-conn-title">Connect to <em>cloud storage</em></h3>'
            '<p class="up-conn-sub">Pull objects directly from your cloud bucket. Read-only credentials only.</p>',
            unsafe_allow_html=True,
        )

        provider = _render_provider_tiles("up_cloud_prov", PROVIDERS, default="s3")

        c1, c2 = st.columns(2)
        with c1:
            bucket = st.text_input("Bucket name", placeholder="my-data-bucket", key="up_cloud_bucket")
        with c2:
            region = st.text_input("Region", value="us-east-1", key="up_cloud_region")

        path = st.text_input("Object key or prefix", placeholder="path/to/file.csv or folder/",
                              key="up_cloud_path")

        c3, c4 = st.columns(2)
        with c3:
            access_key = st.text_input("Access key", placeholder="AKIA\u2026", key="up_cloud_access")
        with c4:
            st.text_input("Secret key", type="password", placeholder="\u2022" * 8,
                          key="up_cloud_secret")

        b1, b2 = st.columns([1, 1])
        with b1:
            test_clicked = st.button("Test connection", key="up_cloud_test")
        with b2:
            st.button("Load data", type="primary", key="up_cloud_load", disabled=True)

        if test_clicked:
            if not bucket or not path or not access_key:
                st.warning("Fill in bucket, path, and access key first.")
            else:
                st.info("Cloud connector not yet configured in this environment. "
                        "Use Manual upload or a sample dataset instead.")

        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        st.markdown(
            '<div class="up-info-panel">'
            '  <h4>\U0001f512 Use IAM with least privilege</h4>'
            '  <p>Create a dedicated IAM user with read-only access to this bucket only.</p>'
            '</div>'
            '<div class="up-info-panel">'
            '  <h4>\U0001f6e1 Credentials handling</h4>'
            '  <p>Keys are stored encrypted in your session and never logged.</p>'
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
