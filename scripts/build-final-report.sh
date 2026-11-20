#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p report
PANDOC_BIN=${PANDOC_BIN:-pandoc}
if [[ -z ${PDF_ENGINE:-} ]]; then
  if command -v xelatex >/dev/null 2>&1; then
    PDF_ENGINE=xelatex
  elif command -v tectonic >/dev/null 2>&1; then
    PDF_ENGINE=tectonic
  else
    echo 'Install xelatex or tectonic to build the report PDF.' >&2
    exit 1
  fi
fi
"$PANDOC_BIN" report/CausalBridge-final.md \
  --from markdown+tex_math_dollars+raw_tex \
  --pdf-engine="$PDF_ENGINE" \
  -V geometry:margin=0.68in \
  -V fontsize=10pt \
  -V linestretch=1.03 \
  -V papersize=letter \
  -o report/CausalBridge-final.pdf
pdfinfo report/CausalBridge-final.pdf | sed -n '/^Pages:/p'
