"""Application appearance and shared severity colors."""
import streamlit as st

SEVERITY_COLORS = {'Fatal': '#fb7185', 'Serious': '#fbbf24', 'Slight': '#38bdf8'}
CSS = '''<style>
.stApp {background:#0b1220;color:#e2e8f0} [data-testid="stSidebar"] {background:#111d30}
[data-testid="stMetric"] {background:#17243a;padding:20px;border-radius:12px;border:1px solid #263b55}
h1,h2,h3 {letter-spacing:-.03em} .stCaption {color:#9aabc3}
</style>'''


def configure_page() -> None:
    st.set_page_config(
        page_title='RoadScope | Traffic intelligence',
        page_icon='🚦',
        layout='wide',
    )
    st.markdown(CSS, unsafe_allow_html=True)
