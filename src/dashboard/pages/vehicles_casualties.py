"""Vehicles & casualties dashboard page."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.config import SEVERITY
from src.dashboard.charts import chart
from src.dashboard.data import load_children
from src.dashboard.theme import SEVERITY_COLORS as COLORS
from src.dashboard.context import DashboardContext


def render(context: DashboardContext) -> None:
    filtered = context.filtered
    ids = filtered.collision_index
    vehicles = load_children('vehicle')
    casualties = load_children('casualty')
    vehicles, casualties = vehicles[vehicles.collision_index.isin(ids)], casualties[casualties.collision_index.isin(ids)]
    a, b = st.columns(2)
    with a:
        types = vehicles.vehicle_type.value_counts().head(12).rename_axis('Vehicle type code').reset_index(name='Vehicles')
        types['Vehicle type code'] = types['Vehicle type code'].astype(str)
        chart(px.bar(types, x='Vehicle type code', y='Vehicles', title='Most common vehicle types (DfT codes)'))
        ages = vehicles[vehicles.age_of_driver.between(0, 110)].copy()
        ages['Age group'] = pd.cut(ages.age_of_driver, bins=list(range(0, 116, 5)), right=False)
        ages = ages.groupby('Age group', observed=False).size().reset_index(name='Drivers')
        ages['Age group'] = ages['Age group'].astype(str)
        chart(px.bar(ages, x='Age group', y='Drivers', title='Driver age distribution'))
    with b:
        ages = casualties[casualties.age_of_casualty.between(0, 110)].copy()
        ages['Casualty severity'] = ages.casualty_severity.map(SEVERITY).fillna('Unknown')
        ages['Age group'] = pd.cut(ages.age_of_casualty, bins=list(range(0, 116, 5)), right=False)
        ages = ages.groupby(['Age group', 'Casualty severity'], observed=False).size().reset_index(name='Casualties')
        ages['Age group'] = ages['Age group'].astype(str)
        chart(px.bar(ages, x='Age group', y='Casualties', color='Casualty severity', color_discrete_map=COLORS, title='Casualty age and severity'))
        classes = casualties.casualty_class.map({1: 'Driver/rider', 2: 'Passenger', 3: 'Pedestrian'}).fillna('Unknown').value_counts().rename_axis('Class').reset_index(name='Casualties')
        chart(px.bar(classes, x='Class', y='Casualties', title='Casualty classes'))
    st.caption(f'{len(vehicles):,} linked vehicle rows · {len(casualties):,} linked casualty rows. Child rows are aggregated before joining to the collision mart to prevent double counting.')
