import io
import json
from urllib.error import HTTPError, URLError

import pytest

from src.dashboard import api_client


def test_prediction_http_request(monkeypatch):
    monkeypatch.setenv('TRAFFIC_API_URL', 'http://api:8000/')
    expected = {'severity': 'Slight', 'probabilities': {'Fatal': .1, 'Serious': .2, 'Slight': .7}, 'model_version': 'test'}

    def respond(request, timeout):
        assert request.full_url == 'http://api:8000/predict'
        assert request.method == 'POST'
        assert json.loads(request.data) == {'hour': 17}
        assert timeout == 30
        return io.BytesIO(json.dumps(expected).encode())

    monkeypatch.setattr(api_client, 'urlopen', respond)
    assert api_client.predict_severity({'hour': 17}) == expected


@pytest.mark.parametrize('failure', [URLError('offline'), TimeoutError(),
    HTTPError('http://api/predict', 422, 'invalid', {}, None),
    HTTPError('http://api/predict', 503, 'unavailable', {}, None)])
def test_prediction_failures_are_user_facing(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(api_client, 'urlopen', fail)
    with pytest.raises(api_client.PredictionServiceError):
        api_client.predict_severity({})


def test_prediction_invalid_response(monkeypatch):
    monkeypatch.setattr(api_client, 'urlopen', lambda *a, **k: io.BytesIO(b'{}'))
    with pytest.raises(api_client.PredictionServiceError):
        api_client.predict_severity({})
