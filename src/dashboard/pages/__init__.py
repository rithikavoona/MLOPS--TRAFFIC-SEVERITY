"""Page registration; imports do not render UI or load datasets."""
from src.dashboard.pages import overview, time_patterns, conditions, hotspots, vehicles_casualties, severity_model, pipeline_health

PAGES = (
    ('Overview', overview.render),
    ('Time patterns', time_patterns.render),
    ('Conditions', conditions.render),
    ('Hotspots', hotspots.render),
    ('Vehicles & casualties', vehicles_casualties.render),
    ('Severity model', severity_model.render),
    ('Pipeline health', pipeline_health.render),
)
