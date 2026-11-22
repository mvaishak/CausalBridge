"""Prepare and replay the fixed exploratory ANM adequacy-policy comparison."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_adequacy_comparison import execute, prepare

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["prepare", "run", "replay"])
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
if args.command == "prepare":
    result = prepare(args.plan)
    print(json.dumps({"panels": result["protocol"]["panels"], "scope": result["scope"]}))
else:
    if args.output is None:
        parser.error("--output is required for run/replay")
    result = execute(args.plan, args.output, replay=args.command == "replay")
    print(json.dumps({"tables": len(result["tables"]), "scope": result["scope"]}))
