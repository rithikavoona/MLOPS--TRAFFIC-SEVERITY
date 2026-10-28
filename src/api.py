"""Validated FastAPI inference with local latency/failure logs."""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from src.config import MODELS, ROOT, FEATURES, SEVERITY

bundle = None


@asynccontextmanager
async def lifespan(app):
    global bundle
    path = MODELS / 'severity.joblib'
    if path.exists():
        bundle = joblib.load(path)
    (ROOT / 'logs').mkdir(exist_ok=True)
    yield


app = FastAPI(title='Traffic severity prediction', version='1.0', lifespan=lifespan)


@app.middleware('http')
async def request_metrics(request, call_next):
    """Include validation errors and unavailable models in service failure metrics."""
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        if request.url.path == '/predict':
            record = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'status_code': status_code, 'status': 'success' if status_code < 400 else 'failed', 'latency_ms': (time.perf_counter() - started) * 1000}
            try:
                (ROOT / 'logs').mkdir(exist_ok=True)
                with (ROOT / 'logs' / 'service_requests.jsonl').open('a') as file:
                    file.write(json.dumps(record) + '\n')
            except OSError:
                logging.exception('Unable to persist request telemetry')


class Scenario(BaseModel):
    hour: int = Field(ge=0, le=23)
    month: int = Field(ge=1, le=12)
    weekday_number: int = Field(ge=0, le=6)
    speed_limit: int = Field(ge=10, le=70)
    road_type: int = Field(ge=1, le=12)
    first_road_class: int = Field(ge=1, le=6)
    light_conditions: int = Field(ge=1, le=7)
    weather_conditions: int = Field(ge=1, le=9)
    road_surface_conditions: int = Field(ge=1, le=7)
    urban_or_rural_area: int = Field(ge=1, le=3)
    latitude: float = Field(ge=49, le=61)
    longitude: float = Field(ge=-9, le=2.5)


@app.get('/health')
def health():
    return {'status': 'ready' if bundle else 'model_missing', 'version': bundle['version'] if bundle else None}


@app.post('/predict')
def predict(scenario: Scenario):
    if bundle is None:
        raise HTTPException(503, 'Train the model before serving predictions.')
    started = time.perf_counter()
    record = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'version': bundle['version']}
    try:
        values = scenario.model_dump()
        probabilities = bundle['pipeline'].predict_proba(pd.DataFrame([values])[FEATURES])[0]
        classes = bundle['pipeline'].classes_
        result = {'severity': SEVERITY[int(classes[probabilities.argmax()])], 'probabilities': {SEVERITY[int(k)]: float(v) for k, v in zip(classes, probabilities)}, 'model_version': bundle['version']}
        record.update(status='success', inputs=values, predicted_class=int(classes[probabilities.argmax()]))
        return result
    except Exception:
        record['status'] = 'failed'
        logging.exception('Inference failed')
        raise HTTPException(500, 'Inference failed; inspect service logs.')
    finally:
        record['latency_ms'] = (time.perf_counter() - started) * 1000
        with (ROOT / 'logs' / 'predictions.jsonl').open('a') as file:
            file.write(json.dumps(record) + '\n')
