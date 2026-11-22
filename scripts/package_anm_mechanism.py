"""Preserve frozen plans, raw producer artifacts, diagnostics and source without rewriting."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_mechanism_study import validate_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight, full = validate_plan(args.preflight), validate_plan(args.full)
    if preflight["source_sha256"] != full["source_sha256"]:
        raise ValueError("Preflight/main sources differ")
    metrics = json.loads((args.analysis / "metrics.json").read_text())
    if metrics["manifest_digest"] != canonical_digest(full):
        raise ValueError("Analysis belongs to another experiment")
    args.output.mkdir(parents=True, exist_ok=False)
    archive = args.output / "run-records.tar.gz"
    entries = []
    with tarfile.open(archive, "w:gz") as tar:
        for label, root in (
            ("preflight", args.preflight),
            ("full", args.full),
            ("analysis", args.analysis),
        ):
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Refuse symlink")
                if not path.is_file():
                    continue
                data = path.read_bytes()
                name = str(Path(label) / path.relative_to(root))
                entries.append(
                    {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                )
                tar.add(path, arcname=name, recursive=False)
        for relative, expected in full["source_sha256"].items():
            path = Path(relative)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Frozen source bytes changed")
            name = "frozen-source/" + relative
            entries.append({"path": name, "bytes": len(data), "sha256": expected})
            tar.add(path, arcname=name, recursive=False)
        # Capture environment/build context alongside the frozen numerical source.
        for relative in ("pyproject.toml", "README.md", ".python-version"):
            path = Path(relative)
            data = path.read_bytes()
            name = "frozen-source/" + relative
            entries.append(
                {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            )
            tar.add(path, arcname=name, recursive=False)
    manifest = {
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": entries,
        "full_manifest_digest": canonical_digest(full),
        "preflight_manifest_digest": canonical_digest(preflight),
        "scope": "Raw experiment plus exact frozen numerical source; hashes are not signatures.",
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(entries), "archive_bytes": archive.stat().st_size}))


if __name__ == "__main__":
    main()
