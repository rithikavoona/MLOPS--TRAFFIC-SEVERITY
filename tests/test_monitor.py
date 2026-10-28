import json
import sys
import pandas as pd
from src import monitor
from src.config import MODELS, PROCESSED, FEATURES


def test_total_variation_has_expected_bounds():
    assert monitor.total_variation({'a': 1}, {'a': 1}) == 0
    assert monitor.total_variation({'a': 1}, {'b': 1}) == 1


def test_unlabeled_batch_does_not_claim_false_negative_or_recall(tmp_path, monkeypatch):
    batch = pd.read_parquet(PROCESSED / 'model_ready.parquet', columns=FEATURES).head(10)
    batch.to_parquet(tmp_path / 'batch.parquet', index=False)
    (tmp_path / 'reference.json').write_text((MODELS / 'reference.json').read_text())
    monkeypatch.setattr(monitor, 'MODELS', tmp_path)
    monkeypatch.setattr(monitor, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['monitor', '--batch', str(tmp_path / 'batch.parquet')])
    monitor.main()
    report = json.loads((tmp_path / 'monitoring.json').read_text())
    assert report['severe_false_negative_rate'] is None
    assert 'recall_by_class' not in report
    assert 'class_drift' not in report
    assert 'alerts' in report
