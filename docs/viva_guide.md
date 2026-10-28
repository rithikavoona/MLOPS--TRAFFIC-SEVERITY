# RoadScope: complete project viva guide

This guide describes the implemented project, not an idealized production system. Memorize the project story and important numbers, then practice explaining the decisions in your own words. Refer to code and evidence when asked for proof. Local Docker deployment was verified on 15 October 2026; that historical evidence does not guarantee containers are currently running.

## 1. Your opening answer

### A 30-second introduction

> RoadScope is a traffic accident severity analytics and MLOps project using Great Britain's public road collision, vehicle and casualty records for 2021–2025. It preserves the raw files, produces validated cleaned and analytical datasets, loads a SQLite warehouse and presents processed data in Streamlit. For Part 2, it trains a class-weighted Random Forest with chronological evaluation, tracks and registers it in MLflow, serves predictions through FastAPI, and deploys the dashboard and API using Docker Compose. A major source limitation is that the supplied external weather file is from Berlin, so I prevent invalid geographic enrichment rather than attaching unrelated weather to British collisions.

### A two-minute explanation

> I separated the work into data engineering, analytics and MLOps. First, ingestion copies the supplied public CSV files and records source names, local ingestion times, row counts and SHA-256 hashes. The ETL preserves staging snapshots, validates keys, dates, severity codes and coordinates, and retains rejected records with reasons. It produces a cleaned layer and a collision-grain mart. Vehicle and casualty rows are aggregated before joining, preventing double counting. The mart feeds a populated SQLite warehouse, dimensional lookups, aggregates, model-ready data and a Streamlit dashboard that reads processed Parquet only.
>
> The prediction target is collision severity: fatal, serious or slight. The model uses 12 contextual features and excludes outcome-related variables. I fit preprocessing only on training data, train on 2021–2023, select the model using 2024 and test on 2025. The selected Random Forest has 100 trees, depth 20, a minimum of 10 samples per leaf and balanced-subsample class weighting. Its test macro-F1 is 0.377, versus 0.283 for a majority-class baseline. Fatal recall is only 0.328, so it is a research prototype.
>
> MLflow records evaluation and registers the selected model. The full preprocessing/model pipeline is saved together. FastAPI validates requests and exposes predictions; Docker Compose runs it and the dashboard as healthy local services. Monitoring covers missing data, distribution drift, labeled performance, latency and failures. The Airflow DAG has three staged tasks but has not been executed under an Airflow scheduler. The external Berlin weather file cannot provide valid GB enrichment, and SQLite approval remains a course-specific consideration.

## 2. What problem are you actually solving?

There are two related tasks:

1. **Descriptive analytics:** when and where reported injury collisions occur, and how their recorded severity varies with conditions, vehicle involvement and casualty characteristics.
2. **Conditional severity classification:** given the context of a collision, predict whether its recorded severity is Fatal, Serious or Slight.

The model does **not** predict whether a collision will occur. All training examples are collision records; there are no representative non-collision examples or exposure denominators. You cannot turn these predictions into a population collision probability.

Similarly, a hotspot count is not an exposure-adjusted risk measure. A busy road can have more collisions because it carries more traffic. A higher severe share in one recorded condition is an association, not proof that the condition caused the outcome.

## 3. Numbers to memorize

### Source and cleaning counts

| Dataset | Raw rows | Accepted rows | Rejected rows |
|---|---:|---:|---:|
| Collisions | 513,801 | 513,748 | 53 |
| Vehicles | 937,265 | 937,164 | 101 |
| Casualties | 652,821 | 652,763 | 58 |
| Supplied hourly weather | 15,576 readings | 15,576 | 0 |

The 53 rejected collisions have invalid geographic coordinates. The rejected 101 vehicle and 58 casualty rows refer to collisions removed by that validation, so they become orphans relative to the accepted collision set. The rejected files retain reasons.

The accepted data spans **1 January 2021 to 31 December 2025**. There are **7,552 fatal collisions** in the full accepted dataset. A fatal collision count and a fatal casualty count are different quantities.

Current accepted child counts reconcile with reported collision totals: **zero vehicle-count mismatches and zero casualty-count mismatches**. Collision IDs are unique. There are no missing times in this particular accepted dataset, although the code handles unavailable times.

### Model split and evaluation

| Item | Actual value |
|---|---|
| Training years | 2021, 2022, 2023 |
| Available training rows | 311,298 |
| Training rows actually used | 150,000 |
| Validation year and rows | 2024; 100,927 |
| Test year and rows | 2025; 101,523 |
| Candidate tree depths | 12 and 20 |
| Selected depth | 20 |
| Test macro-F1 | 0.3773 |
| Majority-baseline macro-F1 | 0.2830 |
| Test balanced accuracy | 0.4455 |
| Test overall accuracy | 0.5874 |
| Fatal precision / recall / F1 | 0.0485 / 0.3276 / 0.0845 |
| Serious precision / recall / F1 | 0.3109 / 0.3300 / 0.3202 |
| Slight precision / recall / F1 | 0.7826 / 0.6790 / 0.7272 |

Do not describe 0.377 macro-F1 as 37.7% accuracy. These are different metrics.

## 4. Data sources and their limitations

The primary inputs are supplied Department for Transport collision, vehicle and casualty CSV files. The project ingests local copies; it does not claim that the DfT files were automatically downloaded from the website. The original download dates are unknown. The manifest timestamp records ingestion into this project.

The provided Open-Meteo CSV has station metadata, a blank separator, then timestamp and temperature columns. Its station is **52.54833°N, 13.407822°E**, which is Berlin. It has GMT/UTC metadata.

The collision data is from Great Britain. Matching only date/hour would incorrectly make British collisions inherit Berlin temperatures. Consequently, all current external-weather join results are unmatched by location. The original and processed weather series are retained and shown separately. Recorded DfT weather conditions still support the dashboard and model.

