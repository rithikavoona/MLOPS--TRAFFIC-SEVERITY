"""Export processed Parquet tables to readable CSV without changing dashboard inputs."""
import csv
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / 'data' / 'processed'


def main():
    destination = PROCESSED / 'csv'
    destination.mkdir(exist_ok=True)
    catalog = []
    for source in sorted(PROCESSED.glob('*.parquet')):
        table = pq.ParquetFile(source)
        target = destination / f'{source.stem}.csv'
        with target.open('w', encoding='utf-8-sig', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(table.schema_arrow.names)
            for batch in table.iter_batches(batch_size=10000):
                columns = [column.to_pylist() for column in batch.columns]
                writer.writerows(zip(*columns))
        # Re-read the CSV to verify every record and column was preserved.
        with target.open(encoding='utf-8-sig', newline='') as output:
            reader = csv.reader(output)
            assert next(reader) == table.schema_arrow.names
            assert sum(1 for _ in reader) == table.metadata.num_rows
        catalog.append({'file': target.name, 'rows': table.metadata.num_rows,
                        'columns': [{'name': field.name, 'type': str(field.type)}
                                    for field in table.schema_arrow]})
        print(f'{target.name}: {table.metadata.num_rows:,} rows verified', flush=True)
    (destination / 'data_dictionary.json').write_text(
        json.dumps(catalog, indent=2), encoding='utf-8')
    lines = ['# Open the processed data', '',
             'Open the files in this folder with Excel, LibreOffice, or a text editor. '
             'CSV files contain all rows and columns from the corresponding processed Parquet files. '
             'In Excel, use Data > From Text/CSV and set identifier columns such as collision_index '
             'to Text to preserve leading zeroes.', '',
             'The dashboard continues to read the original processed Parquet tables in the parent folder. '
             'Parquet is a compact analytical format and does not open directly in a normal spreadsheet app.', '',
             '- collision_mart.csv: cleaned, enriched collisions used for the dashboard.',
             '- vehicle.csv and casualty.csv: processed child records linked by collision_index.',
             '- model_ready.csv: features and target prepared for modelling.',
             '- weather_external.csv: processed external Berlin weather; not matched to GB collisions.',
             '- agg_*.csv: summary tables; dim_*.csv: warehouse dimension tables.',
             '- data_dictionary.json: exact column names and data types for every export.', '',
             '| File | Data rows | Columns |', '| --- | ---: | ---: |']
    lines += [f"| {item['file']} | {item['rows']:,} | {len(item['columns'])} |" for item in catalog]
    (destination / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
