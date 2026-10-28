"""CLI for Workstream C smoke tests and condition-D integration, not A–E scoring."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from causalbridge.demo import demo_runs
from causalbridge.llm.client import ModelConfig, OllamaModel
from causalbridge.pipeline import CausalBridge, RunTrace
from causalbridge.schemas import Proposal, Query, RuntimeCase, ToolRequest, ToolResult, Verdict
from causalbridge.tools.reference import ReferenceBackend
from causalbridge.verifier.contracts import abstention


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="CausalBridge: Vaishak's Workstream C")
    commands = root.add_subparsers(dest="command", required=True)
    for command in ("demo", "run"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--output", type=Path, required=True, help="New JSONL trace file")
        cmd.add_argument("--overwrite", action="store_true")
        if command == "run":
            cmd.add_argument(
                "--input", type=Path, required=True, help="Runtime cases, one JSON object per line"
            )
            cmd.add_argument("--config", type=Path)
            cmd.add_argument(
                "--benchmark-rows",
                action="store_true",
                help="Project dataset rows onto visible fields",
            )
            cmd.add_argument("--numeric-tolerance", type=float, default=1e-3)
            cmd.add_argument("--sign-tolerance", type=float, default=1e-9)
    cmd = commands.add_parser("schemas")
    cmd.add_argument("--output", type=Path, required=True)
    return root


def export_schemas(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, model in {
        "runtime_case": RuntimeCase,
        "query": Query,
        "proposal": Proposal,
        "tool_request": ToolRequest,
        "tool_result": ToolResult,
        "verdict": Verdict,
        "run_trace": RunTrace,
        "model_config": ModelConfig,
    }.items():
        (folder / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8"
        )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "schemas":
            export_schemas(args.output)
            print(f"Exported runtime contracts to {args.output}")
            return 0
        if args.command == "run" and args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output paths must differ")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        counts = Counter()
        with args.output.open("w" if args.overwrite else "x", encoding="utf-8") as output:
            if args.command == "demo":
                for trace in demo_runs():
                    output.write(trace.model_dump_json() + "\n")
                    counts[trace.verdict.status] += 1
                    print(
                        f"{trace.runtime_case.case_id}: {trace.verdict.status} / "
                        f"{trace.verdict.response_action} / {trace.verdict.answer}"
                    )
                print("Scripted fixtures only; these are not LLM evaluation results.")
            else:
                config = (
                    ModelConfig.model_validate_json(args.config.read_text())
                    if args.config
                    else ModelConfig()
                )
                bridge = CausalBridge(
                    OllamaModel(config),
                    ReferenceBackend(),
                    numeric_tolerance=args.numeric_tolerance,
                    sign_tolerance=args.sign_tolerance,
                )
                with args.input.open(encoding="utf-8") as source:
                    for line_number, line in enumerate(source, start=1):
                        if not line.strip():
                            continue
                        try:
                            raw = json.loads(line)
                            case = (
                                RuntimeCase.from_benchmark(raw)
                                if args.benchmark_rows
                                else RuntimeCase.model_validate(raw)
                            )
                            trace = bridge.run(case)
                            output.write(trace.model_dump_json() + "\n")
                            counts[trace.verdict.status] += 1
                        except (ValueError, TypeError) as exc:
                            verdict = abstention("execution_error", "invalid_input", str(exc))
                            output.write(
                                json.dumps(
                                    {
                                        "schema_version": "1.0",
                                        "input_line": line_number,
                                        "verdict": verdict.model_dump(mode="json"),
                                    }
                                )
                                + "\n"
                            )
                            counts["execution_error"] += 1
                        output.flush()
        print(f"Saved {sum(counts.values())} traces to {args.output}; statuses: {dict(counts)}")
        return 1 if counts["execution_error"] else 0
    except (OSError, ValueError) as exc:
        print(f"causalbridge: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