`src/weather.py` provides an optional GB historical-weather API extraction command with HTTP/error/status/row-count logging. Downloaded API JSON is archived raw; normalizing multiple suitable stations and integrating them into nationwide enrichment remains further work. Do not claim that this API extractor already completes the enrichment pipeline.

Source documentation is in `docs/sources.md`. OpenStreetMap-style basemap attribution does not mean that a road-network enrichment pipeline was implemented. Kaggle was not required because DfT was selected.

## 5. Architecture: explain this flow clearly

```text
Supplied DfT CSVs + supplied weather CSV
                   |
                   v
Raw copies + ingestion manifest + SHA-256 hashes
                   |
                   v
Staging snapshots -> validation -> rejected rows/reasons
                   |
                   v
Cleaned collision, vehicle, casualty and weather tables
                   |
         child aggregation + spatial/time weather gate
                   |
                   v
Processed collision mart + dimensions + aggregates
              /                 |                 \
             v                  v                  v
      SQLite warehouse   Streamlit dashboard  Model-ready data
                                                   |
                                chronological training/evaluation
                                                   |
                                 MLflow tracking and registration
                                                   |
                               saved preprocessing/model bundle
                                        /                 \
                                       v                   v
                            Streamlit -- POST /predict -> FastAPI
                                                           |
                                                Docker + telemetry
```

Airflow is the proposed scheduled orchestrator for ingestion, transform/load and persisted-output validation. It is not itself a database or model algorithm.

### Important implementation distinctions

- Streamlit reads **processed Parquet**, not raw CSV and not live SQLite queries.
- SQLite is a persisted analytical warehouse and supports SQL examination and submission evidence.
- The Streamlit prediction form sends **POST /predict** through `src/dashboard/api_client.py`. FastAPI loads the saved pipeline, returns probabilities and model version, and records telemetry. No local prediction fallback is used.
- FastAPI exposes the same saved model as a separately deployed service. It has its own inference validation and telemetry.
- Docker Compose starts runtime services. It does not automatically perform ETL or training.
- MLflow records experiments and versions. The deployed service currently loads a local file; it does not dynamically fetch an approved registry alias.

## 6. Why keep multiple data layers?

| Folder | Purpose |
|---|---|
| `data/raw` | Original byte-preserved inputs and manifest; reproducibility and audit |
| `data/staging` | Source-table snapshots before validation |
| `data/cleaned` | Validated records before collision-mart enrichment |
| `data/processed` | Dashboard/model-ready mart, lookups, aggregates and quality report |
| `data/rejected` | Rejected rows with explicit reasons |
| `data/warehouse` | Populated SQLite database |

This separates evidence from transformations and presentation. If cleaning rules change, the analytical layer can be rebuilt from the retained source. Raw data is not manually modified to make a dashboard look clean.

This is a folder-based, layered batch architecture. It is not a deployed Spark/Delta Lake platform merely because it resembles bronze/silver/gold concepts.

Raw copies are byte-preserved for the ingested inputs, but landing filenames are reused if a changed source is ingested. This is not immutable, append-only versioned raw storage. Historical ingestion versions would require timestamped/object-versioned landing paths and append-only manifests.

## 7. Walk through the ETL code

Read `src/pipeline.py` in this order:

1. **`digest`:** streams file blocks through SHA-256. The hash detects content changes and supports provenance; it is not data encryption.
2. **`ingest`:** copies the four supplied CSV files into raw storage, skips recopying identical content and records metadata. Errors are recorded and raised.
3. **`read_source`:** reads DfT CSVs with identifiers treated as strings. It uses Pandas; it does not perform distributed ingestion.
4. **`clean_collisions`:** parses and validates collision records, derives time features and maps source codes to readable labels.
5. **`clean_children`:** removes duplicate child keys, missing keys and references to rejected/missing parent collisions. Numeric -1 sentinels in non-key child fields become missing.
6. **`process_weather`:** parses metadata and the weather table, converts time/temperature, removes invalid/duplicate readings and writes cleaned/processed outputs.
7. **`enrich_weather`:** requires a suitable station distance and a corresponding UTC hour before attaching temperature.
8. **`transform`:** builds source layers, aggregates children, creates the collision mart, model-ready file, dimensions and aggregates, and loads SQLite.
9. **`validate_outputs`:** checks accepted/rejected reconciliation, key/grain invariants, SQLite integrity and aggregate totals.
10. **`main`:** exposes `all`, `ingest`, `transform` and `validate` CLI stages and logs unexpected failures.

### Collision validation and standardization

- Collision ID must be present and duplicate IDs are rejected after the first occurrence.
- Date uses explicit **DD/MM/YYYY**, avoiding ambiguous parsing of dates such as 03/10/2024.
- Parsed date year must match the reporting year.
- Target severity must be one of 1, 2 or 3.
- Coordinates must lie within the implemented broad GB screen: latitude 49–61, longitude -9–2.5.
- Counts below one are rejected. This is not a claim that every possible malformed numeric input is handled; the validation layer can be strengthened for arbitrary missing/non-numeric values and schema changes.
- Unknown -1 predictor codes become missing where configured. Unmapped display labels become Unknown.
- Speed-limit values are checked against the configured recognized set and are in mph.
- Invalid/missing event time is retained as unavailable rather than invented. Such rows are omitted from hourly views and can be imputed for model features.

The bounding box is not a precise country polygon. Road type is nominal: numerical source codes do not imply a meaningful order.

Analysis uses raw reported severity, not the supplied severity-adjustment fields. Reporting-system changes and release status should be checked before interpreting year-to-year differences as changes in road safety. The dataset covers reported injury collisions, not all collisions or every road user exposure.

### Why treat IDs as strings?

Identifiers are labels, not quantities. String types preserve formatting and avoid accidental numerical conversion. Arithmetic on collision IDs has no meaningful interpretation.

