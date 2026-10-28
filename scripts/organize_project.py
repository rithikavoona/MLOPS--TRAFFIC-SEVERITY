"""Safe migration of documentation into reference/report/evidence folders."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def move(source, destination):
    source = (ROOT / source).resolve()
    destination = (ROOT / destination).resolve()
    if not source.is_relative_to(ROOT) or not destination.is_relative_to(ROOT):
        raise ValueError('Migration paths must remain inside the project.')
    if source.exists() and not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))


move('docs/assignment_brief.pdf', 'docs/reference/assignment_brief.pdf')
move('docs/project_report.pdf', 'docs/reports/project_report.pdf')
move('docs/report_preview', 'docs/reports/report_preview')
move('docs/evidence/dashboard_overview.png', 'docs/evidence/screenshots/dashboard_overview.png')
move('docs/evidence/warehouse_schema.sql', 'docs/evidence/schema/warehouse_schema.sql')
for file in (ROOT / 'docs/evidence').glob('*_sample.csv'):
    move(file.relative_to(ROOT), Path('docs/evidence/samples') / file.name)
for name in ['dashboard_test.log', 'dashboard_final.log']:
    move(Path('logs') / name, Path('logs/diagnostics') / name)
