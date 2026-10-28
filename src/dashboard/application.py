"""Compose shared layout, processed data and the independently defined pages."""
import streamlit as st

from src.config import PROCESSED
from src.dashboard.context import DashboardContext
from src.dashboard.data import load_collisions, load_quality
from src.dashboard.filters import render_filters
from src.dashboard.layout import render_header, render_summary
from src.dashboard.pages import PAGES
from src.dashboard.theme import configure_page


def main() -> None:
    configure_page()
    render_header()
    if not (PROCESSED / 'collision_mart.parquet').exists():
        st.info(
            'Run the ETL first: python -m src.pipeline '
            '--source <folder containing the supplied CSV files>'
        )
        st.stop()
    data = load_collisions()
    filtered = render_filters(data)
    if filtered.empty:
        st.warning('No collisions match the selected filters.')
        st.stop()
    render_summary(filtered, len(data))
    context = DashboardContext(filtered=filtered, quality=load_quality())
    tabs = st.tabs([title for title, _ in PAGES])
    for tab, (_, render_page) in zip(tabs, PAGES):
        with tab:
            render_page(context)
