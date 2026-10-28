"""Package the source, raw/processed data and verified artifacts; prune dependencies."""
import argparse
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.deps', '.venv', '__pycache__', '.pytest_cache', '.git', 'report_preview'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'traffic_severity_project.zip')
    args = parser.parse_args()
    files = []
    for folder, directories, names in os.walk(ROOT):
        directories[:] = [name for name in directories if name not in EXCLUDED]
        for name in names:
            path = Path(folder) / name
            if path.resolve() == args.output.resolve() or name == '.env' or name.endswith(('.pyc', '.tmp.sqlite', '-wal', '-shm', '.zip')):
                continue
            files.append(path)
    print(f'Packaging {len(files)} files', flush=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as output:
        for path in files:
            output.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    with zipfile.ZipFile(args.output) as output:
        assert output.testzip() is None, 'ZIP integrity check failed'
    print(f'{args.output} ({args.output.stat().st_size / 1024**2:.1f} MB)', flush=True)


if __name__ == '__main__':
    main()
