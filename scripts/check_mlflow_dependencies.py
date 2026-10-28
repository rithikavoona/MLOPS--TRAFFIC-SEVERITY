import sys
import importlib.metadata as metadata
from pathlib import Path
from packaging.requirements import Requirement

sys.path.append(str(Path(__file__).resolve().parents[1] / '.deps'))
missing = set()
for distribution in ['mlflow', 'mlflow-skinny', 'mlflow-tracing']:
    for requirement in metadata.requires(distribution):
        req = Requirement(requirement)
        if req.marker and not req.marker.evaluate():
            continue
        try:
            metadata.version(req.name)
        except metadata.PackageNotFoundError:
            missing.add(req.name)
print(' '.join(sorted(missing)))
