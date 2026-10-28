# RoadScope — traffic accident severity analytics

A reproducible data engineering and MLOps project using the supplied DfT collision, vehicle and casualty files. The Streamlit application **only reads processed Parquet data**. The original files remain in `data/raw` with SHA-256 fingerprints.

## Quick start (PowerShell)

Open PowerShell in the extracted `traffic_severity` folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.pipeline --source data/raw
# Start the prediction API in a separate terminal before using the prediction form:
# .\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501. Processed data and a trained model are included in this local workspace, so rerunning ETL/training is optional. If you already have the dependencies, use `python -m streamlit run app.py` directly. Python 3.13 was used for verification. The existing unrelated delivery application in the parent workspace is preserved. `requirements.txt` installs the exact tested versions through `requirements-verified.txt`.

## Project layout

### Opening the processed data

Open `data/processed/csv/` for spreadsheet-friendly CSV copies of every processed table. Start with `collision_mart.csv` for the dashboard dataset. `README.md` in that folder lists row counts and file purposes; `data_dictionary.json` lists every column and type. In Excel, choose **Data > From Text/CSV** and import identifier columns as **Text** to preserve leading zeroes. Regenerate these exports after running ETL with `python scripts/export_processed_csv.py`. The dashboard continues to use the processed Parquet files.

| Path | Purpose |
|---|---|
| `src/pipeline.py` | Ingestion, validation, transformations, dimensions and SQLite warehouse |
| `src/train.py` | Temporal model selection, metrics, bundled preprocessing and MLflow registry |
| `src/api.py` | Validated prediction endpoint and service telemetry |
| `src/monitor.py` | Batch quality, class/location drift, false-negative and latency monitoring |
| `src/weather.py` | Optional historical GB weather extraction |
| `dags/traffic_etl.py` | Weekly Airflow DAG, retries, no overlapping runs |
| `app.py` | Small Streamlit entry point |
| `src/dashboard/application.py` | Shared dashboard setup and page composition |
| `src/dashboard/pages/` | Separate source file for each of the seven tabs |
| `src/dashboard/data.py` | Cached processed data and evaluation metrics |
| `src/dashboard/api_client.py` | Prediction API requests and error handling |
| `src/dashboard/filters.py`, `charts.py`, `layout.py`, `theme.py` | Reusable filters, chart presentation, summary and styling |
| `data/raw` | Unmodified source CSVs and extraction manifest |
| `data/staging` | Typed Parquet snapshots before validation |
| `data/cleaned` | Validated source records before mart enrichment |
| `data/processed` | Cleaned children, collision mart, model data, dimensions, aggregates, quality report |
| `data/rejected` | Rejected rows and reasons |
| `data/warehouse/traffic.sqlite` | Populated open-source analytical database |
| `models` | Model versions, evaluation, training references and monitoring results |
| `docs` | Architecture, dictionary, report and source notes |
| `tests` | ETL edge cases, dashboard rendering/filters, API validation and weather matching |

## Data integrity and weather limitation

The supplied weather station is **Berlin (52.54833°N, 13.407822°E)**. GB collision coordinates do not match it. The ETL implements a 25 km location gate and exact UTC-hour match; British local timestamps are converted using `Europe/London`, with ambiguous/nonexistent DST times excluded. External temperature remains missing for the current inputs. No invented weather values enter the dashboard or model. Recorded DfT weather conditions remain available for analysis. The Berlin series is displayed separately and clearly labeled.

To extract compatible historical station weather, run `python -m src.weather --latitude 51.5 --longitude -0.12 --start 2024-01-01 --end 2024-01-31`. This saves a raw API archive only. Preparing multiple spatially suitable stations and normalizing their responses is further work before nationwide external enrichment. It does not silently alter the mart.

## Model, registry and inference

The dashboard prediction form sends `POST /predict` to the FastAPI service. Local runs default to `http://127.0.0.1:8000`; set `TRAFFIC_API_URL` to override it. Docker Compose configures `http://api:8000` and waits for API health before starting the dashboard. The API applies the saved preprocessing/model pipeline, returns severity probabilities and model version, and logs requests. API failures appear in the dashboard without a local prediction fallback. Historical charts and evaluation metrics remain available from processed files.

