"""Mode Selector — Auto / Guided / Expert toggle widget.

Renders a styled radio group that lets the user choose the analysis mode.
Stores the selection in ``st.session_state["user_mode"]``.
"""

from typing import Final

import streamlit as st

from core.constants import MODE_AUTO, MODE_EXPERT, MODE_GUIDED

_MODE_OPTIONS: Final[dict[str, dict[str, str]]] = {
    MODE_AUTO: {
        "label": "Auto",
        "icon": "bolt",
        "description": "Fully autonomous -- system makes all decisions.",
        "color": "#6366f1",
    },
    MODE_GUIDED: {
        "label": "Guided",
        "icon": "sliders",
        "description": "Interactive -- system recommends, you approve.",
        "color": "#0ea5e9",
    },
    MODE_EXPERT: {
        "label": "Expert",
        "icon": "wrench",
        "description": "Full control -- you specify every parameter.",
        "color": "#f59e0b",
    },
}

_ORDERED_MODES: Final[list[str]] = [MODE_AUTO, MODE_GUIDED, MODE_EXPERT]


def render_mode_selector() -> str:
    """Render the Auto / Guided / Expert mode selector.

    Returns:
        The selected mode string (``"auto"`` | ``"guided"`` | ``"expert"``).
    """
    current_mode: str = st.session_state.get("user_mode", MODE_GUIDED)

    st.markdown("##### Analysis Mode")

    cols = st.columns(len(_ORDERED_MODES))
    for col, mode_key in zip(cols, _ORDERED_MODES):
        info = _MODE_OPTIONS[mode_key]
        is_selected = mode_key == current_mode
        border_css = f"border: 2px solid {info['color']};" if is_selected else "border: 1px solid #e5e7eb;"
        bg_css = f"background: {info['color']}11;" if is_selected else ""

        with col:
            st.markdown(
                f"""
                <div style="padding: 0.75rem; border-radius: 0.5rem; text-align: center;
                            {border_css} {bg_css} margin-bottom: 0.25rem;">
                    <div style="font-size: 1.1rem; font-weight: 600; color: {info['color']};">
                        :{info['icon']}: {info['label']}
                    </div>
                    <div style="font-size: 0.78rem; color: #6b7280; margin-top: 0.25rem;">
                        {info['description']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    selected_label = st.radio(
        "Select mode",
        options=[_MODE_OPTIONS[m]["label"] for m in _ORDERED_MODES],
        index=_ORDERED_MODES.index(current_mode),
        horizontal=True,
        label_visibility="collapsed",
        key="mode_selector_radio",
    )

    label_to_mode = {_MODE_OPTIONS[m]["label"]: m for m in _ORDERED_MODES}
    chosen_mode = label_to_mode.get(selected_label, MODE_GUIDED)

    st.session_state["user_mode"] = chosen_mode
    return chosen_mode