### Is the pipeline incremental or idempotent?

It is a **full batch refresh**. Unchanged raw files are not recopied, but transformations are recomputed. It is not CDC or an incremental merge system. Repeating a run on the same inputs/rules produces the same logical analytical records; ingestion timestamps naturally change.

The three large DfT sources are loaded into memory. SQL insertion uses batches of 5,000 rows, but CSV ingestion itself is not chunked. For much larger data, add chunked processing, partitioned Parquet, a query engine or a distributed framework based on actual scale requirements.

## 8. Keys, grain and avoiding double counting

**Grain means what one row represents.**

| Table | Grain | Logical key |
|---|---|---|
| Collision | One collision | `collision_index` |
| Vehicle | One involved vehicle | collision ID + vehicle reference |
| Casualty | One casualty | collision ID + casualty reference |
| Collision mart | One accepted collision | `collision_index` |

Suppose one collision has two vehicles and three casualties. Joining the collision directly to both child tables can produce **2 × 3 = 6 rows**. Summing collision totals over those rows would overstate counts.

The project instead aggregates each child table by collision ID first, then joins the one-row-per-collision aggregates using Pandas merge with **`validate='one_to_one'`**. Details remain available in separate child tables. The dashboard filters those children by selected collision IDs.

A casualty's own severity and the collision-level severity are distinct fields. The prediction target is `collision_severity`; casualty outcomes are not predictors.

## 9. Explain the weather join technically

1. Read station latitude and longitude.
2. Compute great-circle distance using the Haversine formula.
3. Require the station to be within **25 km** of the collision.
4. Interpret the collision's local timestamp using **Europe/London**.
5. Convert it to UTC, handling British daylight saving time.
6. Floor UTC time to the hour and look up the station temperature at that hour.
7. Attach temperature only when both spatial and time conditions pass.

Haversine distance is `2R × asin(sqrt(sin²(Δlat/2) + cos(lat1)cos(lat2)sin²(Δlon/2)))`, with Earth radius approximately 6,371 km and angles in radians.

DST-ambiguous/nonexistent times become unavailable for the weather match instead of being silently assigned the wrong UTC hour. The 25 km threshold is an engineering assumption, not proof that station weather represents each road. The current matcher expects a single-station table; a multi-station nearest-valid-observation strategy is future work.

**Answer to “Did you integrate the supplied weather?”**

> I ingested, cleaned and retained it, and implemented/tested a time-and-location matching gate. It has zero valid GB matches because it is from Berlin. I explicitly report that limitation. I use DfT-recorded weather for current condition analysis and model features, and I do not claim complete external enrichment.

## 10. Warehouse design and SQL

The database is **SQLite**, not PostgreSQL and not PostGIS. It is open source, embedded and convenient for a self-contained local demonstration. PostgreSQL/PostGIS is a stronger option for concurrency, larger deployment and spatial indexing; course approval of SQLite is still external.

Tables include `fact_collision`, `fact_vehicle`, `fact_casualty`, and dimensions `dim_date`, `dim_road`, `dim_weather`, `dim_location`, `dim_severity`. This is a star-schema-inspired analytical design, not a fully normalized dimensional system with every relationship enforced through SQL foreign-key constraints.

The location dimension contains observed district/highway/area combinations rather than a complete geocoded road network. Coordinates remain in the collision fact. SQL indexes support collision IDs, dates and child collision references. Parent-child validity is checked in ETL; do not claim the DDL enforces all foreign keys.

Aggregates are `agg_hour`, `agg_day`, `agg_weekday_number`, `agg_road`, `agg_weather`. There are 1,826 daily rows and date-dimension rows for the five-year period. The validator requires each aggregate's collision total to reconcile with 513,748 accepted collisions.

Example SQL to explain during viva:

```sql
SELECT severity, COUNT(*) AS collisions
FROM fact_collision
GROUP BY severity;

SELECT road, COUNT(*) AS collisions,
       100.0 * SUM(is_severe) / COUNT(*) AS severe_share_percent
FROM fact_collision
GROUP BY road
ORDER BY severe_share_percent DESC;

SELECT v.collision_index, COUNT(*) AS vehicles
FROM fact_vehicle AS v
GROUP BY v.collision_index;
```

SQLite is built as a temporary file, closed and then replaced after successful writes. Closing the connection is particularly important on Windows, where open file handles prevent replacement. The wider set of Parquet outputs is **not an atomic transactional snapshot**. Stop dashboard refresh during ETL; a stronger design would publish versioned output directories with a single pointer switch after validation.

## 11. Explain the dashboard

The seven tabs are:

1. **Overview:** collision/casualty totals, fatal collision count, fatal-plus-serious share, severity distribution and monthly trends.
2. **Time patterns:** hourly counts by severity and weekday × hour heatmap.
3. **Conditions:** severe shares by recorded weather, surface, lighting and road type; Berlin temperature is separate and labeled.
4. **Hotspots:** 0.02-degree coordinate cells, top 1,500 mapped cells and a top-20 table.
5. **Vehicles & casualties:** vehicle codes, driver age bands, casualty age/severity and casualty classes.
6. **Severity model:** held-out metrics, confusion matrix, scenario-input form and API-served predictions.
7. **Pipeline health:** accepted/rejected counts, reconciliation checks and weather compatibility information.

Filters include year, severity, area, road type and dates. Empty filters produce a clear no-data message. Model evaluation and pipeline-health information refer to the full dataset, not a model retrained on the filtered subset.

`st.cache_data` caches reads, with modification-time signatures used to invalidate cached data after files change. The application reads selected Parquet columns and aggregates age bands on the server, avoiding huge histogram payloads in the browser. Cache use does not make the application a real-time streaming platform.

Map cells are in degrees, so their physical size changes with latitude. The map needs external basemap tiles, whereas local Parquet analysis does not require a live data API.

