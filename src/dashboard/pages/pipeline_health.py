"""Pipeline health dashboard page."""
import pandas as pd
import streamlit as st
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    quality = context.quality
    st.subheader('Data lineage & quality')
    st.success(f'Last successful ETL: {quality["completed_at_utc"]}')
    st.dataframe(pd.DataFrame([{ 'Dataset': name, **{k: value for k, value in quality[name].items() if k in ['raw','clean','rejected']}} for name in ['collision','vehicle','casualty','weather']]), hide_index=True)
    st.json(quality['checks'])
    st.warning('Weather join blocked: supplied station lies outside Great Britain. Location and temporal matching must both pass before any external values enter the collision mart.')
    st.caption('Raw → staging Parquet → validated child tables + collision mart → SQLite warehouse → Streamlit. Originals and rejected records are retained on disk.')
    st.json(quality['weather'])
