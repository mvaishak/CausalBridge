"""Explicit CLI for offline preparation, bounded live execution and saved-result replay."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.diagnostic_analysis import analyze, diagnose
from causalbridge.evaluation.diagnostic_protocol import prepare, read
from causalbridge.evaluation.diagnostic_runtime import run


def smoke(output):
    """All 170 planned cells, no endpoint/model/network; never research evidence."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    prepare(output / "preflight-plan", preflight=True)
    prepare(output / "full-plan")
    run(output / "preflight-plan", output / "preflight-run", scripted=True)
    run(output / "full-plan", output / "full-run", scripted=True)
    result = analyze(output / "full-plan", output / "full-run", output / "analysis")
    if result["scheduled"] != 170 or result["research_result"]:
        raise ValueError("Smoke fixture mislabeled or incomplete")
    for cell in result["cells"]:
        expected = (
            "abstention"
            if cell["arm"] == "no_diagnostic"
            else ("wrong" if cell["arm"].startswith("wrong") else "correct")
        )
        if cell["counts"][expected] != 17 or cell["counts"]["execution_failure"]:
            raise ValueError("Unexpected scripted response scoring")
    return {
        "passed": True,
        "mode": "scripted",
        "live_calls": 0,
        "preflight_observations": 20,
        "full_observations": 170,
        "message": "Software plumbing only; no evidence of model performance.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("diagnose", "smoke"):
        p = sub.add_parser(command)
        p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--phase", choices=["preflight", "full"], required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--base-url")
    p.add_argument("--scripted", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--preflight-run", type=Path)
    p = sub.add_parser("analyze")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "diagnose":
        result = diagnose(args.output)
    elif args.command == "prepare":
        result = prepare(args.output, preflight=args.phase == "preflight")
    elif args.command == "run":
        result = run(
            args.plan,
            args.output,
            base_url=args.base_url,
            scripted=args.scripted,
            gate=args.preflight_run,
            resume=args.resume,
        )
    elif args.command == "analyze":
        result = analyze(args.plan, args.run, args.output)
    else:
        result = smoke(args.output)
    if args.command == "smoke":
        print(json.dumps(result, indent=2))
    elif args.command == "run":
        print(json.dumps(result, indent=2))
        if (
            read(args.plan / "manifest.json")["phase"] == "preflight"
            and not result["preflight_passed"]
        ):
            parser.exit(1, "Preflight failed; preserve artifacts and do not start full run.\n")
    else:
        print(json.dumps({"command": args.command, "output": str(args.output), "completed": True}))


if __name__ == "__main__":
    main()
