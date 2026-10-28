"""Airflow 2.x DAG. Mount project at /opt/traffic and raw CSVs at data/raw."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG('traffic_severity_etl', start_date=datetime(2026, 1, 1), schedule='@weekly', catchup=False, max_active_runs=1, default_args={'retries': 2, 'retry_delay': timedelta(minutes=5)}, tags=['traffic', 'etl']) as dag:
    ingest = BashOperator(task_id='ingest_raw_sources', bash_command='cd /opt/traffic && python -m src.pipeline --stage ingest --source data/raw')
    transform = BashOperator(task_id='transform_and_load_warehouse', bash_command='cd /opt/traffic && python -m src.pipeline --stage transform')
    validate = BashOperator(task_id='validate_persisted_outputs', bash_command='cd /opt/traffic && python -m src.pipeline --stage validate')
    ingest >> transform >> validate
