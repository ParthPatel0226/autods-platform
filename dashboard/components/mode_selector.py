"""Mode Selector -- Auto / Guided / Expert toggle widget.

Renders styled flashcards with buttons for mode selection.
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
        "color": "var(--accent-primary)",
    },
    MODE_GUIDED: {
        "label": "Guided",
        "icon": "sliders",
        "description": "Interactive -- system recommends, you approve.",
        "color": "var(--accent-secondary)",
    },
    MODE_EXPERT: {
        "label": "Expert",
        "icon": "wrench",
        "description": "Full control -- you specify every parameter.",
        "color": "var(--accent-warning)",
    },
}

_ORDERED_MODES: Final[list[str]] = [MODE_AUTO, MODE_GUIDED, MODE_EXPERT]
_RECOMMENDED_MODE: Final[str] = MODE_GUIDED


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
        border_css = f"border: 2px solid {info['color']};" if is_selected else "border: 1px solid var(--border-subtle);"
        bg_css = f"background: color-mix(in srgb, {info['color']} 8%, transparent);" if is_selected else ""

        with col:
            rec_html = ""
            if mode_key == _RECOMMENDED_MODE:
                rec_html = (
                    '<div style="font-size:0.65rem;font-weight:700;color:var(--accent-secondary);'
                    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.15rem;">'
                    "Recommended</div>"
                )
            st.markdown(
                f"""
                {rec_html}
                <div style="padding: 0.75rem; border-radius: 0.5rem; text-align: center;
                            {border_css} {bg_css} margin-bottom: 0.25rem;">
                    <div style="font-size: 1.1rem; font-weight: 600; color: {info['color']};">
                        :{info['icon']}: {info['label']}
                    </div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.25rem;">
                        {info['description']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"Select {info['label']}",
                key=f"mode_sel_btn_{mode_key}",
                use_container_width=True,
            ):
                current_mode = mode_key

    st.session_state["user_mode"] = current_mode
    return current_mode
