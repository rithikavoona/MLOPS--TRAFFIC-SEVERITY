"""Time patterns dashboard page."""
import plotly.express as px
import streamlit as st
from src.dashboard.charts import chart
from src.dashboard.theme import SEVERITY_COLORS as COLORS
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    filtered = context.filtered
    left, right = st.columns(2)
    with left:
        hourly = filtered.groupby(['hour', 'severity']).size().reset_index(name='Collisions')
        chart(px.bar(hourly, x='hour', y='Collisions', color='severity', color_discrete_map=COLORS, title='Collisions by hour', category_orders={'hour': list(range(24))}))
    with right:
        grid = filtered.groupby(['weekday_number', 'hour']).size().unstack(fill_value=0).reindex(index=range(7), columns=range(24), fill_value=0)
        chart(px.imshow(grid, x=list(range(24)), y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], labels=dict(x='Hour', y='Weekday', color='Collisions'), color_continuous_scale='Blues', aspect='auto', title='Weekday × hour'))
    st.caption(f'{filtered.hour.isna().sum():,} records with unavailable time are excluded from hourly views.')
