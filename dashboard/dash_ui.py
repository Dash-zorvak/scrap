"""Cabecera ejecutiva compartida del panel de carga."""

import streamlit as st


def _page_head(overline: str, title: str, sub: str, stats: str = ""):
    stats_html = f'<div class="page-stats">{stats}</div>' if stats else ''
    st.markdown(f"""
    <div class="page-head">
        <div class="page-overline">{overline}</div>
        <div class="page-h">{title}</div>
        <div class="page-sub">{sub}</div>
        {stats_html}
    </div>
    """, unsafe_allow_html=True)
