# PDF requirements audit

Reference: `docs/reference/assignment_brief.pdf`, all four pages. Audited against source code, persisted artifacts, warehouse tables, successful execution logs and tests. Updated 15 October 2026: Docker image build and local dashboard/API container deployment are verified. **The project is not yet fully compliant with every requirement.** Weather integration has no valid GB matches; scheduled Airflow execution is not demonstrated; approval of the SQLite alternative and student-specific submission conditions remain external.

Status definitions: **Verified** = implementation with local artifact/test/run evidence; **Implemented** = source/configuration present but runtime deployment not demonstrated; **Blocked** = supplied data or environment cannot fulfill the outcome; **Approval needed** = only instructor/user can confirm; **Optional** = not a mandatory feature.

## Pages 1–2: objectives, ingestion, architecture, ETL and views

| PDF requirement | Status | Evidence / remaining action |
|---|---|---|
| Accident analytics warehouse and dashboard | Verified | SQLite `fact_collision`, processed mart, `app.py`, screenshot and dashboard test |
| Accident + external weather integration | Blocked | Spatial/UTC matcher exists and is tested; Berlin station has zero GB matches. Acquire geographically compatible GB weather and normalize it before claiming completion. |
| Location- and time-aware database | Verified | Date key, local timestamp, coordinates, district fields and indexed collision fact |
| Patterns and contributing conditions | Verified | Severity, time, weather/surface/lighting, hotspots and people views; descriptions are associations, not causal effects |
| Severity MLOps workflow | Verified locally | Training, evaluation, registry, API and Docker deployment evidence; model remains a research prototype |
| Use public/free/institutional sources | Verified for supplied inputs | Supplied DfT and Open-Meteo files; provenance recorded in `docs/sources.md` |
| Source names and access instructions in report | Verified | Report page 2 and `docs/sources.md` |
| Optional Kaggle alternative | Optional | DfT source selected; no alternative needed |
| Optional OpenStreetMap enrichment | Optional | Map basemap available; road-network enrichment is not implemented |
| Python/Pandas CSV ingestion | Verified | `src/pipeline.py`, full-data ETL log |
| Python requests weather API | Implemented | `src/weather.py`; HTTP status/error/row-count logs supported, extraction not executed during this audit |
| Airflow staged extraction, transformation and schedule | Implemented | Three tasks: ingest → transform/load → persisted validation; weekly schedule, retries; scheduler/worker not launched |
| PostgreSQL/PostGIS recommendation | Approval needed | SQLite used as local open-source alternative; obtain instructor approval if required |
| Retain raw copy | Verified | Four original CSVs and `data/raw/manifest.json`; SHA-256 provenance |
| Extraction date, source, status, row counts | Verified | Ingestion manifest; API extraction-log implementation also includes these fields |
| Extraction errors and failed records | Verified locally | Pipeline exception logs, rejected rows with reasons; API error handling present but not live-tested |
| Repeatable or scheduled workflow | Verified repeatable; schedule implemented | `python -m src.pipeline`; Airflow DAG definition included |
| No manual edits to analytical dataset | Verified workflow | All layers produced by pipeline code; audit rebuilds from raw sources |
| Architecture diagram covering required layers | Verified | `docs/architecture.md`: sources, ingestion, staging/cleaning, transformation, storage, analytics and MLOps |
| Standardize date/time/severity/road/location | Verified | Explicit date parsing, derived hour/date keys, code labels, coordinate validation |
| Remove duplicates and invalid coordinates | Verified | ETL key rules, rejection logs and edge-case tests |
| Join weather using time AND location | Implemented, outcome blocked | 25 km gate + local-to-UTC conversion + hourly join; incompatible weather data prevents real matches |
| Date, road, weather, location, severity dimensions | Verified | Populated `dim_*` tables, processed Parquet and sample CSVs |
| Hour, day, road and weather aggregates | Verified after audit rebuild | `agg_hour`, `agg_day`, `agg_weekday_number`, `agg_road`, `agg_weather`; counts validated against fact |
| Analytical and model-ready tables | Verified | `collision_mart.parquet`, `model_ready.parquet`, SQLite facts |
| Severity distribution | Verified | Overview tab |
| Collisions by hour and weekday | Verified | Time-patterns tab and heatmap |
| Weather and road conditions | Verified for recorded DfT fields | Conditions tab; external weather completeness is explicitly unresolved |
| Hotspot map | Verified locally | Aggregated 0.02-degree cells; no exposure-adjusted risk claim |
| Vehicle and casualty analysis | Verified | People tab using linked clean child records |

## Page 3: Part 1 implementation and ten submission items

