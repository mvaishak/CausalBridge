"""Archive the frozen real-noise study, copied originals and executable source."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_real_noise import validate_plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--analysis", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    frozen = validate_plan(a.plan)
    metrics = json.loads((a.analysis / "metrics.json").read_text())
    if metrics["manifest_digest"] != canonical_digest(frozen):
        raise ValueError("Analysis/plan mismatch")
    a.output.mkdir(parents=True, exist_ok=False)
    archive = a.output / "run-records.tar.gz"
    entries = []
    with tarfile.open(archive, "w:gz") as tar:

        def add(path, name, expected=None):
            if path.is_symlink():
                raise ValueError("Refuse symlink")
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if expected is not None and expected != digest:
                raise ValueError("Frozen source changed")
            entries.append({"path": name, "bytes": len(data), "sha256": digest})
            tar.add(path, arcname=name, recursive=False)

        for label, root in [("plan", a.plan), ("analysis", a.analysis)]:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    add(path, str(Path(label) / path.relative_to(root)))
        for path, digest in frozen["source_sha256"].items():
            add(Path(path), "frozen-source/" + path, digest)
        for path in ["pyproject.toml", "README.md", ".python-version"]:
            add(Path(path), "frozen-source/" + path)
    manifest = {
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": entries,
        "plan_digest": canonical_digest(frozen),
        "scope": "Frozen inputs, vectors, original records and source; hashes are not signatures.",
    }
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(entries), "archive_bytes": archive.stat().st_size}))


if __name__ == "__main__":
    main()