## 12. Machine-learning formulation and all 12 features

Target encoding:

- 1 = Fatal
- 2 = Serious
- 3 = Slight

The problem is three-class supervised classification with class imbalance. Although severity has an intuitive order, this implementation uses a conventional multiclass classifier; it does not optimize an ordinal loss or explicitly assign different costs to every type of misclassification.

| Feature | Interpretation | Model branch |
|---|---|---|
| `hour` | Local event hour | Numeric |
| `month` | Calendar month | Numeric |
| `weekday_number` | Monday=0 through Sunday=6 | Numeric |
| `speed_limit` | mph | Numeric |
| `road_type` | Road type code | Categorical |
| `first_road_class` | Road classification code | Categorical |
| `light_conditions` | Recorded light conditions | Categorical |
| `weather_conditions` | Recorded weather | Categorical |
| `road_surface_conditions` | Recorded surface | Categorical |
| `urban_or_rural_area` | Area code | Categorical |
| `latitude` | Decimal degrees | Numeric |
| `longitude` | Decimal degrees | Numeric |

External temperature is **not** a feature. Hour/month/weekday are numeric in the current model, not sine/cosine cyclic encodings. A useful improvement is cyclic encoding or comparison with categorical representations of these fields.

### Leakage prevention

Do not use casualty severity, enhanced severity, adjusted severity, fatal casualty counts or other target-derived fields as predictors. Vehicle/casualty totals are also excluded from this feature allowlist. These fields remain useful for descriptive analytics.

Preprocessing is fitted on training data only. Computing medians or encoding categories from the combined train/test data would leak future information.

Even the approved contextual fields are not necessarily known before a collision. The model is conditional assessment, not a validated prospective road-warning system. The code minimizes obvious leakage but does not prove all data-collection biases are absent.

## 13. Preprocessing and model fitting

`ColumnTransformer` applies different processing to numeric and categorical columns.

- Numeric: `SimpleImputer(strategy='median', add_indicator=True)`.
- Categorical: most-frequent imputation followed by `OneHotEncoder(handle_unknown='ignore')`.
- Classifier: `RandomForestClassifier`.

The missing indicator can help the model learn whether availability itself carries information. Median imputation is relatively robust to extreme values. Most-frequent imputation is simple, but can hide informative missingness in categories; an explicit missing category is a possible alternative.

One-hot encoding avoids imposing a numerical order on nominal codes. Unknown categories at inference do not crash the encoder; they receive an all-zero pattern for that feature's encoded columns. That does not guarantee a reliable prediction for unfamiliar conditions, so drift monitoring still matters.

There is no standard scaler: decision-tree splits do not depend on feature magnitude in the way distance-based methods or gradient-descent models often do.

The complete preprocessing and model pipeline is saved in a joblib bundle alongside a timestamp version and feature list. Loading one bundle prevents forgetting or changing preprocessing during inference. Load only trusted model artifacts: pickle/joblib-style deserialization can execute code.

## 14. Why Random Forest and what do its parameters do?

A Random Forest averages predictions from many decision trees trained with bootstrap samples and feature randomness. Different trees can capture nonlinear interactions; averaging usually reduces variance compared with a single deep tree. It works well as a tabular baseline and does not require scaling.

The implementation uses:

| Parameter | Value | Explanation |
|---|---|---|
| `n_estimators` | 100 | Number of trees |
| `max_depth` | 12 or 20; selected 20 | Limits tree complexity |
| `min_samples_leaf` | 10 | Prevents tiny leaves and helps regularization |
| `class_weight` | `balanced_subsample` | Recomputes inverse-frequency weights within each bootstrap sample |
| `random_state` | 42 | Controls stochastic reproducibility |
| `n_jobs` | -1 | Uses available CPU cores |

Depth-12 validation macro-F1 was 0.3557; depth-20 was 0.3805. The selected model is the depth-20 candidate trained on the sampled training years. It was **not refitted on train+validation** after selection.

Only two depths were compared. Do not claim exhaustive hyperparameter optimization or that Random Forest was proven better than XGBoost/LightGBM; those alternatives were not compared in this implementation.

## 15. Splitting, sampling and imbalance

Chronological splitting mimics learning from earlier years and evaluating on a later year. A random split can make performance look more optimistic by mixing future and earlier reporting patterns.

The 311,298 eligible training records are proportionally sampled within severity classes to approximately cap training at 150,000 rows; the realized count is exactly 150,000. This retains the approximate class distribution and is done for laptop resources, not to balance the classes. All eligible validation and test rows are used.

Class balancing comes from `balanced_subsample` weights. These methods can increase attention to rare classes, but can also produce more false positives and do not guarantee good fatal recall. No SMOTE, oversampling pipeline or probability calibration was used.

The held-out test year is 2025. Do not tune repeatedly on its metrics and then still call it untouched. A future model-development cycle needs a suitable forward evaluation policy. Chronological splitting alone does not test transfer to entirely unseen geographical regions.

## 16. Metrics: explain formulas and business meaning

For a chosen class, treat it as positive versus all other classes:

- `Precision = TP / (TP + FP)`: of records predicted as that class, how many actually belong to it?
- `Recall = TP / (TP + FN)`: of actual records in that class, how many were found?
- `F1 = 2 × precision × recall / (precision + recall)`.
- `Macro-F1 = mean(F1_fatal, F1_serious, F1_slight)`: each class has equal weight.
- `Balanced accuracy = mean(per-class recalls)` for this multiclass problem.
- `Accuracy = correct predictions / all predictions`.

Accuracy can be misleading when most cases are slight. Always predicting the majority class gets about **73.8% test accuracy**, but zero recall for fatal and serious cases. The trained model has **58.7% accuracy**, which is lower, while its macro-F1 improves from **0.283 to 0.377**. Therefore say “better macro-F1 and minority-class detection,” not “better on every metric.”

