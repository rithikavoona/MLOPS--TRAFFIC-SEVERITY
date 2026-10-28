"""Generate a nine-page project report from actual run artifacts (bundled Python)."""
import json
import sqlite3
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
quality = json.loads((ROOT / 'data/processed/quality_report.json').read_text())
metrics = json.loads((ROOT / 'models/metrics.json').read_text())
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=11, leading=17, spaceAfter=14, textColor=colors.HexColor('#24334c')))
styles['Title'].textColor = colors.HexColor('#103354')
styles['Heading1'].textColor = colors.HexColor('#103354')
story = []


def p(text):
    story.append(Paragraph(text, styles['Body']))


def heading(text):
    story.append(Paragraph(text, styles['Heading1']))
    story.append(Spacer(1, 18))


def table(rows):
    rendered = [[Paragraph(escape(str(cell)), styles['Body']) for cell in row] for row in rows]
    item = Table(rendered, hAlign='LEFT', repeatRows=1)
    item.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#deebf5')), ('VALIGN',(0,0),(-1,-1),'TOP'), ('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#3882a8')), ('BOTTOMPADDING',(0,0),(-1,-1),9), ('TOPPADDING',(0,0),(-1,-1),9)]))
    story.append(item)


heading('RoadScope')
story.append(Paragraph('Traffic Accident Severity<br/>Analytics and Prediction', styles['Title']))
story.append(Spacer(1, 30))
p('Data Engineering and MLOps project report | Updated 15 October 2026')
p('The project turns the supplied Department for Transport collision, vehicle and casualty files into validated analytical data, a populated SQLite warehouse and an interactive Streamlit application. It also provides a reproducible Random Forest training pipeline, FastAPI inference service, experiment tracking integration and monitoring scripts.')
p(f'The successful full ETL retained {quality["collision"]["clean"]:,} collision records for 2021-2025, {quality["vehicle"]["clean"]:,} linked vehicles and {quality["casualty"]["clean"]:,} linked casualties. Raw files remain unchanged and processed tables drive every dashboard view.')
p('A material source limitation is handled explicitly: the supplied temperature series belongs to Berlin. It cannot be spatially joined to Great Britain collision records. Its processed series is retained independently, and external temperature remains missing in the collision mart.')
p('This report records implemented behavior and observed results. The Docker image was built and both dashboard and FastAPI containers were deployed locally on 15 October 2026. Health, model-version, prediction and invalid-input checks passed. The Airflow scheduler has not been launched. The current model remains a research prototype.')
story.append(PageBreak())
heading('1. Problem, scope and sources')
p('The analytical problem is to describe injury collision severity by time, location, road conditions, vehicles and casualties. The prediction problem is conditional severity classification once a collision has occurred; the project does not estimate the probability that a collision will occur.')
p('The assignment brief describes an analytics implementation followed by an MLOps extension. This implementation supplies both source-code layers, with the local analytical pipeline and model evaluation executed against the provided files. Streamlit is selected because it supports interactive filtering, model scenarios and data-quality visibility.')
table([['Source','Raw rows'], ['DfT collisions',quality['collision']['raw']], ['DfT vehicles',quality['vehicle']['raw']], ['DfT casualties',quality['casualty']['raw']], ['Open-Meteo temperature',quality['weather']['clean']]])
p('DfT source and access: https://www.gov.uk/government/statistical-data-sets/road-safety-open-data . Download the five-year collision, vehicle and casualty CSV files and the release-specific data guide. Original download dates are unknown; the manifest records local ingestion dates.')
p('Open-Meteo documentation: https://open-meteo.com/en/docs/historical-weather-api . The provided export has a metadata header, a blank separator and an hourly UTC temperature table. The project has an optional archive API extraction CLI for compatible GB stations.')
p('Source severity is unadjusted reported severity. Adjustment fields are retained for provenance but excluded from prediction. Changes in injury reporting and publication status must be considered before making trend comparisons.')
story.append(PageBreak())
heading('2. Architecture and orchestration')
p('Source CSVs -> raw landing zone -> typed staging -> validation and rejection logs -> cleaned facts and collision mart -> SQLite warehouse / processed Parquet -> Streamlit. Model-ready processed features feed chronological training, versioned inference bundles and monitoring.')
p('The architecture diagram is supplied in docs/architecture.md as Mermaid. A collision is the analytical grain. Vehicle and casualty records have distinct child keys and are aggregated before joining, preventing multiplication of collision totals in many-to-many joins.')
p('The pipeline CLI is repeatable. Ingestion copies files byte-for-byte, records hashes and skips recopying identical inputs. Every transformation can be reproduced from raw files. A fresh temporary SQLite database is closed and replaced only after successful writes.')
p('The weekly Airflow 2.x DAG separates ingestion, transformation/warehouse loading and persisted-output validation into three tasks. It uses two retries, five-minute retry delay, disabled catchup and a single active run. It assumes a Linux worker with the project mounted at /opt/traffic. The same staged CLI is repeatable locally; the scheduler has not been launched.')
p('SQLite is the implemented open-source local warehouse. It supports populated tables and indexed identifiers with no credential requirements. PostgreSQL/PostGIS is a future deployment option rather than a claimed installed service. Ask the instructor whether this database alternative is acceptable.')
p('Processed Parquet outputs are not a transactional multi-file snapshot. Dashboard and ETL refresh should not run concurrently. Stop the dashboard, execute ETL and restart after success. Schedule retraining separately and review the new version before promoting it.')
story.append(PageBreak())
heading('3. Preprocessing and validation')
p('Dates are parsed explicitly as DD/MM/YYYY; year consistency is checked. IDs remain strings. Duplicated collision IDs, invalid dates, unsupported target labels, invalid counts and out-of-bounds GB coordinates are rejected with explicit reasons. Unknown time does not remove an otherwise valid collision or manufacture an event hour.')
p('The GB bounding-box screen is 49-61 degrees north and -9 to 2.5 degrees longitude. This is a broad geographic validation, not a country polygon. Source road, weather, lighting, surface and urban/rural codes receive readable labels. Numeric -1 sentinels become missing for selected predictors and non-key child fields.')
p('Vehicle keys use collision ID and vehicle reference. Casualty keys use collision ID and casualty reference. Duplicate child keys, missing keys and orphan collision references are rejected. Cleaned child counts are compared with reported collision counts.')
table([['Layer','Raw','Clean','Rejected'], *[[name.title(),quality[name]['raw'],quality[name]['clean'],quality[name]['rejected']] for name in ['collision','vehicle','casualty']]])
p('All 53 rejected collisions had invalid coordinates. Their associated 101 vehicle rows and 58 casualty rows were rejected as orphan records after collision screening. Unique IDs and mart row-count preservation passed. Vehicle and casualty count mismatches were both zero.')
p('The rejection CSVs retain the original row values and reason text. Unexpected failures are written to logs/pipeline.log; ingestion failure status is retained in the manifest. Data dictionary and field-level validation rules are in docs/data_dictionary.md.')
story.append(PageBreak())
heading('4. Weather and analytical storage')
p('Correct enrichment requires both geographic and temporal alignment. The implemented matcher applies a 25 km station-distance gate and an exact UTC-hour lookup. GB event times are localized with Europe/London and converted to UTC; DST-ambiguous or nonexistent times remain unmatched.')
p('The supplied station is 52.54833 N, 13.407822 E, elevation 38 m, timezone GMT. Its 15,576 hourly readings do not match GB collision locations. External temperature values therefore remain missing, with unmatched_location status, and the quality report records zero matches. The separate Berlin series can be viewed without implying an accident relationship.')
p('The dashboard condition analysis uses recorded DfT weather, road surface and lighting fields. Missing external temperature is not replaced by Berlin readings. The supplied files cannot complete a geographically valid external weather enrichment requirement; compatible GB observations must be acquired and normalized first.')
p('SQLite tables include fact_collision, fact_vehicle, fact_casualty, dim_date, dim_road, dim_weather, dim_severity and dim_location. Aggregate tables summarize collisions, severe collisions and casualties by hour, weekday, road type and weather condition. Facts retain source codes and IDs for traceability.')
p('The location dimension is an observed district/highway/area lookup. Coordinates remain in the collision fact; this is not a geospatial road network database. Date and severity dimensions have stable source-derived keys, while road and weather use DfT codes.')
p('Raw, staging, cleaned and analytical layers are explicit folders. Validated collision, vehicle, casualty and weather records are retained in data/cleaned before mart enrichment. Aggregates now include calendar day as well as hour, weekday, road and weather. The model-ready file contains dates, target and an explicit predictor allowlist. Streamlit reads only processed artifacts.')
story.append(PageBreak())
heading('5. Dashboard design and interpretation')
p('The Streamlit application has seven tabs: overview, time patterns, conditions, hotspots, vehicles and casualties, severity model and pipeline health. The dark visual theme uses blue for slight severity, amber for serious and rose for fatal records, with separate metric cards and labeled charts.')
p('Year, collision severity, area, road type and date-window filters apply to analytical views and linked child rows. Empty selections produce a clear no-data state. The model and quality sections describe the complete dataset rather than pretending filtered metrics change training results.')
p('The overview presents collision totals, casualty totals, fatal collisions and fatal-plus-serious share, a severity donut and monthly trends. Time patterns include an hourly severity chart and weekday-by-hour heatmap. Condition views show severe shares with group counts so users can see small-denominator categories.')
p('Hotspots aggregate rounded 0.02-degree coordinate cells, show the top 1,500 cells and provide a top-20 table. Cell area varies by latitude. These are collision concentrations, not exposure-adjusted road risk. Online map tiles may require internet access.')
p('Vehicle and casualty analyses show DfT vehicle type codes, aggregated five-year age bands, casualty severity by age and casualty class. Only cleaned child rows attached to the filtered collision IDs enter these charts. Age histograms are pre-aggregated server-side to reduce browser payload.')
p('The prediction form accepts only approved model features. Evaluation displays macro-F1, balanced accuracy, fatal recall and the confusion matrix. Pipeline health shows accepted/rejected counts, reconciliation checks, extraction time and the weather mismatch.')
p('Counts describe reported injury collisions. Without traffic volume, road length or population denominators, shares and hotspots do not demonstrate causal effects or population-level accident rates.')
story.append(PageBreak())
heading('6. Model development and evaluation')
p(f'Training uses years {metrics["train_years"]}; validation uses {metrics["validation_year"]}; testing uses {metrics["test_year"]}. Of {metrics["train_rows_available"]:,} training records, {metrics["train_rows_used"]:,} are proportionally sampled by target class for laptop operation. Validation and testing use all {metrics["validation_rows"]:,} and {metrics["test_rows"]:,} eligible records respectively.')
p('Numeric predictors use training-fitted median imputation and missing indicators. Categorical predictors use most-frequent imputation and one-hot encoding with unknown-category handling. A class-weighted Random Forest has 100 trees, minimum leaf size 10, fixed random seed 42 and candidate depths 12 and 20. Depth is selected by validation macro-F1.')
p('Predictors include hour, month, weekday, speed limit, road class/type, recorded weather, surface, lighting, area and coordinates. Vehicle/casualty totals, casualty severity, adjusted severity and enhanced severity are excluded to limit outcome leakage. Current weather and lighting information may itself be unavailable before an incident, so the use case remains conditional assessment.')
table([['Held-out metric','Value'], ['Macro F1',f'{metrics["macro_f1"]:.4f}'], ['Balanced accuracy',f'{metrics["balanced_accuracy"]:.4f}'], ['Majority baseline macro F1',f'{metrics["baseline_macro_f1"]:.4f}'], ['Fatal recall',f'{metrics["report"]["Fatal"]["recall"]:.4f}'], ['Serious recall',f'{metrics["report"]["Serious"]["recall"]:.4f}'], ['Slight recall',f'{metrics["report"]["Slight"]["recall"]:.4f}']])
p('The model improves macro-F1 over the majority baseline, but fatal precision and recall remain low. Predicted probabilities are uncalibrated. This evaluation does not justify operational safety use. Hyperparameter search, richer prospective features, calibration and geographical robustness evaluation remain useful next steps.')
story.append(PageBreak())
heading('7. Serving, tracking and monitoring')
p('The persisted joblib bundle contains the full preprocessing/model pipeline, version ID and feature list. A timestamped artifact supports local version history, and severity.joblib is the file consumed by the API and Streamlit. Only trusted locally generated model artifacts should be loaded.')
p('The optional --mlflow mode tracks experiment parameters, macro-F1, balanced accuracy, the majority baseline, each class recall and the evaluation/confusion-matrix artifact, and registers traffic-severity. Tracking is backed by a local SQLite database. MLflow status is recorded explicitly in metrics.json. The existing evaluated model was successfully tracked and registered as traffic-severity version 1 during local verification; src.tracking can repeat registration without retraining.')
p('FastAPI exposes /health, /predict and interactive /docs. Pydantic validates input ranges and predictions return all class probabilities with model version. HTTP middleware records latency and status for all prediction requests, including validation errors, unavailable models and inference failures. Payload prediction logs remain separate from request-health logs.')
p('The Python 3.13 Docker image was built and deployed with Compose. Both services run as a non-root user with health checks and localhost-only host ports. Processed data and models are mounted read-only; API logs are writable. Streamlit health, evaluated model-version consistency, a valid prediction and HTTP 422 rejection passed. Image IDs and results are recorded in docs/evidence/deployment/docker_verification.json.')
p('Batch monitoring reports missing-data fractions, categorical total-variation distance, latitude-distribution drift and class-distribution drift when labels are available. Severe false negatives are measurable only with observed severity. Service logs support failure-rate and p95-latency summaries.')
p('Review thresholds are categorical/location drift >0.15, class drift >0.10, severe false-negative rate >0.40, fatal recall <0.40, feature missingness >0.20, failure rate >0.05 or p95 latency >1,000 ms. These are engineering heuristics, not calibrated alarms. They trigger review rather than automatic deployment. The lifecycle document defines promotion, retraining and rollback.')
story.append(PageBreak())
heading('8. Reproduction, evidence and limitations')
p('From the project directory: install requirements, run python -m src.pipeline --source followed by the supplied CSV folder, then python -m streamlit run app.py. The dashboard can use the included processed artifacts immediately. Run python -m src.train --mlflow for tracked training and python -m uvicorn src.api:app for inference.')
p(f'The recorded successful ETL completed at {escape(quality["completed_at_utc"])}. The analytical date range is 1 January 2021 through 31 December 2025. The manifest fingerprints every raw source and reconciles source row counts; the quality report confirms unique collision IDs, collision-grain preservation and zero linked child-count mismatches.')
p('Evidence files are logs/pipeline.log, data/raw/manifest.json, data/processed/quality_report.json, models/metrics.json and models/monitoring.json. Unit tests exercise duplicate/orphan handling, date parsing, invalid coordinates, unknown time, spatial/UTC weather matching and API validation. Streamlit integration tests check rendering and the empty-filter state. Test output is retained in logs/tests_verified.log when run during validation.')
p('The original assignment brief and source datasets are preserved. The code is organized by responsibility, with explicit feature and category configuration. The student should review the implementation, explain its choices and adapt the report to course-specific submission requirements.')
p('Material limitations: no compatible nationwide external weather data; raw reported rather than adjusted severity; bounding-box geographic validation; SQLite instead of PostGIS; no live scheduled Airflow runtime; partial model training sample; limited hyperparameter search; uncalibrated probabilities; no exposure denominator; and a nontransactional multi-file processed refresh.')
p('The local ETL, populated warehouse, dashboard, model and Docker-hosted inference service are demonstrated. The container deployment is local, not publicly hosted. Airflow remains a supplied scheduling definition without runtime evidence. External weather integration needs compatible observations if the instructor requires nonzero matches. The deployment guide documents repeatable start, stop and verification commands.')


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#bed3e4'))
    canvas.line(42, 40, A4[0]-42, 40)
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#57718a'))
    canvas.drawString(42, 26, 'RoadScope | Data Engineering and MLOps')
    canvas.drawRightString(A4[0]-42, 26, str(doc.page))


output = ROOT / 'docs/reports/project_report.pdf'
output.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(output), pagesize=A4, leftMargin=42, rightMargin=42, topMargin=48, bottomMargin=58).build(story, onFirstPage=footer, onLaterPages=footer)
print(output)