| PDF requirement | Status | Evidence / remaining action |
|---|---|---|
| Acquire/document chosen data | Verified | Raw CSVs, manifest, source notes |
| Reproducible ingestion scripts | Verified | Pipeline CLI and staged arguments |
| Airflow DAG or approved equivalent | Implemented; runtime unverified | Three-task DAG included; CLI repeatability demonstrated; equivalence approval is external |
| Raw, staging, cleaned and analytical layers | Verified after audit rebuild | Explicit `data/raw`, `staging`, `cleaned`, `processed` directories |
| Quality checks and rejected/error log | Verified | `quality_report.json`, rejected CSVs, pipeline logs and tests |
| Load PostgreSQL or approved open-source DB | Approval needed | SQLite populated; instructor approval not evidenced |
| At least one data mart | Verified | Collision-grain mart with child aggregates |
| At least five meaningful views/indicators | Verified | Seven tabs plus four headline metrics |
| Architecture and dictionary | Verified | Both Markdown documents included |
| Successful end-to-end run | Verified locally | Raw → processed → database ETL logs, persisted validation and dashboard evidence |
| 1. Source code and ETL | Verified | `src`, `app.py`, `scripts` |
| 2. DAG / approved workflow | Implemented | `dags/traffic_etl.py`; approval/runtime caveat above |
| 3. Schema and sample populated tables | Verified | `docs/evidence/schema` and `docs/evidence/samples` |
| 4. Source and access information | Verified | Source notes and report |
| 5. Architecture and pipeline flow | Verified | Architecture diagram |
| 6. Data dictionary and validation rules | Verified | Data dictionary |
| 7. Streamlit app | Verified | `app.py`, UI screenshot and render/filter tests |
| 8. Approximately 8–10-page report | Verified | Nine-page `docs/reports/project_report.pdf` |
| 9. Screenshots or execution evidence | Verified | Screenshot, warehouse counts, test/ETL logs, metrics and registry evidence |
| 10. Setup/run README | Verified | Dependency setup, ETL, Streamlit, training, API, monitoring, Docker commands |
| Part 1 without final ML deployment | Submission choice needed | The combined project includes optional Part 2 code/UI. Demonstrate analytics separately without launching API; confirm whether instructor requires a separate Part 1-only package. |

## Pages 3–4: Part 2 requirements

| PDF requirement | Status | Evidence / remaining action |
|---|---|---|
| Random Forest / XGBoost / LightGBM classifier | Verified | Random Forest selected and trained; alternatives not all required |
| Imbalance weighting or sampling | Verified | Balanced-subsample class weights and proportional capped sampling |
| Recall, macro-F1 and confusion matrix in MLflow | Verified | Per-class recall metrics and evaluation JSON artifact in registered run |
| Preprocessing + model as one inference pipeline | Verified | Imputer, encoder, classifier saved in one bundle |
| Deploy using FastAPI and Docker | Verified locally | Image built; dashboard/API containers healthy; model version, prediction and HTTP 422 checks passed. See `docs/evidence/deployment/docker_verification.json`. |
| Class drift, location drift and false negatives | Verified as batch monitoring | Monitoring script/artifact; new outcomes required for operational false negatives |
| Reproducible feature engineering/training | Verified | Feature allowlist, seed, recorded split/sampling, data hash, saved artifacts |
| Chronological/problem-appropriate splits | Verified | 2021–2023 train, 2024 validation, 2025 held-out test |
| Experiments/parameters/metrics/artifacts tracked | Verified | Local MLflow run ID in metrics file and registry logs |
| Register and version selected model | Verified | `traffic-severity`, version 1, READY |
| Serve predictions with API framework | Verified locally | Running FastAPI container on port 8000, validated prediction and invalid-input checks |
| Containerize inference service | Verified locally | Python 3.13 image built and started with Compose; non-root runtime, read-only model mount, health checks and restart policy |
| Integrate model output into dashboard | Verified | Scenario prediction form and model evaluation tab |
| Monitor input quality, drift and model performance | Verified as batch monitoring | Missing fractions, drift, macro-F1, class recalls and severe FN; example batch overlaps train years and is labeled accordingly |
| Monitor latency and failures | Verified instrumentation | HTTP request middleware includes 422/503/inference failures; test traffic is not production evidence |
| Define retraining criteria | Verified definition | Explicit missingness/drift/performance/service thresholds and review alerts |
| Document lifecycle | Verified | `docs/model_lifecycle.md`: validation, training, tracking, promotion, retraining and rollback |

## Page 4: general instructions and assessment context

| PDF item | Status | Evidence / remaining action |
|---|---|---|
| Student individual work and explanation | Human responsibility | Student must understand, adapt and truthfully explain assisted work under course rules; project files cannot certify authorship |
| Attribution for public code | Human review | Source datasets/libraries documented; student must disclose assistance and any additional reused code as required |
| Environment variables for credentials/API keys | Not applicable locally | SQLite/Open-Meteo inputs require no secrets. No credentials added; future secured DB/API must use environment configuration. |
| No private/PII/confidential uploads | Verified scope | Provided public statistical files handled locally; no external upload performed |
| Demonstration from ingestion to dashboard | Verified locally | ETL evidence and dashboard screenshot; student still performs the final course demonstration |
| Part 1 deadline / Part 2 announcement / late policy | Course administration | These document dates/policies are not software features and cannot be completed or changed by code |
| Suggested mark distribution | Assessment context | Coverage matrix supplied; no marks or instructor acceptance are guaranteed |

## What still prevents a complete compliance claim

1. Obtain compatible GB weather observations and demonstrate at least one genuine time/location match. The current Berlin dataset is unsuitable; do not fill missing temperature with unrelated data.
2. Install/start the Airflow worker/scheduler and demonstrate the staged DAG if the instructor expects scheduled execution rather than the repeatable CLI.
3. Obtain approval for SQLite or deploy the warehouse to PostgreSQL/PostGIS.
4. Confirm whether Part 1 must exclude the optional Part 2 code and complete student-specific authorship, attribution and presentation obligations.

The audit reran the full ETL, checked all nine persisted-artifact invariants and passed eight tests, including unlabeled monitoring and HTTP validation-failure telemetry. Machine-readable checks are in `docs/evidence/requirements_verification.json`, the verified dependency versions are in `docs/evidence/verified_environment.json`, and test output is in `logs/audit_tests.log`.

The downloadable archive includes this audit. File presence does not establish operational deployment, source compatibility or instructor approval.
