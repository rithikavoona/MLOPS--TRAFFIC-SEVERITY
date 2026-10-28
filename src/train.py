"""Chronological tuning and test evaluation; all imputation is fit on training data."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, f1_score, balanced_accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from src.config import PROCESSED, MODELS, FEATURES, CATEGORICAL, SEVERITY


def make_pipeline(depth):
    numeric = [x for x in FEATURES if x not in CATEGORICAL]
    prep = ColumnTransformer([
        ('numeric', SimpleImputer(strategy='median', add_indicator=True), numeric),
        ('category', Pipeline([('impute', SimpleImputer(strategy='most_frequent')), ('encode', OneHotEncoder(handle_unknown='ignore'))]), CATEGORICAL),
    ])
    return Pipeline([('preprocessing', prep), ('model', RandomForestClassifier(n_estimators=100, max_depth=depth, min_samples_leaf=10, class_weight='balanced_subsample', random_state=42, n_jobs=-1))])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-train-rows', type=int, default=150000, help='Explicit training cap for laptop operation; test and validation use all records.')
    parser.add_argument('--mlflow', action='store_true', help='Require MLflow experiment tracking and registry.')
    args = parser.parse_args()
    data = pd.read_parquet(PROCESSED / 'model_ready.parquet').sort_values('date')
    years = sorted(data.collision_year.unique())
    if len(years) < 3:
        raise ValueError('At least three distinct years are required for chronological train/validation/test.')
    train = data[data.collision_year < years[-2]]
    valid = data[data.collision_year == years[-2]]
    test = data[data.collision_year == years[-1]]
    full_train_rows = len(train)
    if len(train) > args.max_train_rows:
        # Stratify sampling within each target class, preserving imbalance.
        fraction = args.max_train_rows / len(train)
        train = train.groupby('collision_severity', group_keys=False).sample(frac=fraction, random_state=42)
    candidates = []
    best_score, model = -1, None
    for depth in [12, 20]:
        candidate = make_pipeline(depth)
        candidate.fit(train[FEATURES], train.collision_severity)
        score = f1_score(valid.collision_severity, candidate.predict(valid[FEATURES]), average='macro', zero_division=0)
        candidates.append({'max_depth': depth, 'validation_macro_f1': score})
        if score > best_score:
            best_score, model = score, candidate
    prediction = model.predict(test[FEATURES])
    baseline = np.full(len(test), train.collision_severity.mode().iloc[0])
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    metrics = {'version': version, 'train_years': years[:-2], 'validation_year': int(years[-2]), 'test_year': int(years[-1]), 'train_rows_available': full_train_rows, 'train_rows_used': len(train), 'validation_rows': len(valid), 'test_rows': len(test), 'macro_f1': f1_score(test.collision_severity, prediction, average='macro', zero_division=0), 'balanced_accuracy': balanced_accuracy_score(test.collision_severity, prediction), 'baseline_macro_f1': f1_score(test.collision_severity, baseline, average='macro', zero_division=0), 'report': classification_report(test.collision_severity, prediction, labels=[1,2,3], target_names=list(SEVERITY.values()), output_dict=True, zero_division=0), 'confusion_matrix': confusion_matrix(test.collision_severity, prediction, labels=[1,2,3]).tolist(), 'candidates': candidates, 'selected_depth': model.named_steps['model'].max_depth, 'features': FEATURES, 'data_sha256': hashlib.sha256((PROCESSED / 'model_ready.parquet').read_bytes()).hexdigest(), 'mlflow_status': 'not_requested'}
    MODELS.mkdir(exist_ok=True)
    bundle = {'pipeline': model, 'version': version, 'features': FEATURES}
    joblib.dump(bundle, MODELS / 'severity.joblib')
    joblib.dump(bundle, MODELS / f'severity_{version}.joblib')
    reference = {col: train[col].fillna(-999).value_counts(normalize=True).to_dict() for col in CATEGORICAL}
    reference['latitude_bins'] = np.histogram(train.latitude, bins=np.linspace(49,61,25))[0].tolist()
    reference['class_distribution'] = train.collision_severity.value_counts(normalize=True).to_dict()
    (MODELS / 'reference.json').write_text(json.dumps(reference, indent=2))
    if args.mlflow:
        from src.tracking import track
        metrics['mlflow_run_id'] = track(model, metrics, train[FEATURES].head(5))
        metrics['mlflow_status'] = 'tracked_and_registered'
    (MODELS / 'metrics.json').write_text(json.dumps(metrics, indent=2, default=lambda x: x.item() if hasattr(x, 'item') else str(x)))
    print(json.dumps({k: metrics[k] for k in ['macro_f1', 'balanced_accuracy', 'baseline_macro_f1', 'train_rows_used', 'mlflow_status']}, indent=2))


if __name__ == '__main__':
    main()