Class-weighted decisions produce many false fatal predictions: fatal precision is only **4.85%**. Fatal recall is **32.76%**, meaning approximately two-thirds of actual fatal collisions are not classified as Fatal. This is a serious performance limitation, not a production-ready safety result.

### The actual test confusion matrix

Rows are actual, columns predicted:

| Actual \ Predicted | Fatal | Serious | Slight | Actual support |
|---|---:|---:|---:|---:|
| Fatal | 476 | 482 | 495 | 1,453 |
| Serious | 3,250 | 8,313 | 13,627 | 25,190 |
| Slight | 6,090 | 17,945 | 50,845 | 74,880 |

Explain the first row: of 1,453 actual fatal collisions, 476 were correctly predicted fatal, 482 predicted serious and 495 predicted slight. Fatal recall is `476/1453`.

There are two different false-negative questions:

1. **Fatal versus everything else:** fatal misses are 482+495. Fatal false-negative rate is about 67.2%.
2. **Severe (fatal+serious) versus slight:** severe misses are 495+13,627. Derived test severe false-negative rate is approximately **53.0%**: `14122 / 26643`.

The monitoring artifact's severe false-negative rate of about **47.6%** is from a different, full-data batch that includes training years. It is not the held-out test rate. Its macro-F1 of approximately 0.414 is likewise not an improved held-out result.

## 17. What MLflow actually does

Read `src/tracking.py`. It uses a local SQLite-backed tracking store, an experiment named `traffic-severity`, logs parameters, selected evaluation metrics and class recalls, stores the evaluation/confusion-matrix JSON artifact, and registers the model.

Verified registered model: **`traffic-severity`, version 1, READY**. The model bundle's timestamp version is **`20261013T081416Z`**. The MLflow run ID is **`b4830defedf24b96952eb26346a1d537`**. You need not memorize the long run ID; know where to retrieve it.

Do not confuse:

- Experiment: groups related runs.
- Run: one tracked execution, with parameters/metrics/artifacts.
- Artifact: saved output such as a model or evaluation JSON.
- Registry version: a numbered version under a registered model name.
- Bundle version: the project's timestamp identifier stored in the local joblib bundle.

Registration is not automatic promotion or deployment approval. `READY` indicates a registered artifact state, not sufficient predictive quality. The deployed API loads `models/severity.joblib`, not a dynamically resolved registry alias.

MLflow model logging uses explicit trusted types for the locally fitted Random Forest's dtype/tree containers. Do not accept arbitrary untrusted types or load unknown external serialized models blindly.

Tracking can be rerun without retraining via `python -m src.tracking`. Exported registry metadata can retain original-machine artifact URIs; after extraction, retrack the portable local bundle to establish artifact paths for that machine.

## 18. FastAPI inference and request validation

The app exposes:

- `GET /health`: reports readiness and loaded model version.
- `POST /predict`: accepts a scenario and returns severity, all class probabilities and model version.
- `/docs`: generated interactive API documentation.

Pydantic validates required fields and numeric ranges. Invalid request payloads return HTTP **422**. Missing model inference returns **503**. Inference failures return **500** with details retained in logs rather than a full internal exception returned to clients. Range validation is not exhaustive source-code validation: checking every discrete category against an allowed list would strengthen the API.

The model is loaded during application startup rather than retrained per request. Input is converted to a DataFrame with the shared feature allowlist and passed to `predict_proba`. The highest probability determines the class label. These probabilities sum to one but are **not calibrated**; they should not be interpreted as reliable real-world frequency estimates.

Example request:

```json
{
  "hour": 17, "month": 6, "weekday_number": 2,
  "speed_limit": 30, "road_type": 6, "first_road_class": 3,
  "light_conditions": 1, "weather_conditions": 1,
  "road_surface_conditions": 1, "urban_or_rural_area": 1,
  "latitude": 51.5, "longitude": -0.12
}
```

The verified Docker response for this scenario was Slight, with approximately Fatal 0.0864, Serious 0.3923 and Slight 0.5213. That is an example response, not a calibration claim.

Telemetry has two files: `predictions.jsonl` contains successful inference inputs/predicted class and prediction-path information; `service_requests.jsonl` records HTTP status and end-to-end latency, including validation errors and unavailable-model failures. Successful payload logs are not a substitute for all-request service monitoring.

## 19. Docker deployment: understand every part

An **image** is a packaged filesystem/runtime specification; a **container** is a running instance. A Dockerfile defines the image. Compose defines the multi-service application, commands, mounts, ports, restart policies and health checks.

This deployment has **one image** (`roadscope:local`) and **two containers**:

| Service | Purpose | Local URL |
|---|---|---|
| `roadscope-dashboard-1` | Streamlit and direct model inference | http://localhost:8501 |
| `roadscope-api-1` | Uvicorn/FastAPI inference | http://localhost:8000/docs |

The older host Streamlit URL on 8502 is separate. In viva, demonstrate the Docker service on **8501**.

### Dockerfile explanation

- `FROM python:3.13-slim`: base runtime matching the verified Python major/minor environment.
- `WORKDIR /opt/traffic`: consistent application directory.
- Environment variables disable Python bytecode writes and enable unbuffered logs; Streamlit usage statistics are disabled.
- `requirements-runtime.txt`: top-level runtime dependencies, omitting MLflow/training/test tooling from the served image.
- Dependency installation occurs before source copying so Docker can reuse that layer when only code changes.
- A non-root `traffic` user with UID/GID **10001** runs the service.
- Source, application and Streamlit config are copied; raw data, models, installed local packages and logs are excluded from the build context where configured.
- `EXPOSE` documents ports; **Compose `ports` actually publishes them**.
- Default command starts Streamlit; Compose overrides the API command to run Uvicorn.

### Mounts and ports

Processed data and model artifacts are read-only bind mounts. API logs are a writable host mount, so telemetry survives container replacement. The image does not contain the raw dataset or train a model when starting.