```powershell
python -m src.train --mlflow
python -m src.tracking  # Register the existing evaluated model without retraining
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
python -m src.monitor --batch data/processed/model_ready.parquet
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

API documentation: http://localhost:8000/docs. The model trains on 2021–2023, selects depth on 2024 and evaluates on 2025 for the supplied data. Training is capped at 150,000 proportionally sampled rows by default; validation and test use all eligible records. Change `--max-train-rows` to fit all training records. No casualty count, casualty severity, enhanced severity or adjusted severity is a predictor. The saved inference pipeline includes imputers and categorical encoding. Test data is never fit by preprocessing.

Run `python -m src.train` without the flag for local model files when MLflow is unavailable. MLflow is an explicit optional execution mode, listed in full requirements. Registry versions are not automatically promoted to production. The served file is the latest local training artifact; promotion should be reviewed after comparing class recalls and monitoring results.

## Scheduling and containers

Install Airflow 2.x in a separate Linux/WSL environment and place `dags/traffic_etl.py` in its DAG folder. Mount the project at `/opt/traffic`, install project dependencies into the worker, and make CSVs available at `data/raw`. The weekly DAG runs the repeatable ETL with two retries; it does not retrain automatically. Alternatively schedule the CLI command with Windows Task Scheduler. SQLite is the local database alternative; seek instructor approval if PostgreSQL/PostGIS is mandatory for grading.

```powershell
docker compose up --build -d --wait --wait-timeout 180
python scripts/verify_deployment.py
```

The Docker deployment was completed and verified locally on 15 October 2026. Both services are healthy: dashboard http://localhost:8501 and API documentation http://localhost:8000/docs. Read-only mounts provide processed data and models; API telemetry is written to the host logs folder. Health, model-version consistency, prediction probabilities and invalid-input rejection passed. See `docs/docker_deployment.md` and `docs/evidence/deployment/docker_verification.json` for commands and evidence. Docker Desktop must remain running. Airflow's scheduler/worker still needs separate deployment.

## Validation

```powershell
python -m pytest -q
```

Tests verify duplicate/orphan rejection, invalid coordinates, date parsing, missing time, spatial/time weather gates, UI rendering and filters, and inference validation. Execution evidence is in `logs/pipeline.log`, `data/raw/manifest.json`, `data/processed/quality_report.json`, `models/metrics.json` and `models/monitoring.json`.

The supplied nine-page report is `docs/reports/project_report.pdf`. The warehouse schema, populated samples, row counts and dashboard screenshot are in `docs/evidence/schema`, `docs/evidence/samples` and `docs/evidence/screenshots`. `scripts/export_evidence.py` regenerates the schema and samples. Initial verification passed all five tests; a subsequent dashboard check also passed after the final plot refinements. Monitoring was demonstrated on the full processed dataset, including training years; those results are illustrative batch monitoring, not additional held-out evaluation. Service telemetry currently includes a test request and is not a production latency benchmark.

See `docs/project_structure.md` for the folder architecture and `docs/requirements_audit.md` for the complete PDF checklist. Part 1 can be demonstrated using ETL, warehouse and analytical tabs without starting the optional Part 2 model API. The PDF's instructor approval and student authorship requirements cannot be certified by automated checks.

The requirements audit reran ETL successfully, passed all nine persisted-artifact checks and all eight tests. Results are in `docs/evidence/requirements_verification.json` and `logs/audit_tests.log`. `requirements-verified.txt` records exact top-level versions used for verification; use it when you need the tested versions for loading the included model. Report rebuilding dependencies are separate in `requirements-report.txt`.

Package the complete folder with `python scripts/package_project.py`. This excludes installed dependencies/caches and retains raw files, all data layers, models, report and evidence.

The dashboard is organized into one renderer module per tab under `src/dashboard/pages`. Shared filters, data access, chart presentation, layout and theme live beside the pages, while `app.py` only starts the application. A full regression run after this refactor passed nine tests, including every tab, all initial charts, scenario prediction and filter/date boundaries. See `logs/dashboard_refactor_tests.log`.

Local MLflow tracking was verified and the evaluated model registered as `traffic-severity` version 1. The run ID is recorded in `models/metrics.json`; `logs/mlflow_tracking.log` records registry execution. Project-local `.deps` packages were used to complete this check without changing the system's numerical libraries. A fresh environment should install `requirements.txt`. The local dashboard was also opened and verified at http://localhost:8502 during development.

## Interpretation

Statistics cover reported injury collisions, not all traffic incidents. Raw reported severity is used; adjusted severity columns are retained but are not applied. Trends can reflect changes in reporting systems and 2025 data may have a different release status; consult source metadata before claiming comparable annual rates. Severity associations are descriptive and are not causal effects. Hotspot counts have no traffic-exposure denominator. Research predictions are conditional on a collision occurring and probabilities are uncalibrated. No operational safety decisions should be based on the current model alone.
