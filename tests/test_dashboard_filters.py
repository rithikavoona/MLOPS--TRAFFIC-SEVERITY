from datetime import date

import pandas as pd

from src.dashboard.filters import FilterSelection, apply_filters


def test_combined_filters_include_date_boundaries_without_other_rows():
    data = pd.DataFrame({
        'collision_index': ['start', 'end', 'next_month', 'serious', 'rural'],
        'date': pd.to_datetime(['2024-01-01', '2024-01-31', '2024-02-01', '2024-01-15', '2024-01-15']),
        'collision_year': [2024] * 5,
        'severity': ['Fatal', 'Fatal', 'Fatal', 'Serious', 'Fatal'],
        'area': ['Urban', 'Urban', 'Urban', 'Urban', 'Rural'],
        'road': ['Single carriageway'] * 5,
    })
    selected = FilterSelection(
        years=[2024], severities=['Fatal'], areas=['Urban'],
        roads=['Single carriageway'], dates=(date(2024, 1, 1), date(2024, 1, 31)),
    )
    assert apply_filters(data, selected).collision_index.tolist() == ['start', 'end']
