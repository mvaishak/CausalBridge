"""Produce explicit outcome categories from a complete, canonically scored saved panel."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.outcome_accounting import account_panel


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--evaluator", type=Path)
    ap.add_argument("--scores", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    def read(path):
        return json.loads(path.read_text())

    result = account_panel(
        [json.loads(line) for line in (args.run / "analysis.jsonl").read_text().splitlines()],
        read(args.evaluator or args.run / "evaluator.json"),
        read(args.run / "evaluation_mapping.json"),
        read(args.scores or args.run / "scores.json"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"case_count": result["case_count"], "contrasts": result["e2_e3_contrasts"]}))


if __name__ == "__main__":
    main()
