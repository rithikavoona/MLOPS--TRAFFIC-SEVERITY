"""Shared filter selection and pure filtering logic."""
from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from src.config import SEVERITY


@dataclass(frozen=True)
class FilterSelection:
    years: list[int]
    severities: list[str]
    areas: list[str]
    roads: list[str]
    dates: tuple[date, ...]


def apply_filters(data: pd.DataFrame, selection: FilterSelection) -> pd.DataFrame:
    mask = (
        data.collision_year.isin(selection.years)
        & data.severity.isin(selection.severities)
        & data.area.isin(selection.areas)
        & data.road.isin(selection.roads)
    )
    if len(selection.dates) == 2:
        mask &= data.date.between(
            pd.Timestamp(selection.dates[0]), pd.Timestamp(selection.dates[1]),
        )
    return data.loc[mask]


def render_filters(data: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title('Explore the data')
    years = sorted(data.collision_year.unique())
    areas = sorted(data.area.unique())
    roads = sorted(data.road.unique())
    selected_years = st.sidebar.multiselect('Year', years, default=years)
    severities = st.sidebar.multiselect(
        'Collision severity', list(SEVERITY.values()), default=list(SEVERITY.values()),
    )
    selected_areas = st.sidebar.multiselect('Area', areas, default=areas)
    selected_roads = st.sidebar.multiselect('Road type', roads, default=roads)
    dates = st.sidebar.date_input(
        'Date window',
        value=(data.date.min().date(), data.date.max().date()),
        min_value=data.date.min().date(),
        max_value=data.date.max().date(),
    )
    selection = FilterSelection(
        selected_years, severities, selected_areas, selected_roads,
        tuple(dates) if isinstance(dates, (tuple, list)) else (dates,),
    )
    st.sidebar.caption(
        'Filters apply to analytical views and linked vehicle/casualty records. '
        'Model and pipeline information use the full dataset.'
    )
    return apply_filters(data, selection)