`127.0.0.1:8501:8501` means host loopback port 8501 forwards to the container's port 8501. Inside the container the server binds `0.0.0.0` so it is reachable through container networking; publishing only host loopback keeps this deployment local. It is not a cloud deployment, public API or Kubernetes cluster.

### Health and recovery

- Streamlit health uses `/_stcore/health` and expects `ok`.
- API health requires `/health` to return `status=ready`, not merely an HTTP response from an empty process.
- Interval 15 seconds, timeout 10 seconds, six retries, 40-second start period.
- `unless-stopped` restarts an exited container under Docker's restart policy. An unhealthy health check alone does not automatically restart a running container. Docker Desktop must itself be running.

Docker on this Windows machine uses its WSL Linux backend. Initially Docker cached a failure from before WSL was available; restarting Docker Desktop resolved that precondition check. No separate Ubuntu distribution was installed for this deployment.

### Evidence, not just configuration

The image was built; both containers were healthy; the browser displayed processed data; inference returned the evaluated version; probabilities were valid; invalid input returned 422. Evidence is in `docs/evidence/deployment`, including image IDs, container status, runtime package versions and a screenshot. The verified image was about 1.11 GB, shared by both services; it is not duplicated into the downloadable project ZIP.

## 20. Airflow: what is implemented and what is pending?

The DAG is **implemented**, but **scheduler/worker execution has not been demonstrated**. It contains:

```text
ingest_raw_sources
      -> transform_and_load_warehouse
             -> validate_persisted_outputs
```

It uses `BashOperator` to invoke the pipeline CLI from `/opt/traffic`, runs weekly, disables catchup, permits one active run, retries failed tasks twice with a five-minute delay. Two retries allow up to three attempts including the first.

A DAG is a directed acyclic graph: dependencies determine task ordering and cycles are disallowed. A scheduler decides when runs/tasks should be scheduled; workers/executors execute tasks. A retry is a new attempt after failure, not proof that duplicate writes cannot happen.

`catchup=False` avoids automatically creating all missed historical scheduled intervals. `max_active_runs=1` avoids overlapping DAG runs, but does not prevent someone separately launching a conflicting CLI process.

The API/dashboard image does not include Airflow. Deploy Airflow in its appropriate separate Linux/WSL worker environment and provide project/data mounts and dependencies. Do not claim the running Compose stack includes an Airflow service.

## 21. Monitoring and retraining

Monitoring is a **batch script plus request instrumentation**, not a live Prometheus/Grafana monitoring installation or an automatic retraining service.

The training run saves reference categorical frequencies, latitude bins and target frequencies. Current batches are compared with these references using total variation distance:

`TV(P,Q) = 0.5 × Σ |P(category) - Q(category)|`.

TV is zero for identical discrete distributions and one for fully disjoint distributions. Categorical drift, latitude-distribution drift and labeled target drift are monitored. Geographic drift currently examines **latitude bins only**; it can miss east–west changes, so longitude/2D-region monitoring is an improvement.

- Data drift: input distributions change.
- Class/prior drift: class frequencies change; requires outcomes to observe directly.
- Concept drift: the relationship between features and target changes. Input drift alone does not prove or fully detect concept drift.
- Performance degradation: evaluated quality worsens on newly labeled data.

Missing fractions describe input availability. Macro-F1, class recalls and severe false-negative rate require labels. Without labels, the code does not invent these performance measures. Delayed outcomes mean performance monitoring can lag behind service activity.

Review thresholds are categorical/latitude TV >0.15, class TV >0.10, severe FN >0.40, fatal recall <0.40, feature missingness >0.20, service failure fraction >0.05 or p95 latency >1,000 ms. These are initial heuristics, not statistically calibrated alerts or a measured production SLA.

The saved example monitoring report uses all 513,748 records, including training years. It reports severe FN about 47.6% and triggers review. Its small service sample includes an intentionally invalid request, so a 50% failure figure reflects a test sample, not demonstrated production unreliability. Validation errors and server-side failures should be separated in a mature dashboard even though the current health summary counts both as failed requests.

Retraining review is not automatic retraining. A responsible lifecycle validates new data/labels, trains a candidate, compares performance, registers it and requires acceptance before promotion. Current training writes the latest local model file automatically; do not train directly onto a production mount. Stage an approved artifact, switch it deliberately and restart services. Retain a previous evaluated bundle for rollback.

## 22. Testing and quality evidence

Eight project tests passed in the recorded audit. Coverage includes duplicate/invalid-coordinate handling, date parsing, unavailable time, orphan/duplicate child keys, spatial and UTC-hour weather matching, API inference/validation, HTTP validation-error telemetry, monitoring TV behavior, unlabeled monitoring behavior and Streamlit render/filter behavior. Multiple assertions can belong to one test.

Nine persisted-artifact checks passed: expected files, raw checksums, accepted/rejected reconciliation, database integrity, dimensions, aggregates, aggregate reconciliation, evaluation-data hash consistency and registry readiness.

The separate Docker verifier checks actual running containers and HTTP requests. Unit tests alone would not prove that the Docker image builds, host ports work or model mounts are readable. Health checks alone would not prove the dashboard data view renders, which is why the browser check matters.

This is not exhaustive testing. There is no demonstrated high-load test, failover test, real-time monitoring deployment or complete schema-evolution coverage. Avoid claiming comprehensive production validation.

## 23. File-by-file oral explanation

