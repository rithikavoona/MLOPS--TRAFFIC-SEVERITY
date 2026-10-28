"""Exercise the deployed dashboard form and confirm API telemetry on the host."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = '''
import json
import os
from streamlit.testing.v1 import AppTest
assert os.environ['TRAFFIC_API_URL'] == 'http://api:8000'
app = AppTest.from_file('/opt/traffic/app.py', default_timeout=120).run()
assert not app.exception, str(app.exception)
next(button for button in app.button if button.label == 'Estimate severity').click().run()
assert not app.exception, str(app.exception)
assert not app.error, str(app.error)
assert any('Predicted severity:' in item.value for item in app.success)
assert any('Prediction served by API' in item.value for item in app.caption)
assert len(app.get('plotly_chart')) == 16
print(json.dumps({'success_message': [item.value for item in app.success],
                  'api_caption': [item.value for item in app.caption if 'Prediction served by API' in item.value]}))
'''


def main():
    log = ROOT / 'logs' / 'service_requests.jsonl'
    before = len(log.read_text().splitlines()) if log.exists() else 0
    result = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'dashboard', 'python', '-c', CODE],
        cwd=ROOT, capture_output=True, text=True, timeout=300, check=True,
    )
    new_requests = [json.loads(line) for line in log.read_text().splitlines()[before:]]
    assert any(item['status_code'] == 200 for item in new_requests), 'No successful API request logged.'
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
              'success': True, 'dashboard': json.loads(result.stdout.strip()),
              'new_api_requests': new_requests}
    output = ROOT / 'docs/evidence/deployment/dashboard_api_verification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
