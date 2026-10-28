"""Track an evaluated local artifact without repeating model training."""
import importlib.util
import json
import sys
from pathlib import Path
import joblib
import pandas as pd
from src.config import ROOT, MODELS, PROCESSED, FEATURES, SEVERITY


def track(model, metrics, example):
    # Local support packages are appended; existing numerical libraries take priority.
    if importlib.util.find_spec('mlflow') is None and (ROOT / '.deps').exists():
        sys.path.append(str(ROOT / '.deps'))
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature
    mlflow.set_tracking_uri('sqlite:///' + str(ROOT / 'mlflow.db').replace('\\', '/'))
    mlflow.set_experiment('traffic-severity')
    example = example.astype(float)  # Float schema accepts missing numeric values.
    with mlflow.start_run(run_name=metrics['version']):
        mlflow.log_params({'max_depth': metrics['selected_depth'], 'n_estimators': 100, 'train_rows': metrics['train_rows_used'], 'class_weight': 'balanced_subsample', 'random_state': 42, 'test_year': metrics['test_year'], 'data_sha256': metrics['data_sha256']})
        mlflow.log_metrics({k: metrics[k] for k in ['macro_f1', 'balanced_accuracy', 'baseline_macro_f1']})
        for label, report in metrics['report'].items():
            if label in SEVERITY.values():
                mlflow.log_metric(f'recall_{label.lower()}', report['recall'])
        mlflow.log_dict(metrics, 'evaluation.json')
        # This is our locally fitted Random Forest. Trust only its known dtype/tree
        # containers; never derive a blanket trust list from an external model.
        mlflow.sklearn.log_model(model, name='severity', registered_model_name='traffic-severity', signature=infer_signature(example, model.predict(example)), input_example=example, skops_trusted_types=['numpy.dtype', 'sklearn.tree._tree.Tree'])
        return mlflow.active_run().info.run_id


def main():
    bundle = joblib.load(MODELS / 'severity.joblib')
    metrics_path = MODELS / 'metrics.json'
    metrics = json.loads(metrics_path.read_text())
    example = pd.read_parquet(PROCESSED / 'model_ready.parquet', columns=FEATURES).head(5)
    metrics['mlflow_run_id'] = track(bundle['pipeline'], metrics, example)
    metrics['mlflow_status'] = 'tracked_and_registered'
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(metrics['mlflow_run_id'])


if __name__ == '__main__':
    main()
