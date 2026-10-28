"""Explicit inputs shared by dashboard pages; pages do not rely on app globals."""
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DashboardContext:
    filtered: pd.DataFrame
    quality: dict[str, Any]
