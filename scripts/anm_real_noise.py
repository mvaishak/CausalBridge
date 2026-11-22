"""Prepare, run and replay the real-pair residual-spread investigation."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_real_noise import analyze, execute, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", type=Path, required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.output)
        print(
            json.dumps({"real_attempts": len(result["real"]), "controls": len(result["controls"])})
        )
    elif args.command == "run":
        result = execute(args.plan)
        print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
    else:
        result = analyze(args.plan, args.output, replay=args.replay)
        print(json.dumps(result["tables"], indent=2))


if __name__ == "__main__":
    main()
