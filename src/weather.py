"""Explicit, bounded archive API extraction for a GB station; no automatic network calls."""
import argparse
import json
from datetime import date, datetime, timezone
import requests
from src.config import DATA


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--latitude', type=float, required=True)
    parser.add_argument('--longitude', type=float, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end or not 49 <= args.latitude <= 61 or not -9 <= args.longitude <= 2.5:
        raise ValueError('Use a GB station and a valid date range.')
    path = DATA / 'raw' / 'weather_api'
    path.mkdir(parents=True, exist_ok=True)
    extraction = {'extracted_at_utc': datetime.now(timezone.utc).isoformat(), 'source': 'Open-Meteo archive API', 'requested_station': [args.latitude, args.longitude], 'start': args.start, 'end': args.end}
    try:
        response = requests.get('https://archive-api.open-meteo.com/v1/archive', params={'latitude': args.latitude, 'longitude': args.longitude, 'start_date': args.start, 'end_date': args.end, 'hourly': 'temperature_2m,precipitation,weather_code', 'timezone': 'GMT'}, timeout=90)
        extraction['http_status'] = response.status_code
        response.raise_for_status()
        payload = response.json()
        extraction.update(status='success', row_count=len(payload['hourly']['time']))
    except (requests.RequestException, ValueError, KeyError) as error:
        extraction.update(status='failed', error=str(error))
        with (path / 'extraction_log.jsonl').open('a') as file:
            file.write(json.dumps(extraction) + '\n')
        raise
    payload['_extraction'] = extraction
    (path / f'{args.latitude}_{args.longitude}_{args.start}_{args.end}.json').write_text(json.dumps(payload))
    with (path / 'extraction_log.jsonl').open('a') as file:
        file.write(json.dumps(extraction) + '\n')
    print('Raw weather archive saved. Apply timezone and distance gates before enrichment; this extraction does not alter the mart.')


if __name__ == '__main__':
    main()
