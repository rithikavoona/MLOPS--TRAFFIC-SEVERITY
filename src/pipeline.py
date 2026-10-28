"""Idempotent offline ETL. Raw inputs are copied byte-for-byte; the UI reads Parquet only."""
import argparse
import hashlib
import json
import logging
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DATA, PROCESSED, FILENAMES, SEVERITY, ROAD, WEATHER, LIGHT, SURFACE, AREA, FEATURES

LOG = logging.getLogger(__name__)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ingest(source):
    raw = DATA / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, filename in FILENAMES.items():
        source_file, target = Path(source) / filename, raw / filename
        entry = {'source': name, 'filename': filename, 'extracted_at_utc': datetime.now(timezone.utc).isoformat()}
        try:
            source_hash = digest(source_file)
            if not target.exists() or digest(target) != source_hash:
                if source_file.resolve() != target.resolve():
                    shutil.copy2(source_file, target)
            entry.update(status='success', sha256=source_hash, bytes=target.stat().st_size)
        except Exception as exc:
            entry.update(status='failed', error=str(exc))
            manifest.append(entry)
            (raw / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            raise
        manifest.append(entry)
    (raw / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def read_source(name):
    return pd.read_csv(DATA / 'raw' / FILENAMES[name], dtype={'collision_index': 'string', 'collision_ref_no': 'string'}, low_memory=False)


def clean_collisions(frame):
    """Return collision-grain records and rejected originals with explicit reasons."""
    df = frame.copy()
    date = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    reasons = pd.Series('', index=df.index)
    checks = {
        'missing_collision_id': df.collision_index.isna() | df.collision_index.eq(''),
        'duplicate_collision_id': df.duplicated('collision_index'),
        'invalid_date': date.isna(),
        'year_mismatch': date.dt.year.ne(df.collision_year),
        'invalid_severity': ~df.collision_severity.isin(SEVERITY),
        'invalid_gb_coordinates': ~(df.latitude.between(49, 61) & df.longitude.between(-9, 2.5)),
        'invalid_counts': (df.number_of_vehicles < 1) | (df.number_of_casualties < 1),
    }
    for reason, mask in checks.items():
        reasons.loc[mask.fillna(True)] += reason + ';'
    rejected = df.loc[reasons.ne('')].copy()
    rejected['rejection_reason'] = reasons[reasons.ne('')].str.rstrip(';')
    df = df.loc[reasons.eq('')].copy()
    df['date'] = date.loc[df.index]
    # Retain valid collisions without time; do not invent an hour.
    dt = pd.to_datetime(df.date.dt.strftime('%Y-%m-%d') + ' ' + df.time.fillna(''), format='%Y-%m-%d %H:%M', errors='coerce')
    df['timestamp_local'] = dt
    df['hour'] = dt.dt.hour
    df['month'] = df.date.dt.month
    df['weekday_number'] = df.date.dt.dayofweek
    df['weekday'] = df.date.dt.day_name()
    df['date_key'] = df.date.dt.strftime('%Y%m%d').astype(int)
    for col in ['speed_limit', 'road_type', 'first_road_class', 'light_conditions', 'weather_conditions', 'road_surface_conditions', 'urban_or_rural_area']:
        df[col] = pd.to_numeric(df[col], errors='coerce').replace({-1: np.nan})
    df.loc[~df.speed_limit.isin([10, 15, 20, 30, 40, 50, 60, 70]), 'speed_limit'] = np.nan
    for source, target, mapping in [('collision_severity', 'severity', SEVERITY), ('road_type', 'road', ROAD), ('weather_conditions', 'weather', WEATHER), ('light_conditions', 'lighting', LIGHT), ('road_surface_conditions', 'surface', SURFACE), ('urban_or_rural_area', 'area', AREA)]:
        df[target] = df[source].map(mapping).fillna('Unknown')
    df['is_severe'] = df.collision_severity.isin([1, 2]).astype('int8')
    return df.reset_index(drop=True), rejected


def clean_children(df, collision_ids, keys):
    reasons = pd.Series('', index=df.index)
    reasons.loc[df.duplicated(keys)] += 'duplicate_child_key;'
    reasons.loc[~df.collision_index.isin(collision_ids)] += 'orphan_collision;'
    reasons.loc[df[keys].isna().any(axis=1)] += 'missing_child_key;'
    rejected = df.loc[reasons.ne('')].copy()
    rejected['rejection_reason'] = reasons[reasons.ne('')].str.rstrip(';')
    clean = df.loc[reasons.eq('')].copy()
    for col in clean.select_dtypes(include='number').columns:
        if col not in keys:
            clean[col] = clean[col].replace(-1, np.nan)
    return clean, rejected


def process_weather():
    path = DATA / 'raw' / FILENAMES['weather']
    metadata = pd.read_csv(path, nrows=1).iloc[0].to_dict()
    weather = pd.read_csv(path, skiprows=3)
    weather.columns = ['timestamp_utc', 'temperature_c']
    weather.timestamp_utc = pd.to_datetime(weather.timestamp_utc, utc=True, errors='coerce')
    weather.temperature_c = pd.to_numeric(weather.temperature_c, errors='coerce')
    rejected = weather.loc[weather.isna().any(axis=1) | weather.duplicated('timestamp_utc')].copy()
    rejected['rejection_reason'] = 'invalid_or_duplicate_weather'
    weather = weather.dropna().drop_duplicates('timestamp_utc')
    for key in ['latitude', 'longitude']:
        weather[key] = float(metadata[key])
    weather.to_parquet(DATA / 'cleaned' / 'weather.parquet', index=False)
    weather.to_parquet(PROCESSED / 'weather_external.parquet', index=False)
    rejected.to_csv(DATA / 'rejected' / 'weather.csv', index=False)
    return metadata, len(weather), len(rejected)


def enrich_weather(mart, weather, max_distance_km=25):
    """Match station-hour in UTC, gating by distance. DST-ambiguous times stay unmatched."""
    result = mart.copy()
    result['external_temperature_c'] = np.nan
    result['external_weather_status'] = 'unmatched_location'
    if weather.empty:
        return result
    station = weather.iloc[0]
    lat = np.radians(result.latitude.to_numpy())
    station_lat = np.radians(float(station.latitude))
    delta_lat = lat - station_lat
    delta_lon = np.radians(result.longitude.to_numpy() - float(station.longitude))
    distance = 6371 * 2 * np.arcsin(np.sqrt(np.clip(np.sin(delta_lat / 2)**2 + np.cos(lat) * np.cos(station_lat) * np.sin(delta_lon / 2)**2, 0, 1)))
    eligible = pd.Series(distance <= max_distance_km, index=result.index)
    utc = result.timestamp_local.dt.tz_localize('Europe/London', ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC').dt.floor('h')
    temperature = utc.map(weather.set_index('timestamp_utc').temperature_c)
    result.loc[eligible, 'external_weather_status'] = 'unmatched_time'
    matched = eligible & temperature.notna()
    result.loc[matched, 'external_temperature_c'] = temperature[matched]
    result.loc[matched, 'external_weather_status'] = 'matched'
    return result


def transform(manifest):
    for layer in ['staging', 'cleaned', 'processed', 'rejected', 'warehouse']:
        (DATA / layer).mkdir(parents=True, exist_ok=True)
    frames = {name: read_source(name) for name in ['collision', 'vehicle', 'casualty']}
    for name, frame in frames.items():
        frame.to_parquet(DATA / 'staging' / f'{name}.parquet', index=False)
    collisions, rejected = clean_collisions(frames['collision'])
    collisions.to_parquet(DATA / 'cleaned' / 'collision.parquet', index=False)
    rejected.to_csv(DATA / 'rejected' / 'collision.csv', index=False)
    quality = {'collision': {'raw': len(frames['collision']), 'clean': len(collisions), 'rejected': len(rejected), 'reasons': rejected.rejection_reason.value_counts().to_dict()}}
    children = {}
    for name, keys in [('vehicle', ['collision_index', 'vehicle_reference']), ('casualty', ['collision_index', 'casualty_reference'])]:
        clean, reject = clean_children(frames[name], collisions.collision_index, keys)
        clean.to_parquet(DATA / 'cleaned' / f'{name}.parquet', index=False)
        clean.to_parquet(PROCESSED / f'{name}.parquet', index=False)
        reject.to_csv(DATA / 'rejected' / f'{name}.csv', index=False)
        children[name] = clean
        quality[name] = {'raw': len(frames[name]), 'clean': len(clean), 'rejected': len(reject), 'reasons': reject.rejection_reason.value_counts().to_dict()}
    va = children['vehicle'].groupby('collision_index').agg(observed_vehicle_count=('vehicle_reference', 'size'), mean_driver_age=('age_of_driver', 'mean'), mean_vehicle_age=('age_of_vehicle', 'mean'))
    ca = children['casualty'].assign(fatal=lambda x: x.casualty_severity.eq(1).astype(int)).groupby('collision_index').agg(observed_casualty_count=('casualty_reference', 'size'), fatal_casualties=('fatal', 'sum'), mean_casualty_age=('age_of_casualty', 'mean'))
    mart = collisions.merge(va, on='collision_index', how='left', validate='one_to_one').merge(ca, on='collision_index', how='left', validate='one_to_one')
    metadata, weather_rows, weather_rejected = process_weather()
    mart = enrich_weather(mart, pd.read_parquet(PROCESSED / 'weather_external.parquet'))
    mart.to_parquet(PROCESSED / 'collision_mart.parquet', index=False)
    mart[['collision_index', 'date', 'collision_year', 'collision_severity'] + FEATURES].to_parquet(PROCESSED / 'model_ready.parquet', index=False)
    matched_weather = int(mart.external_weather_status.eq('matched').sum())
    quality['weather'] = {'clean': weather_rows, 'rejected': weather_rejected, 'metadata': metadata, 'join_status': 'matched' if matched_weather else 'no_valid_matches', 'matched_collisions': matched_weather, 'match_status_counts': mart.external_weather_status.value_counts().to_dict()}
    quality['checks'] = {'unique_collision_ids': bool(mart.collision_index.is_unique), 'mart_row_count_matches_clean': len(mart) == len(collisions), 'missing_time': int(mart.hour.isna().sum()), 'vehicle_count_mismatches': int(mart.observed_vehicle_count.fillna(0).ne(mart.number_of_vehicles).sum()), 'casualty_count_mismatches': int(mart.observed_casualty_count.fillna(0).ne(mart.number_of_casualties).sum())}
    dimensions = {
        'dim_date': mart[['date_key', 'date', 'month', 'weekday', 'weekday_number', 'collision_year']].drop_duplicates('date_key'),
        'dim_road': mart[['road_type', 'road']].drop_duplicates('road_type'),
        'dim_weather': mart[['weather_conditions', 'weather']].drop_duplicates('weather_conditions'),
        'dim_severity': pd.DataFrame({'collision_severity': list(SEVERITY), 'severity': list(SEVERITY.values())}),
        'dim_location': mart[['local_authority_ons_district', 'local_authority_highway', 'area']].drop_duplicates(['local_authority_ons_district', 'local_authority_highway', 'area']),
    }
    aggregates = {f'agg_{col}': mart.groupby(col, dropna=False).agg(collisions=('collision_index', 'size'), severe=('is_severe', 'sum'), casualties=('number_of_casualties', 'sum')).reset_index() for col in ['hour', 'date', 'weekday_number', 'road', 'weather']}
    aggregates['agg_day'] = aggregates.pop('agg_date')
    # Build a fresh database and replace it after successful completion.
    database = DATA / 'warehouse' / 'traffic.tmp.sqlite'
    if database.exists():
        database.unlink()
    with closing(sqlite3.connect(database)) as conn:
        for name, frame in {'fact_collision': mart, 'fact_vehicle': children['vehicle'], 'fact_casualty': children['casualty'], **dimensions, **aggregates}.items():
            frame.to_sql(name, conn, index=False, if_exists='replace', chunksize=5000)
        conn.execute('CREATE UNIQUE INDEX collision_pk ON fact_collision(collision_index)')
        conn.execute('CREATE INDEX collision_date ON fact_collision(date_key)')
        conn.execute('CREATE INDEX vehicle_fk ON fact_vehicle(collision_index)')
        conn.execute('CREATE INDEX casualty_fk ON fact_casualty(collision_index)')
        conn.commit()
    database.replace(DATA / 'warehouse' / 'traffic.sqlite')
    for name, frame in {**dimensions, **aggregates}.items():
        frame.to_parquet(PROCESSED / f'{name}.parquet', index=False)
    for entry in manifest:
        entry['row_count'] = quality[entry['source']].get('raw', weather_rows + weather_rejected)
    (DATA / 'raw' / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    quality.update(completed_at_utc=datetime.now(timezone.utc).isoformat(), date_min=str(mart.date.min()), date_max=str(mart.date.max()), years=sorted(mart.collision_year.unique().tolist()))
    (PROCESSED / 'quality_report.json').write_text(json.dumps(quality, indent=2, default=str))
    LOG.info('Completed ETL: %s collisions; years %s', len(mart), quality['years'])
    return quality


def validate_outputs():
    """Read persisted artifacts and check key, count and aggregate invariants."""
    report = json.loads((PROCESSED / 'quality_report.json').read_text())
    if not report['checks']['unique_collision_ids'] or not report['checks']['mart_row_count_matches_clean']:
        raise ValueError('Collision key or grain validation failed.')
    for name in ['collision', 'vehicle', 'casualty']:
        counts = report[name]
        if counts['raw'] != counts['clean'] + counts['rejected']:
            raise ValueError(f'{name}: accepted and rejected rows do not reconcile.')
    with closing(sqlite3.connect(DATA / 'warehouse' / 'traffic.sqlite')) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Warehouse integrity check failed.')
        for table in ['agg_hour', 'agg_day', 'agg_weekday_number', 'agg_road', 'agg_weather']:
            total = conn.execute(f'SELECT SUM(collisions) FROM {table}').fetchone()[0]
            if total != report['collision']['clean']:
                raise ValueError(f'{table}: aggregate totals do not reconcile.')
    LOG.info('Persisted artifact validation passed.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=DATA / 'raw')
    parser.add_argument('--stage', choices=['all', 'ingest', 'transform', 'validate'], default='all')
    args = parser.parse_args()
    (DATA.parent / 'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(DATA.parent / 'logs' / 'pipeline.log')])
    try:
        if args.stage in ['all', 'ingest']:
            manifest = ingest(args.source)
        else:
            manifest = json.loads((DATA / 'raw' / 'manifest.json').read_text())
        if args.stage in ['all', 'transform']:
            transform(manifest)
        if args.stage in ['all', 'validate']:
            validate_outputs()
    except Exception:
        LOG.exception('Pipeline failed')
        raise


if __name__ == '__main__':
    main()
