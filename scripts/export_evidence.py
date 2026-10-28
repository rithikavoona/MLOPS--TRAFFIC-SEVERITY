"""Export schema and small populated table samples from the actual warehouse."""
import json
import sqlite3
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
output = root / 'docs' / 'evidence'
output.mkdir(exist_ok=True)
(output / 'schema').mkdir(exist_ok=True)
(output / 'samples').mkdir(exist_ok=True)
conn = sqlite3.connect(root / 'data' / 'warehouse' / 'traffic.sqlite')
try:
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name").fetchall()
    (output / 'schema' / 'warehouse_schema.sql').write_text(';\n\n'.join(row[0] for row in schema) + ';\n')
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    counts = {}
    for (table,) in tables:
        # Table names come from our generated warehouse, not external input.
        counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT 20', conn).to_csv(output / 'samples' / f'{table}_sample.csv', index=False)
    (output / 'warehouse_counts.json').write_text(json.dumps(counts, indent=2))
finally:
    conn.close()
