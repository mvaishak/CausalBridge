#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p report
pandoc report/CausalBridge-final.md \
  --from markdown+tex_math_dollars+raw_tex \
  --pdf-engine=xelatex \
  -V geometry:margin=0.68in \
  -V fontsize=10pt \
  -V linestretch=1.03 \
  -V papersize=letter \
  -o report/CausalBridge-final.pdf
pdfinfo report/CausalBridge-final.pdf | sed -n '/^Pages:/p'
