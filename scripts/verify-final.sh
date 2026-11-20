#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/check.sh
uv run --extra anm python scripts/final_analysis.py >/tmp/causalbridge-final-analysis-check.json

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

postmerge_check=$(mktemp -d "${TMPDIR:-/tmp}/causalbridge-postmerge-verify.XXXXXX")
trap 'rm -rf "$postmerge_check"' EXIT
tar -xzf artifacts/final-delivery/postmerge-track-b/integrated-38-interrupted-live.tar.gz -C "$postmerge_check"
tar -xzf artifacts/final-delivery/postmerge-track-b/integrated-38-resumed-live.tar.gz -C "$postmerge_check"
uv run --extra anm python scripts/verify_integrated_live_provenance.py \
  --run "$postmerge_check/postmerge-track-b-38-resumed-live" \
  --source "$postmerge_check/postmerge-track-b-38-live" \
  --output "$postmerge_check/provenance.json"
cmp "$postmerge_check/provenance.json" \
  artifacts/final-delivery/postmerge-track-b/integrated-38-provenance-audit.json
uv run --extra anm python scripts/analyze_final_track_b_38.py \
  --run "$postmerge_check/postmerge-track-b-38-resumed-live" \
  --output "$postmerge_check/analysis"
cmp "$postmerge_check/analysis/metrics.json" \
  artifacts/final-delivery/postmerge-track-b/integrated-38-analysis/metrics.json
cmp "$postmerge_check/analysis/case-results.json" \
  artifacts/final-delivery/postmerge-track-b/integrated-38-analysis/case-results.json
echo 'Final archives, Track A traces, 304 bound real Track B responses, slides and report verified.'
