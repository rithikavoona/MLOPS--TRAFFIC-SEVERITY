"""Conditions dashboard page."""
import plotly.express as px
import streamlit as st
from src.dashboard.charts import chart
from src.dashboard.data import load_weather
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    filtered = context.filtered
    for columns in [['weather', 'surface'], ['road', 'lighting']]:
        panes = st.columns(2)
        for pane, field in zip(panes, columns):
            with pane:
                summary = filtered.groupby(field).agg(collisions=('collision_index', 'size'), severe=('is_severe', 'sum')).reset_index()
                summary['Severe share (%)'] = 100 * summary.severe / summary.collisions
                chart(px.bar(summary.sort_values('Severe share (%)'), x='Severe share (%)', y=field, orientation='h', color='collisions', color_continuous_scale='Teal', hover_data=['collisions', 'severe'], title=f'Severity association by {field}'))
    st.warning('External weather enrichment: 0 matches. The supplied temperature file is a Berlin station (52.55°N, 13.41°E). These charts use DfT recorded weather and surface conditions.')
    external = load_weather()
    with st.expander('Separate Berlin weather series — unrelated to GB collisions'):
        daily = external.set_index('timestamp_utc').temperature_c.resample('D').mean().reset_index()
        chart(px.line(daily, x='timestamp_utc', y='temperature_c', title='Berlin daily mean temperature (°C)'))
