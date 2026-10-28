"""Cached access to processed artifacts and saved evaluation metrics."""
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.config import MODELS, PROCESSED

COLLISION_COLUMNS = (
    'collision_index', 'collision_year', 'date', 'hour', 'severity', 'area',
    'road', 'weather', 'surface', 'lighting', 'latitude', 'longitude',
    'weekday_number', 'number_of_vehicles', 'number_of_casualties', 'is_severe',
)
CHILD_COLUMNS = {
    'vehicle': ('collision_index', 'vehicle_type', 'age_of_driver'),
    'casualty': ('collision_index', 'age_of_casualty', 'casualty_severity', 'casualty_class'),
}


@st.cache_data
def _read_parquet(path: str, signature: int, columns: tuple | None) -> pd.DataFrame:
    return pd.read_parquet(path, columns=list(columns) if columns else None)


@st.cache_data
def _read_json(path: str, signature: int) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _parquet(name: str, columns: tuple | None = None) -> pd.DataFrame:
    path = PROCESSED / name
    return _read_parquet(str(path), path.stat().st_mtime_ns, columns)


def load_collisions() -> pd.DataFrame:
    return _parquet('collision_mart.parquet', COLLISION_COLUMNS)


def load_quality() -> dict[str, Any]:
    path = PROCESSED / 'quality_report.json'
    return _read_json(str(path), path.stat().st_mtime_ns)


def load_children(name: str) -> pd.DataFrame:
    if name not in CHILD_COLUMNS:
        raise ValueError(f'Unsupported child dataset: {name}')
    return _parquet(f'{name}.parquet', CHILD_COLUMNS[name])


def load_weather() -> pd.DataFrame:
    return _parquet('weather_external.parquet')


def load_model_metrics() -> dict[str, Any] | None:
    path = MODELS / 'metrics.json'
    if not path.exists():
        return None
    return _read_json(str(path), path.stat().st_mtime_ns)


