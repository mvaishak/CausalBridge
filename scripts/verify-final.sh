#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/check.sh
saved_check=$(mktemp -d "${TMPDIR:-/tmp}/causalbridge-saved-verify.XXXXXX")
trap 'rm -rf "$saved_check"' EXIT
uv run --extra anm python scripts/reproduce_saved_results.py --output "$saved_check/results"

python3 - <<'PY'
import hashlib
import json
import tarfile
from pathlib import Path

root = Path('artifacts/anm-experiments-2026-11-18')
manifest = json.loads((root / 'manifest.json').read_text())
archive = root / manifest['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256']
expected = {item['path']: item for item in manifest['files']}
observed = set()
with tarfile.open(archive, 'r:gz') as handle:
    for item in handle:
        if not item.isfile():
            continue
        data = handle.extractfile(item).read()
        record = expected[item.name]
        assert len(data) == record['bytes']
        assert hashlib.sha256(data).hexdigest() == record['sha256']
        observed.add(item.name)
assert observed == set(expected) and len(observed) == 7125
print('ANM archive: 7,125 files verified')
PY

test "$(gzip -dc artifacts/final-delivery/track-a-live/traces.jsonl.gz | wc -l | tr -d ' ')" = 50
unzip -tq artifacts/final-delivery/track-b-pilot/original-real-pilot-01.zip >/dev/null
unzip -tq presentation/CausalBridge-final.pptx >/dev/null
test "$(pdfinfo report/CausalBridge-final.pdf | awk '/^Pages:/ {print $2}')" -le 4

echo 'Saved analyses reproduced from tracked archives; no inference required for replay.'
