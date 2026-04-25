"""LLM Provider Selector -- sidebar widget to switch between AI models.

Allows runtime switching between Ollama (local Gemma), Google Gemini,
Anthropic Claude, and OpenAI GPT models.
"""

from __future__ import annotations

import os

import streamlit as st

from core.llm_config import (
    get_available_providers,
    get_provider_name,
    set_runtime_provider,
)


def render_llm_selector() -> str:
    """Render LLM provider selector in sidebar.

    Returns:
        Selected provider key string.
    """
    providers = get_available_providers()
    current = st.session_state.get("llm_provider", get_provider_name())

    st.markdown("##### AI Model")

    # Build options
    options = []
    option_map = {}
    for p in providers:
        status = "Ready" if p["available"] else f"Need {p['key_env']}"
        label = f"{p['icon']} {p['label']}"
        if not p["available"]:
            label += " (no key)"
        options.append(label)
        option_map[label] = p["id"]

    # Find current index
    current_labels = [l for l, pid in option_map.items() if pid == current]
    current_idx = options.index(current_labels[0]) if current_labels else 0

    selected_label = st.selectbox(
        "LLM Provider",
        options=options,
        index=current_idx,
        key="llm_provider_select",
        label_visibility="collapsed",
    )

    selected_id = option_map.get(selected_label, "ollama")

    # Check if provider changed
    if selected_id != current:
        # Verify key available for API providers
        provider_info = next((p for p in providers if p["id"] == selected_id), None)
        if provider_info and not provider_info["available"]:
            st.warning(f"Set `{provider_info['key_env']}` in `.env` to use this provider.")
            return current

        set_runtime_provider(selected_id)
        st.session_state["llm_provider"] = selected_id
        st.toast(f"Switched to {selected_label}", icon="🔄")

    st.session_state["llm_provider"] = selected_id

    # Show provider status
    provider_info = next((p for p in providers if p["id"] == selected_id), None)
    if provider_info:
        if selected_id == "ollama":
            st.caption("Free local model via Ollama")
        elif provider_info["available"]:
            st.caption(f"{provider_info['desc']}")
        else:
            st.caption(f"⚠ API key not configured")

    return selected_id
