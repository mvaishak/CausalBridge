"""Reproduce the saved ANM failure audit without fitting or inference."""

import argparse
import json
from pathlib import Path

from causalbridge.evaluation.anm_failure_audit import run_audit
from causalbridge.evaluation.anm_failure_report import report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_audit(args.output)
    report(result, args.output / "report.md")
    print(
        json.dumps(
            {
                "archive_files_verified": result["archive_files_verified"],
                "real_attempts_verified": result["real_attempts_verified"],
                "synthetic_attempts_verified": result["synthetic"]["verified_attempts"],
                "primary": result["real"]["primary"],
                "new_fits": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
