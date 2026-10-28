"""Verify running Docker services and retain reproducible deployment evidence."""
import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/evidence/deployment/docker_verification.json'


def command(*args):
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True, timeout=30).stdout


def request(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.status, response.read().decode()


def main():
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'success': False}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        ids = command('docker', 'compose', 'ps', '-q').split()
        if len(ids) != 2:
            raise AssertionError(f'Expected two running services, found {len(ids)}.')
        inspected = json.loads(command('docker', 'inspect', *ids))
        report['containers'] = [{'name': item['Name'].lstrip('/'), 'image_id': item['Image'], 'running': item['State']['Running'], 'health': item['State'].get('Health', {}).get('Status'), 'ports': item['NetworkSettings']['Ports']} for item in inspected]
        assert all(item['running'] and item['health'] == 'healthy' for item in report['containers']), 'Containers must both be running and healthy.'
        status, body = request('http://127.0.0.1:8501/_stcore/health')
        assert status == 200 and body.strip() == 'ok'
        report['dashboard_health'] = {'status_code': status, 'body': body}
        status, body = request('http://127.0.0.1:8000/health')
        health = json.loads(body)
        metrics = json.loads((ROOT / 'models/metrics.json').read_text())
        assert status == 200 and health['status'] == 'ready'
        assert health['version'] == metrics['version'], 'Served model version differs from evaluated model.'
        report['api_health'] = health
        scenario = {'hour':17, 'month':6, 'weekday_number':2, 'speed_limit':30, 'road_type':6, 'first_road_class':3, 'light_conditions':1, 'weather_conditions':1, 'road_surface_conditions':1, 'urban_or_rural_area':1, 'latitude':51.5, 'longitude':-.12}
        status, body = request('http://127.0.0.1:8000/predict', scenario)
        result = json.loads(body)
        assert status == 200 and result['model_version'] == metrics['version']
        assert set(result['probabilities']) == {'Fatal','Serious','Slight'}
        assert all(0 <= value <= 1 for value in result['probabilities'].values())
        assert abs(sum(result['probabilities'].values()) - 1) < 1e-6
        report['prediction'] = result
        try:
            request('http://127.0.0.1:8000/predict', {'hour':99})
        except urllib.error.HTTPError as error:
            assert error.code == 422
            report['invalid_payload_status'] = error.code
        else:
            raise AssertionError('Invalid payload was not rejected.')
        report['success'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        OUTPUT.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
