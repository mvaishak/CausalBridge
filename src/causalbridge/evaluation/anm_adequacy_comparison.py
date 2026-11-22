"""Frozen, label-blind abstention-rule replay; no ANM refits or live inference."""

import math
from collections import Counter
from pathlib import Path

from causalbridge.discovery.schemas import canonical_digest
from causalbridge.evaluation.anm_failure_audit import outcome, ratio, read, sha, write

CONFIG = Path("configs/anm-adequacy-policy-comparison-v1.json")
AUDIT = Path("artifacts/anm-decision-audit-20261121")
METADATA = Path("artifacts/anm-real-noise-20261121/real-records.json")
KINDS = ("correct", "wrong", "abstention", "execution_failure")


def verify_inventory(path):
    """Integrity check of the audit's evidence, not scientific validity certification."""
    for entry in read(path)["files"]:
        if sha(entry["path"]) != entry["sha256"]:
            raise ValueError("Audit evidence inventory mismatch: " + entry["path"])


def adequacy(directions, scheme, alpha):
    """Describe rejections; unavailable values must never become nonrejection evidence."""
    rejected = {}
    for direction in ("A_to_B", "B_to_A"):
        value = directions.get(direction, {}).get(scheme, {}).get("pvalue_nominal")
        if value is None:
            rejected[direction] = None
        elif (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("Invalid nominal p-value")
        else:
            rejected[direction] = value <= alpha
    status = (
        "unavailable"
        if None in rejected.values()
        else ("neither_rejected", "one_rejected", "both_rejected")[sum(rejected.values())]
    )
    return {"status": status, "rejected": rejected}


def apply_policy(direction, diagnostic, policy):
    """Use only original preference and diagnostic flags, never reference labels."""
    if policy not in (
        "original",
        "warning_only",
        "withhold_if_both_rejected",
        "withhold_if_selected_rejected",
        "require_unique_nonrejected",
    ):
        raise ValueError("Unknown policy")
    if direction not in (None, "A_to_B", "B_to_A"):
        raise ValueError("Invalid original direction")
    if direction is None:
        return None, "original_nondirection"
    if policy in ("original", "warning_only"):
        return direction, "original_direction_retained"
    if diagnostic["status"] == "unavailable":
        return None, "diagnostic_unavailable"
    rejected = diagnostic["rejected"]
    opposite = "B_to_A" if direction == "A_to_B" else "A_to_B"
    blocked = (
        diagnostic["status"] == "both_rejected"
        if policy == "withhold_if_both_rejected"
        else rejected[direction]
        if policy == "withhold_if_selected_rejected"
        else rejected[direction] or not rejected[opposite]
    )
    return (None, "policy_withheld") if blocked else (direction, "original_direction_retained")


def summarize(rows):
    """Explicit pre-LLM/pre-checker denominators and paired removals; no accuracy-only claim."""
    counts = {kind: sum(r["policy_outcome"] == kind for r in rows) for kind in KINDS}
    if sum(counts.values()) != len(rows):
        raise ValueError("Nonpartitioning outcomes")
    n = len(rows)
    answered = counts["correct"] + counts["wrong"]
    weighted = {
        kind: sum(r["weight"] for r in rows if r["policy_outcome"] == kind) for kind in KINDS
    }
    total_weight = sum(r["weight"] for r in rows)
    return {
        "n": n,
        "source_groups": len({r["source_group"] for r in rows}),
        "counts": counts,
        "correct_yield": ratio(counts["correct"], n),
        "wrong_yield": ratio(counts["wrong"], n),
        "abstention_rate": ratio(counts["abstention"], n),
        "execution_failure_rate": ratio(counts["execution_failure"], n),
        "coverage": ratio(answered, n),
        "directional_accuracy": ratio(counts["correct"], answered),
        "original_abstentions": sum(r["original_outcome"] == "abstention" for r in rows),
        "added_policy_abstentions": sum(
            r["original_direction"] is not None
            and r["policy_direction"] is None
            and r["policy_outcome"] == "abstention"
            for r in rows
        ),
        "wrong_answers_removed": sum(
            r["original_outcome"] == "wrong" and r["policy_outcome"] == "abstention" for r in rows
        ),
        "correct_answers_lost": sum(
            r["original_outcome"] == "correct" and r["policy_outcome"] == "abstention" for r in rows
        ),
        "diagnostic_states": dict(sorted(Counter(r["adequacy"]["status"] for r in rows).items())),
        "transitions": dict(
            sorted(
                Counter(r["original_outcome"] + "->" + r["policy_outcome"] for r in rows).items()
            )
        ),
        "weighted": {
            "counts": weighted,
            "total_weight": total_weight,
            "directional_accuracy": ratio(
                weighted["correct"], weighted["correct"] + weighted["wrong"]
            ),
            "correct_yield": ratio(weighted["correct"], total_weight),
            "wrong_yield": ratio(weighted["wrong"], total_weight),
        },
    }


def prepare(plan):
    """Copy hash-verified saved evidence and fixed rules before calculating policy metrics."""
    plan = Path(plan)
    plan.mkdir(parents=True, exist_ok=False)
    verify_inventory(AUDIT / "source-manifest.json")
    audit = read(AUDIT / "records.json")
    if canonical_digest(audit) != read(AUDIT / "completion.json")["records_digest"]:
        raise ValueError("Audit record binding mismatch")
    cfg = read(CONFIG)
    metadata = {
        (r["panel"], r["pair_id"]): r
        for r in read(METADATA)
        if r["split_seed"] == 261 and r["direction_tested"] == r["reference"]
    }
    rows = []
    for row in audit:
        meta = metadata[row["panel"], row["pair_id"]]
        for key in (
            "request_digest",
            "result_digest",
            "reference",
            "original_direction",
            "original_outcome",
        ):
            if row[key] != meta[key]:
                raise ValueError("Metadata does not match saved audit: " + key)
        if not math.isfinite(meta["weight"]) or meta["weight"] <= 0:
            raise ValueError("Invalid source weight")
        rows.append({**row, "weight": meta["weight"], "source_group": meta["source_group"]})
    if dict(Counter(r["panel"] for r in rows)) != cfg["panels"]:
        raise ValueError("Missing or duplicated cases")
    if len({(r["panel"], r["pair_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate pair")
    write(plan / "inputs.json", rows)
    sources = [
        CONFIG,
        Path("scripts/anm_adequacy_comparison.py"),
        Path("src/causalbridge/evaluation/anm_adequacy_comparison.py"),
        Path("src/causalbridge/evaluation/anm_failure_audit.py"),
        Path("uv.lock"),
    ]
    evidence = [
        AUDIT / "records.json",
        AUDIT / "completion.json",
        AUDIT / "source-manifest.json",
        METADATA,
    ]
    manifest = {
        "protocol": cfg,
        "inputs_digest": canonical_digest(rows),
        "source_sha256": {str(p): sha(p) for p in sources},
        "evidence_sha256": {str(p): sha(p) for p in evidence},
        "scope": (
            "Opened-data replay; no new fits/permutations or LLM inference;"
            " no production rule change."
        ),
    }
    write(plan / "manifest.json", manifest)
    return manifest


def calculate(inputs, cfg):
    """Retain every scheduled case and report all fixed policies and sensitivity schemes."""
    records = []
    for original in inputs:
        for scheme in cfg["schemes"]:
            diagnostic = adequacy(original["directions"], scheme, cfg["alpha"])
            for policy in cfg["policies"]:
                direction, reason = apply_policy(original["original_direction"], diagnostic, policy)
                status = original["original_outcome"]
                result = (
                    status
                    if status == "execution_failure"
                    else outcome(direction, original["reference"])
                )
                records.append(
                    {
                        **{
                            k: original[k]
                            for k in (
                                "panel",
                                "pair_id",
                                "reference",
                                "source_group",
                                "weight",
                                "request_digest",
                                "result_digest",
                                "original_direction",
                                "original_outcome",
                            )
                        },
                        "scheme": scheme,
                        "policy": policy,
                        "adequacy": diagnostic,
                        "policy_direction": direction,
                        "policy_outcome": result,
                        "reason": reason,
                    }
                )
    tables = []
    groups = []
    for panel in cfg["panels"]:
        for scheme in cfg["schemes"]:
            for policy in cfg["policies"]:
                selected = [
                    r
                    for r in records
                    if r["panel"] == panel and r["scheme"] == scheme and r["policy"] == policy
                ]
                tables.append(
                    {"panel": panel, "scheme": scheme, "policy": policy, **summarize(selected)}
                )
                for source in sorted({r["source_group"] for r in selected}):
                    groups.append(
                        {
                            "panel": panel,
                            "scheme": scheme,
                            "policy": policy,
                            "source_group": source,
                            **summarize([r for r in selected if r["source_group"] == source]),
                        }
                    )
    return records, {
        "protocol": cfg,
        "tables": tables,
        "source_groups": groups,
        "scope": (
            "ANM diagnostic decisions before any LLM or verification "
            "checker; verification rejection not applicable."
        ),
    }


def markdown(metrics):
    lines = [
        "# Fixed adequacy-policy replay",
        "",
        (
            "Exploratory opened cases, unchanged original preferences. No "
            "refits, permutation reruns, or deployed policy. "
        )
        + (
            "IID checks are nominal; blocks are a saved-order heuristic. "
            "Nonrejection is not proof of independence. "
        )
        + ("Warning-only is an annotation and deliberately has the same outcomes as original."),
        "",
        (
            "| Panel | Scheme | Policy | N | Correct | Wrong | Abstained | "
            "Execution failures | Coverage | Directional accuracy | Wrong "
            "removed | Correct lost | Added abstentions |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for table in metrics["tables"]:
        counts = table["counts"]

        def display(metric):
            return f"{metric['numerator']}/{metric['denominator']}" + (
                f" ({metric['rate']:.1%})" if metric["rate"] is not None else " (undefined)"
            )

        values = [
            table["panel"],
            table["scheme"],
            table["policy"],
            table["n"],
            counts["correct"],
            counts["wrong"],
            counts["abstention"],
            counts["execution_failure"],
            display(table["coverage"]),
            display(table["directional_accuracy"]),
            table["wrong_answers_removed"],
            table["correct_answers_lost"],
            table["added_policy_abstentions"],
        ]
        lines.append("| " + " | ".join(str(v) for v in values) + " |")
    lines += [
        "",
        (
            "All yields use all scheduled cases in that panel (17 or 38). "
            "Accuracy uses directional answers only. "
        )
        + (
            "Original abstention and added policy withholding are separate "
            "in JSON. No answer is flipped; a rule "
        )
        + ("can retain a direction or withhold it, so it cannot increase correct-answer yield."),
        "",
        (
            "Complete case-level transitions, source-group breakdowns and "
            "source-weighted descriptive metrics "
        )
        + (
            "are in JSON. No policy is selected as a winner; new held-out "
            "evaluation is outside this replay."
        ),
    ]
    return "\n".join(lines) + "\n"


def execute(plan, output, *, replay=False):
    """Deterministically replay the frozen inputs; fail rather than overwrite outputs."""
    plan, output = Path(plan), Path(output)
    manifest = read(plan / "manifest.json")
    if not replay:
        if manifest["protocol"] != read(CONFIG):
            raise ValueError("Protocol changed after freeze")
        for path, digest in {**manifest["source_sha256"], **manifest["evidence_sha256"]}.items():
            if sha(path) != digest:
                raise ValueError("Frozen source/evidence changed")
    inputs = read(plan / "inputs.json")
    if canonical_digest(inputs) != manifest["inputs_digest"]:
        raise ValueError("Frozen inputs changed")
    output.mkdir(parents=True, exist_ok=False)
    rows, metrics = calculate(inputs, manifest["protocol"])
    metrics["manifest_digest"] = canonical_digest(manifest)
    write(output / "case-results.json", rows)
    write(output / "metrics.json", metrics)
    (output / "tables.md").write_text(markdown(metrics))
    return metrics
