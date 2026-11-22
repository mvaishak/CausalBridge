"""Freeze, execute, or replay the fixed ANM mean robustness diagnostic."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_mean_robustness import prepare, report, run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["prepare", "run", "report"])
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--originals", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
if args.command == "prepare":
    result = prepare(args.plan, args.originals)
    print(json.dumps({"cases": len(result["real"])}))
elif args.command == "run":
    result = run(args.plan)
    print(json.dumps({"configurations": len(result)}))
else:
    print(json.dumps(report(args.plan, args.output)))
