"""Reusable Streamlit UI helpers for the platform pages."""

from __future__ import annotations

import streamlit as st

from shared.documentation_content import get_section_help


def render_section_header(title: str, help_text: str | None = None, *, key: str | None = None) -> None:
    """Render a section header with a compact info button."""

    section_key = key or title.lower().replace(" ", "_").replace("·", "").replace("—", "_")
    section_help = help_text or get_section_help(title)

    left_col, right_col = st.columns([0.96, 0.04], vertical_alignment="center")
    with left_col:
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    with right_col:
        if st.button("ℹ", key=f"{section_key}_info", help=section_help or title, use_container_width=True):
            state_key = f"{section_key}_info_open"
            st.session_state[state_key] = not st.session_state.get(state_key, False)

    state_key = f"{section_key}_info_open"
    if st.session_state.get(state_key, False):
        st.info(section_help or title)