| File | What to say |
|---|---|
| `src/config.py` | Central paths, code mappings, source filenames and feature allowlist |
| `src/pipeline.py` | Repeatable ingestion, validation, layers, joins, warehouse, aggregates and output checks |
| `src/weather.py` | Optional API extraction and provenance/error logging; integration still pending |
| `src/train.py` | Chronological sampling/training, parameter comparison and test evaluation |
| `src/tracking.py` | MLflow run metrics/artifacts and registered model versions |
| `src/api.py` | Model loading, request validation, inference, readiness and telemetry |
| `src/monitor.py` | Reference comparisons, labeled performance, service summaries and review alerts |
| `app.py` | Small entry point that invokes the modular dashboard application |
| `src/dashboard/application.py` | Composes shared layout, filters and page renderers |
| `src/dashboard/pages/` | One renderer module for each dashboard tab |
| `src/dashboard/data.py` | Cached processed Parquet and evaluation JSON access |
| `src/dashboard/api_client.py` | HTTP requests from the prediction form to FastAPI |
| `src/dashboard/filters.py` | Shared sidebar controls and pure filtering function |
| `src/dashboard/charts.py`, `layout.py`, `theme.py` | Reusable chart styling, summary/header components and page appearance |
| `dags/traffic_etl.py` | Weekly staged Airflow definition, not a running scheduler |
| `Dockerfile` | Runtime image construction and non-root execution |
| `compose.yaml` | Two service instances, mounts, host ports, health and restart policies |
| `scripts/verify_deployment.py` | Actual Docker/HTTP deployment evidence |
| `scripts/audit_project.py` | Persisted-artifact checks and remaining requirements |
| `scripts/package_project.py` | ZIP packaging with installed dependencies/caches excluded |
| `docs/requirements_audit.md` | Detailed assignment coverage and unresolved requirements |

## 24. A practical 8–10-minute viva demonstration

1. Give the 30-second introduction and show the architecture diagram.
2. Show the raw manifest and explain one checksum, timestamp and row count.
3. Show a rejected row and the quality report. Explain 513,801 = 513,748 + 53.
4. Show the `cleaned`, `processed` and warehouse folders; explain the collision grain and double-counting example.
5. Open Docker dashboard port 8501. Change one filter and explain the counts, then reset it. Show the time, conditions and people views.
6. Explain why Berlin weather is separate and why hotspot counts are not risk estimates.
7. Show temporal split, macro-F1, fatal recall and the test confusion matrix. Acknowledge weak fatal precision/recall.
8. Show MLflow run/registry evidence and the saved pipeline bundle.
9. Run `docker compose ps` and show both services healthy. Open API `/docs`, submit the example request, and point out the version/probabilities.
10. Show monitoring results and the Airflow DAG source. Distinguish deployed Docker from unexecuted Airflow scheduling.

Do not rerun the full ETL during a short live demonstration unless explicitly asked: it can take time and the multi-file processed refresh is not atomic. Use the successful run evidence and demonstrate persisted validation instead. Likewise avoid a full retraining run unless required.

Useful commands from the project directory:

```powershell
docker compose ps
python scripts/verify_deployment.py
python -m src.pipeline --stage validate
python -m pytest -q
docker compose logs --tail 30 api
```

Commands for rebuilding/retraining, when requested and after stopping conflicting readers:

```powershell
python -m src.pipeline --source data/raw
python -m src.train --mlflow
python -m src.monitor --batch data/processed/model_ready.parquet
docker compose up --build -d --wait --wait-timeout 180
```

## 25. Likely viva questions and concise answers

**1. What is novel about the project?** The value is the integrated, reproducible engineering workflow: traceable raw inputs, validated collision-grain analytics, explicit weather-quality gates, chronological modeling and verified containerized serving. I do not claim a novel ML algorithm.

**2. Why not use Excel for everything?** The source tables contain hundreds of thousands of related records. Scripted ETL provides repeatability, key validation, joins, reject logs and model/serving integration; the dashboard provides interactive exploration.

**3. Why keep raw files?** To preserve evidence, reproduce transformations, audit decisions and recover when rules change.

**4. Why Parquet rather than only CSV?** Typed columnar storage, compression and selective column reading suit repeated analytics. CSV remains useful as the supplied interchange format and for small exports.

**5. Why retain rejected records?** Deleting without reasons hides data-quality problems. Rejected rows support reconciliation and later review.

**6. Why not fill every missing value immediately?** Analytics and modeling have different requirements. Preserve meaningful unknowns in data layers; fit model imputation on training data only.

**7. What is the most dangerous join mistake?** Joining raw vehicle and casualty detail simultaneously can multiply rows and overstate collision metrics. Aggregate to the common collision grain first.

**8. Is the warehouse fully normalized?** No. It is an analytical fact/lookup design with a denormalized mart, and not every relationship is enforced by SQL foreign keys.

**9. Why SQLite?** A portable local analytical database with minimal setup. It is a practical alternative, but instructor approval and any PostgreSQL/PostGIS requirement must be addressed.

**10. Did you use a real weather API?** An optional requests-based extractor is implemented. The delivered analytical run uses the supplied CSV; valid nationwide API enrichment is not claimed.

**11. What if two stations are nearby?** The current matcher expects one station table. A multi-station extension should select an eligible nearest observation with explicit distance/time/source rules and track coverage.

**12. Why UTC?** It supplies a common time basis for station and event matching; British daylight saving offsets must be accounted for.

**13. Why not a random split?** Time-based evaluation is closer to using historical releases to predict a later release and avoids mixing future records into earlier training periods.

**14. Is the 150,000-row sample balanced?** No. It is sampled proportionally by class to fit resource limits. Class weights address imbalance.

**15. Why one-hot encode road types?** Codes represent categories, not continuous numerical magnitude. Encoding avoids artificial ordinal meaning.

**16. Why no feature scaling?** This classifier uses tree splits, so a common scale is unnecessary in the way it is for many distance-based models.

**17. Why not deep learning?** Random Forest is a reasonable tabular baseline with manageable CPU resources. No evidence here proves deep learning would be worse; it was not compared.

**18. Can Random Forest overfit?** Yes. Depth/leaf constraints and held-out validation help, but do not eliminate overfitting or distribution shift.

