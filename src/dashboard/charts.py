"""Consistent presentation for every Plotly chart."""
import streamlit as st
from plotly.graph_objects import Figure


def chart(figure: Figure) -> None:
    figure.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(family='Arial', color='#dbeafe'),
    )
    st.plotly_chart(figure, width='stretch')
