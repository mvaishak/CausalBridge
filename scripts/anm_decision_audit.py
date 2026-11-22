"""Freeze, execute, and replay the independent numerical/decision audit."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_decision_audit import prepare, report, run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["prepare", "run", "report"])
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
if args.command == "prepare":
    print(json.dumps({"cases": len(prepare(args.plan)["cases"])}))
elif args.command == "run":
    print(json.dumps({"records": len(run(args.plan))}))
else:
    print(json.dumps(report(args.plan, args.output)))
