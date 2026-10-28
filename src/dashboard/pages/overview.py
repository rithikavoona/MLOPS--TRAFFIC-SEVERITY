"""Overview dashboard page."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.dashboard.charts import chart
from src.dashboard.theme import SEVERITY_COLORS as COLORS
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    filtered = context.filtered
    left, right = st.columns([1, 2])
    with left:
        counts = filtered.severity.value_counts().rename_axis('Severity').reset_index(name='Collisions')
        chart(px.pie(counts, names='Severity', values='Collisions', hole=.65, color='Severity', color_discrete_map=COLORS, title='Collision severity'))
    with right:
        monthly = filtered.groupby([pd.Grouper(key='date', freq='MS'), 'severity']).size().reset_index(name='Collisions')
        chart(px.line(monthly, x='date', y='Collisions', color='severity', color_discrete_map=COLORS, title='Monthly collision trend'))
    st.info('Counts describe reported injury collisions. Severity shares are associations within these records; traffic exposure and unreported events are unavailable.')
    with st.expander('Explore processed records'):
        cols = ['collision_index', 'date', 'hour', 'severity', 'road', 'weather', 'area', 'number_of_vehicles', 'number_of_casualties']
        st.dataframe(filtered[cols].head(1000), hide_index=True, width='stretch')
        st.download_button('Download filtered processed data', filtered[cols].to_csv(index=False), 'roadscope_filtered.csv', 'text/csv')