**19. How did you select the final model?** Validation macro-F1 compared depths 12 and 20; depth 20 won. I then evaluated that selected candidate on the later test year.

**20. Does a high accuracy imply good fatal detection?** No. The majority slight class can dominate accuracy. I report class recalls, precision, macro-F1 and the confusion matrix.

**21. Is your model better than baseline?** On macro-F1 and fatal/serious recall, yes; overall accuracy is lower. The comparison is metric-specific.

**22. Why is fatal precision so low?** Fatal events are rare and contextual features have limited discriminatory power; class weighting encourages more fatal predictions, producing many false positives. More rigorous feature/model/calibration work is needed.

**23. Why not use number of casualties?** It is an observed event outcome that may reveal severity and may not be available at the intended inference moment. It is excluded from the explicit allowlist.

**24. Are the probabilities trustworthy?** They are model outputs normalized across classes, not calibrated outcome frequencies. Calibration should be assessed on separate validation data.

**25. How is the model deployed?** Its complete pipeline is mounted read-only into a non-root FastAPI container, loaded at startup and served over a local port. Compose also runs the dashboard container.

**26. Does Streamlit call FastAPI?** Yes. The prediction form sends JSON to `/predict` through `dashboard/api_client.py`. Local runs use `http://127.0.0.1:8000`; Docker uses `http://api:8000`. The API validates input, applies preprocessing and the model, and returns severity probabilities and model version. API failures appear in the UI.

**27. What does MLflow add beyond a joblib file?** Organized experiments, parameters, metrics, artifacts and registered versions that connect an evaluation to a model. A joblib file alone does not record the full experimental context.

**28. Does registration automatically approve deployment?** No. Registry readiness is not a quality or governance approval; the current runtime uses the selected local artifact.

**29. Why two containers but one image?** Both services need the same runtime libraries and source. Different startup commands provide separate processes/services while sharing the image layers.

**30. Does EXPOSE publish a port?** No. Compose port mappings publish it; EXPOSE is image metadata/documentation.

**31. Why non-root?** It limits the service process's privileges. It is one operational measure, not complete production security.

**32. Why mount models read-only?** Inference should not overwrite the evaluated model. Deliberate promotion occurs outside the running inference process.

**33. Does unhealthy automatically cause restart?** Not with plain Docker health checks alone. The restart policy applies when the process exits; an orchestrator or additional supervisor would be needed for health-driven recovery.

**34. Why Docker on Windows needs WSL here?** This deployment uses Linux containers through Docker Desktop's WSL backend. The application itself is packaged for Linux runtime.

**35. Have you deployed Airflow?** The staged DAG is written; the scheduler/worker has not been run. The ETL has been executed successfully from the CLI.

**36. What happens if a DAG task fails?** Airflow can retry twice after five-minute delays. Downstream tasks wait for upstream success. The ETL's batch replacement behavior helps repeatability, but the whole output directory is not transactional.

**37. What is data drift versus concept drift?** Data drift changes input distributions; concept drift changes the feature-to-target relationship. Our frequency checks do not prove concept drift is absent.

**38. Can you monitor recall without labels?** No. Input drift and service health are available sooner; recall and false negatives require observed outcomes.

**39. Why did monitoring raise a service alert?** The example request sample is tiny and includes an intentionally invalid request. That test artifact is not a production reliability estimate.

**40. What triggers retraining?** The script flags review thresholds. A person must investigate data quality and labels, then train/evaluate a candidate; automatic promotion is not implemented.

**41. What would you improve first?** Obtain compatible GB weather; improve rare-severity detection and calibration; use fresh labeled monitoring data; demonstrate Airflow scheduling; evaluate geography transfer and strengthen atomic publication/promotion.

**42. Is this real-time?** No. ETL and monitoring are batch workflows. The prediction endpoint responds to requests, but the underlying data pipeline is not streaming.

**43. Is it production-ready?** No. Local serving and container checks pass, but model quality, prospective validation, operational monitoring, deployment resilience and governance need further work.

**44. What exactly did the Docker verifier prove?** Two healthy running containers, working host access, correct evaluated model version, normalized predictions and HTTP 422 for invalid data at the recorded time.

**45. What does a passing test not prove?** It does not guarantee future uptime, correctness on all malformed inputs, high-load performance, generalization to new populations or absence of all leakage/bias.

## 26. Claims to avoid

Do not say: “I predicted accident occurrence,” “Berlin weather was merged successfully,” “I used PostGIS,” “Airflow is running,” “the model is 90% accurate,” “the model beats baseline on accuracy,” “MLflow automatically promotes models,” “monitoring automatically retrains,” “health checks restart unhealthy containers,” “the warehouse is read live by Streamlit,” or “all course requirements are complete.” Those statements do not describe the current code/evidence.

Instead distinguish what was **implemented**, **executed locally**, **verified**, and **still pending**. If asked about a missing feature, explain the current behavior, its limitation and a concrete next step.

## 27. Your final revision checklist

- Can you explain the entire data flow without reading the screen?
- Can you distinguish collision, vehicle and casualty grain and show the 2×3 join problem?
- Can you defend the weather mismatch and UTC/distance gate?
- Can you list all 12 features and identify leakage-prone fields?
- Can you explain chronological splitting, sampling and class weighting separately?
- Can you calculate fatal recall from the first confusion-matrix row?
- Can you explain why accuracy is lower than the majority baseline while macro-F1 is higher?
- Can you distinguish 47.6% monitoring severe FN from approximately 53.0% held-out severe FN?
- Can you explain Streamlit's HTTP prediction request, FastAPI serving, MLflow registration and Airflow scheduling?
- Can you show real Docker containers and historical verification evidence?
- Can you explain why raw files and read-only inference mounts are retained?
- Can you state the unfinished requirements honestly?

Study source files alongside this guide. You should be able to explain the implementation in your own words and acknowledge assistance and any reused material according to your course rules.
