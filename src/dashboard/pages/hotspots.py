"""Hotspots dashboard page."""
import plotly.express as px
import streamlit as st
from src.dashboard.charts import chart
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    filtered = context.filtered
    st.subheader('Collision concentration')
    st.caption('Cells are approximately 0.02 degrees; their physical size varies by latitude. Counts are not exposure-adjusted risk estimates.')
    spatial = filtered.assign(lat_cell=(filtered.latitude / .02).round() * .02, lon_cell=(filtered.longitude / .02).round() * .02).groupby(['lat_cell', 'lon_cell']).agg(collisions=('collision_index', 'size'), severe=('is_severe', 'sum')).reset_index()
    chart(px.scatter_map(spatial.nlargest(1500, 'collisions'), lat='lat_cell', lon='lon_cell', size='collisions', color='severe', hover_data=['collisions', 'severe'], zoom=4.5, center={'lat': 54.5, 'lon': -2.5}, map_style='carto-darkmatter', color_continuous_scale='Sunset', title='Top 1,500 collision cells', height=570))
    st.dataframe(spatial.nlargest(20, 'collisions'), hide_index=True, width='stretch')
