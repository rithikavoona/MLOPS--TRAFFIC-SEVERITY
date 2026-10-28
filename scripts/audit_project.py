"""Verify persisted deliverables and report environmental/data compliance gaps."""
import hashlib
import importlib.util
import importlib.metadata
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / '.deps').exists():
    sys.path.append(str(ROOT / '.deps'))


def sha256(path):
    checksum = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


required = ['app.py', 'README.md', 'requirements.txt', 'Dockerfile', 'compose.yaml', '.dockerignore', 'dags/traffic_etl.py', 'docs/reference/assignment_brief.pdf', 'docs/reports/project_report.pdf', 'docs/requirements_audit.md', 'docs/project_structure.md', 'docs/architecture.md', 'docs/data_dictionary.md', 'docs/model_lifecycle.md', 'docs/sources.md', 'docs/evidence/screenshots/dashboard_overview.png', 'docs/evidence/schema/warehouse_schema.sql', 'models/severity.joblib', 'models/metrics.json', 'models/monitoring.json', 'data/processed/model_ready.parquet', 'data/processed/collision_mart.parquet']
required += [f'data/cleaned/{name}.parquet' for name in ['collision','vehicle','casualty','weather']]
required += [f'src/dashboard/{name}.py' for name in ['application','context','data','filters','charts','layout','theme']]
required += [f'src/dashboard/pages/{name}.py' for name in ['overview','time_patterns','conditions','hotspots','vehicles_casualties','severity_model','pipeline_health']]
checks = {'required_files_present': all((ROOT / name).is_file() for name in required)}
missing = [name for name in required if not (ROOT / name).is_file()]
manifest = json.loads((ROOT / 'data/raw/manifest.json').read_text())
checks['raw_checksums_match'] = all(sha256(ROOT / 'data/raw' / item['filename']) == item['sha256'] for item in manifest)
quality = json.loads((ROOT / 'data/processed/quality_report.json').read_text())
checks['accepted_rejected_reconcile'] = all(quality[name]['raw'] == quality[name]['clean'] + quality[name]['rejected'] for name in ['collision','vehicle','casualty'])
warehouse = sqlite3.connect(ROOT / 'data/warehouse/traffic.sqlite')
try:
    checks['warehouse_integrity'] = warehouse.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    tables = {row[0] for row in warehouse.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    checks['required_dimensions'] = set(['dim_date','dim_road','dim_weather','dim_location','dim_severity']).issubset(tables)
    checks['required_aggregates'] = set(['agg_hour','agg_day','agg_weekday_number','agg_road','agg_weather']).issubset(tables)
    checks['aggregate_counts_reconcile'] = all(warehouse.execute(f'SELECT SUM(collisions) FROM {table}').fetchone()[0] == quality['collision']['clean'] for table in ['agg_hour','agg_day','agg_weekday_number','agg_road','agg_weather'])
finally:
    warehouse.close()
metrics = json.loads((ROOT / 'models/metrics.json').read_text())
checks['evaluated_model_data_hash_matches'] = metrics['data_sha256'] == sha256(ROOT / 'data/processed/model_ready.parquet')
registry = sqlite3.connect(ROOT / 'mlflow.db')
try:
    versions = registry.execute("SELECT name, version, status FROM model_versions WHERE name='traffic-severity'").fetchall()
    checks['registered_model_ready'] = any(row[2] == 'READY' for row in versions)
finally:
    registry.close()
deployment_file = ROOT / 'docs/evidence/deployment/docker_verification.json'
deployment = json.loads(deployment_file.read_text()) if deployment_file.exists() else {}
remaining = ['Compatible GB weather and demonstrated valid spatial/time enrichment', 'Airflow scheduler/worker run evidence if required', 'Instructor approval for SQLite alternative', 'Student authorship/attribution and separate Part 1 submission confirmation']
if not deployment.get('success'):
    remaining.append('Docker image build and running API container evidence')
report = {'audited_at_utc': datetime.now(timezone.utc).isoformat(), 'artifact_checks': checks, 'missing_files': missing, 'registered_versions': versions, 'external_weather_matches': quality['weather']['matched_collisions'], 'runtime_availability': {'docker_command': shutil.which('docker'), 'airflow_package': importlib.util.find_spec('airflow') is not None}, 'docker_verification': {'success': deployment.get('success', False), 'verified_at_utc': deployment.get('verified_at_utc')}, 'remaining_requirements': remaining}
output = ROOT / 'docs/evidence/requirements_verification.json'
output.write_text(json.dumps(report, indent=2))
packages = ['pandas','numpy','pyarrow','streamlit','plotly','scikit-learn','joblib','fastapi','uvicorn','requests','pytest','httpx','mlflow']
versions = {name: importlib.metadata.version(name) for name in packages}
(ROOT / 'docs/evidence/verified_environment.json').write_text(json.dumps({'python': sys.version, 'packages': versions}, indent=2))
(ROOT / 'requirements-verified.txt').write_text('# Exact top-level versions used for local verification.\n' + '\n'.join(f'{name}=={version}' for name, version in versions.items()) + '\n')
print(json.dumps(report, indent=2))
if not all(checks.values()):
    raise SystemExit('One or more persisted artifact checks failed.')
