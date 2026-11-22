"""Generate transparent spread-flag tables; no automatic causal interpretation."""

import argparse
import json
from pathlib import Path


def fmt(value):
    return "unavailable" if value is None else f"{value:.4g}"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError("Use a new report path")
    m = json.loads((a.analysis / "metrics.json").read_text())
    records = json.loads((a.analysis / "real-records.json").read_text())
    lines = [
        "# Real-pair residual-spread tables",
        "",
        "**Exploratory diagnostics. Flags are not proof of changing structural "
        "noise or causal failure.**",
        "",
        "Both panels retain their original predictions. Unavailable diagnostics "
        "are not negative tests. "
        "Nominal randomization assumes exchangeability; saved-row-order blocks are a heuristic, "
        "not a validated dependence correction. Multiplicity correction "
        "does not fix invalid assumptions.",
        "",
        "## Reference-direction primary outcomes",
        "",
        "| Panel | Form | Scheme | Original outcome | Scheduled | Available | "
        "Nominal flags | Holm nominal flags |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for r in m["tables"]:
        lines.append(
            f"| {r['panel']} | {r['mode']} | {r['scheme']} | {r['original_outcome']} | "
            f"{r['scheduled_pairs']} | {r['available']} | {r['nominal_flags']} | "
            f"{r['holm_nominal_flags']} |"
        )
    lines += [
        "",
        "## Known residual controls (nominal .05; not fresh validation)",
        "",
        "| Control | Form | Scheme | N | Available | Flags |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in m["calibration"]:
        lines.append(
            f"| {r['label']} | {r['mode']} | {r['scheme']} | "
            f"{r['n']} | {r['available']} | {r['nominal_flags']} |"
        )
    lines += [
        "",
        "## Every primary reference-direction case",
        "",
        "Adjusted p-values are from separate directional families (34 or 76 tests). "
        "A blank diagnostic does not imply constant variance. Ratios are of mean absolute "
        "deviations from bin medians, not ratios of structural noise variances.",
        "",
        "| Panel | Pair | Outcome | N eval | Raw ratio | Detrended ratio | "
        "Raw IID adjusted p | Detrended IID adjusted p | Detrended block adjusted p |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(records, key=lambda r: (r["panel"], r["pair_id"])):
        if r["split_seed"] != 261 or r["direction_tested"] != r["reference"]:
            continue
        raw = r["modes"]["raw"]["iid"]
        d = r["modes"]["mean_detrended"]["iid"]
        b = r["modes"]["mean_detrended"]["saved_order_blocks"]
        lines.append(
            f"| {r['panel']} | {r['pair_id']} | {r['original_outcome']} | "
            f"{len(r['vectors']['cause'])} | "
            f"{fmt(raw.get('spread_ratio'))} | {fmt(d.get('spread_ratio'))} | "
            f"{fmt(raw.get('pvalue_holm_nominal'))} | {fmt(d.get('pvalue_holm_nominal'))} | "
            f"{fmt(b.get('pvalue_holm_nominal'))} |"
        )
    lines += [
        "",
        "## Persistent wrong cases across saved splits",
        "",
        "| Pair | Split | Raw IID adjusted p | Detrended IID adjusted p | "
        "Detrended block adjusted p |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in sorted(records, key=lambda r: (r["pair_id"], r["split_seed"])):
        if (
            r["panel"] == "validation38"
            and r["pair_id"] in (91, 92, 108)
            and r["direction_tested"] == r["reference"]
        ):
            raw = r["modes"]["raw"]["iid"]
            d = r["modes"]["mean_detrended"]["iid"]
            b = r["modes"]["mean_detrended"]["saved_order_blocks"]
            lines.append(
                f"| {r['pair_id']} | {r['split_seed']} | {fmt(raw.get('pvalue_holm_nominal'))} | "
                f"{fmt(d.get('pvalue_holm_nominal'))} | {fmt(b.get('pvalue_holm_nominal'))} |"
            )
    lines += [
        "",
        "Original ANM C/W/A totals: pilot 6/8/3; later primary 13/13/12. "
        "No new ANM direction is selected, and reference labels remain fallible. "
        "All opposite-direction values, split sensitivities and vectors are preserved in JSON.",
    ]
    a.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
