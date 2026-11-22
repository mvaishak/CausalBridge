"""Prepare, execute or replay the bounded synthetic ANM mechanism experiment."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_mechanism_analysis import analyze
from causalbridge.evaluation.anm_mechanism_study import execute, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--phase", choices=["preflight", "full"], required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--preflight", type=Path)
    p = sub.add_parser("analyze")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.output, args.phase)
        print(json.dumps({"scheduled": len(result["schedule"]), "phase": result["phase"]}))
    elif args.command == "run":
        result = execute(args.plan, preflight=args.preflight)
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            parser.exit(1, "Execution/preflight failures retained.\n")
    else:
        result = analyze(args.plan, args.output)
        print(json.dumps({"cells": result["scheduled_cells"], "failures": result["failures"]}))


if __name__ == "__main__":
    main()
