"""Approval Widget -- human-in-the-loop approval UI for pipeline decisions.

Shows proposed decisions, lets the user approve or modify, and stores the
result in ``st.session_state``.
"""

from typing import Any, Callable

import streamlit as st


def render_approval_widget(
    step_name: str,
    decisions: dict[str, Any],
    on_approve: Callable[[], None] | None = None,
    on_modify: Callable[[dict], None] | None = None,
    reasoning: str = "",
    key_prefix: str = "",
) -> bool:
    """Render a human-in-the-loop approval widget.

    Args:
        step_name: Display name of the pipeline step (e.g. ``"Feature Engineering"``).
        decisions: Dict of decision_name -> value proposed by the system.
        on_approve: Callback fired when the user clicks Approve.
        on_modify: Callback fired with the modified decisions dict.
        reasoning: Optional AI reasoning text shown in an expander.
        key_prefix: Streamlit key prefix to avoid widget collisions.

    Returns:
        ``True`` if the user has approved (either now or previously).
    """
    approval_key = f"{key_prefix}_approval_{step_name}"

    if st.session_state.get(approval_key):
        st.success(f"{step_name} -- Approved")
        return True

    st.markdown(f"#### Approve: {step_name}")

    # Display decisions as a clean table
    if decisions:
        rows: list[dict[str, str]] = []
        for name, value in decisions.items():
            display_val = value if isinstance(value, str) else str(value)
            rows.append({"Decision": name, "Proposed Value": display_val})
        st.table(rows)

    # AI reasoning expander
    if reasoning:
        with st.expander("View AI reasoning", expanded=False):
            st.markdown(reasoning)

    # Action buttons
    col_approve, col_modify = st.columns(2)

    with col_approve:
        if st.button(
            "Approve & Continue",
            key=f"{key_prefix}_btn_approve_{step_name}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state[approval_key] = True
            st.session_state[f"{approval_key}_decisions"] = decisions
            if on_approve is not None:
                on_approve()
            st.rerun()

    with col_modify:
        show_modify = st.button(
            "Modify",
            key=f"{key_prefix}_btn_modify_{step_name}",
            use_container_width=True,
        )

    # Editable form when Modify is clicked
    if show_modify or st.session_state.get(f"{key_prefix}_modifying_{step_name}"):
        st.session_state[f"{key_prefix}_modifying_{step_name}"] = True

        with st.form(key=f"{key_prefix}_form_{step_name}"):
            st.markdown("**Edit decisions:**")
            modified: dict[str, Any] = {}
            for name, value in decisions.items():
                if isinstance(value, bool):
                    modified[name] = st.checkbox(name, value=value)
                elif isinstance(value, (int, float)):
                    modified[name] = st.number_input(name, value=value)
                else:
                    modified[name] = st.text_input(name, value=str(value))

            if st.form_submit_button("Save & Approve", type="primary"):
                st.session_state[approval_key] = True
                st.session_state[f"{approval_key}_decisions"] = modified
                st.session_state[f"{key_prefix}_modifying_{step_name}"] = False
                if on_modify is not None:
                    on_modify(modified)
                st.rerun()

    return bool(st.session_state.get(approval_key, False))
