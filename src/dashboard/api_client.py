"""HTTP boundary between the dashboard and the prediction service."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PredictionServiceError(RuntimeError):
    """A user-facing prediction service failure."""


def predict_severity(values: dict) -> dict:
    base_url = os.getenv('TRAFFIC_API_URL', 'http://127.0.0.1:8000').rstrip('/')
    request = Request(
        f'{base_url}/predict', data=json.dumps(values).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as exc:
        messages = {
            422: 'The prediction service rejected the scenario. Check the input values.',
            503: 'The prediction model is unavailable. Start the API with a trained model.',
        }
        raise PredictionServiceError(messages.get(exc.code, 'The prediction service failed. Check the API logs.')) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PredictionServiceError(
            'Cannot reach the prediction API. Check that the API is running and TRAFFIC_API_URL is correct.'
        ) from exc
    except (ValueError, TypeError) as exc:
        raise PredictionServiceError('The prediction API returned an invalid response.') from exc
    if not isinstance(result, dict) or not isinstance(result.get('probabilities'), dict) or not result.get('model_version') or not result.get('severity'):
        raise PredictionServiceError('The prediction API returned an incomplete response.')
    return result
