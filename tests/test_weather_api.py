import pandas as pd
from fastapi.testclient import TestClient
from src.pipeline import enrich_weather
from src.api import app
from src import api as api_module
import json


def test_weather_requires_location_and_utc_hour():
    mart = pd.DataFrame({'latitude':[51.5,51.5,54], 'longitude':[-.12,-.12,-2], 'timestamp_local':pd.to_datetime(['2024-07-01 13:30','2024-07-01 15:30','2024-07-01 13:30'])})
    weather = pd.DataFrame({'latitude':[51.5], 'longitude':[-.12], 'timestamp_utc':pd.to_datetime(['2024-07-01 12:00'], utc=True), 'temperature_c':[20.]})
    result = enrich_weather(mart, weather)
    assert result.external_weather_status.tolist() == ['matched','unmatched_time','unmatched_location']
    assert result.external_temperature_c.iloc[0] == 20
    berlin = weather.assign(latitude=52.55, longitude=13.41)
    assert enrich_weather(mart, berlin).external_temperature_c.isna().all()


def test_api_validation_and_prediction():
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        assert client.post('/predict', json={'hour':99}).status_code == 422
        payload = {'hour':17,'month':6,'weekday_number':2,'speed_limit':30,'road_type':6,'first_road_class':3,'light_conditions':1,'weather_conditions':1,'road_surface_conditions':1,'urban_or_rural_area':1,'latitude':51.5,'longitude':-.12}
        response = client.post('/predict', json=payload)
        assert response.status_code == 200
        assert abs(sum(response.json()['probabilities'].values()) - 1) < 1e-6


def test_http_validation_failure_is_counted_in_service_telemetry(tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, 'ROOT', tmp_path)
    with TestClient(app) as client:
        assert client.post('/predict', json={'hour':99}).status_code == 422
    records = [json.loads(line) for line in (tmp_path / 'logs/service_requests.jsonl').read_text().splitlines()]
    assert records[-1]['status'] == 'failed'
    assert records[-1]['status_code'] == 422
    assert records[-1]['latency_ms'] >= 0
