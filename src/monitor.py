"""Batch drift monitoring. False negatives require observed severity labels."""
import argparse
import json
import numpy as np
import pandas as pd
from src.config import MODELS, PROCESSED, CATEGORICAL, ROOT, FEATURES
from sklearn.metrics import f1_score, recall_score

THRESHOLDS = {'categorical_tv': .15, 'latitude_tv': .15, 'class_tv': .10, 'severe_false_negative_rate': .40, 'fatal_recall_min': .40, 'missing_fraction': .20, 'service_failure_rate': .05, 'p95_latency_ms': 1000}


def total_variation(reference, current):
    keys = set(reference) | set(current)
    return .5 * sum(abs(reference.get(k, 0) - current.get(k, 0)) for k in keys)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', default=str(PROCESSED / 'model_ready.parquet'))
    args = parser.parse_args()
    batch = pd.read_parquet(args.batch)
    reference = json.loads((MODELS / 'reference.json').read_text())
    report = {'rows': len(batch), 'missing_fraction': batch.isna().mean().to_dict(), 'categorical_drift': {}}
    for col in CATEGORICAL:
        current = {str(float(k)): v for k, v in batch[col].fillna(-999).value_counts(normalize=True).items()}
        ref = {str(float(k)): v for k, v in reference[col].items()}
        report['categorical_drift'][col] = total_variation(ref, current)
    loc = np.histogram(batch.latitude.dropna(), bins=np.linspace(49,61,25))[0].astype(float)
    baseline = np.array(reference['latitude_bins'], dtype=float)
    report['latitude_drift'] = float(.5 * np.abs(loc / max(loc.sum(), 1) - baseline / max(baseline.sum(), 1)).sum())
    if 'collision_severity' in batch:
        current = {str(int(k)): v for k, v in batch.collision_severity.value_counts(normalize=True).items()}
        report['class_drift'] = total_variation(reference['class_distribution'], current)
        import joblib
        model = joblib.load(MODELS / 'severity.joblib')['pipeline']
        prediction = model.predict(batch[FEATURES])
        report['macro_f1'] = float(f1_score(batch.collision_severity, prediction, labels=[1,2,3], average='macro', zero_division=0))
        report['recall_by_class'] = dict(zip(['Fatal', 'Serious', 'Slight'], recall_score(batch.collision_severity, prediction, labels=[1,2,3], average=None, zero_division=0).tolist()))
        severe = batch.collision_severity.isin([1,2])
        report['severe_false_negative_rate'] = float((prediction[severe] == 3).mean()) if severe.any() else None
    else:
        report['severe_false_negative_rate'] = None
    log = ROOT / 'logs' / 'service_requests.jsonl'
    if log.exists():
        requests = pd.read_json(log, lines=True)
        report['service'] = {'requests': len(requests), 'failure_rate': float(requests.status.ne('success').mean()), 'p95_latency_ms': float(requests.latency_ms.quantile(.95))}
    alerts = []
    if any(value > THRESHOLDS['categorical_tv'] for value in report['categorical_drift'].values()):
        alerts.append('categorical_drift')
    if report['latitude_drift'] > THRESHOLDS['latitude_tv']:
        alerts.append('location_drift')
    if report.get('class_drift', 0) > THRESHOLDS['class_tv']:
        alerts.append('class_drift')
    if report.get('severe_false_negative_rate') is not None and report['severe_false_negative_rate'] > THRESHOLDS['severe_false_negative_rate']:
        alerts.append('severe_false_negatives')
    if report.get('recall_by_class', {}).get('Fatal', 1) < THRESHOLDS['fatal_recall_min']:
        alerts.append('low_fatal_recall')
    if any(report['missing_fraction'].get(col, 0) > THRESHOLDS['missing_fraction'] for col in FEATURES):
        alerts.append('input_missingness')
    service = report.get('service', {})
    if service.get('failure_rate', 0) > THRESHOLDS['service_failure_rate'] or service.get('p95_latency_ms', 0) > THRESHOLDS['p95_latency_ms']:
        alerts.append('service_health')
    report.update(alerts=alerts, thresholds=THRESHOLDS, retraining_review_required=bool(alerts), evaluation_scope='Provided batch; may contain training rows. Use new labeled records for operational monitoring.')
    (MODELS / 'monitoring.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
