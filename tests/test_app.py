from streamlit.testing.v1 import AppTest
from src.config import ROOT


def test_dashboard_renders_and_filters(monkeypatch):
    from src.dashboard.pages import severity_model
    from src.dashboard.api_client import PredictionServiceError
    calls = []
    def predict(values):
        calls.append(values)
        return {'severity': 'Slight', 'probabilities': {'Fatal': .1, 'Serious': .2, 'Slight': .7}, 'model_version': 'test-api'}
    monkeypatch.setattr(severity_model, 'predict_severity', predict)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=90).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        'Overview', 'Time patterns', 'Conditions', 'Hotspots',
        'Vehicles & casualties', 'Severity model', 'Pipeline health',
    ]
    assert len(app.metric) >= 4
    plots_before_prediction = len(app.get('plotly_chart'))
    assert plots_before_prediction == 15
    next(button for button in app.button if button.label == 'Estimate severity').click().run()
    assert not app.exception
    assert len(app.get('plotly_chart')) == plots_before_prediction + 1
    assert len(calls) == 1 and calls[0]['hour'] == 17
    assert any('Predicted severity: Slight' in item.value for item in app.success)
    def fail(values):
        raise PredictionServiceError('Cannot reach the prediction API.')
    monkeypatch.setattr(severity_model, 'predict_severity', fail)
    next(button for button in app.button if button.label == 'Estimate severity').click().run()
    assert not app.exception
    assert any('Cannot reach' in item.value for item in app.error)
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any('No collisions' in item.value for item in app.warning)
