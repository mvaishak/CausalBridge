"""Plot saved audit metrics only. Optional renderer: matplotlib==3.10.6."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = {"correct": "#237c69", "wrong": "#bb5145", "abstention": "#92989d"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metrics_path = args.analysis / "metrics.json"
    data = json.loads(metrics_path.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 10, "svg.hashsalt": "anm-failure-audit-v1"})
    rows = data["real"]["case_results"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    for kind, color in COLORS.items():
        selected = [r for r in rows if r["outcome"] == kind]
        for ax, field, label in (
            (axes[0, 0], "selected_rows", "Selected observations"),
            (axes[0, 1], "max_tie_fraction", "Largest repeated-value fraction in either column"),
        ):
            ax.scatter(
                [r["quality"][field] for r in selected],
                [r["absolute_margin"] for r in selected],
                label=f"{kind} (n={len(selected)})",
                c=color,
                alpha=0.8,
                s=42,
            )
            ax.set_xlabel(label)
            ax.set_ylabel("Absolute HSIC margin (log scale)")
            ax.set_yscale("log")
    for ax in axes[0]:
        ax.axhline(0.001, color="#333333", ls="--", lw=0.8, label="Frozen threshold .001")
        ax.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].set_title("Real-data association is confounded with source family")
    axes[0, 1].set_title("Tied values occur in correct and wrong cases")
    ax = axes[1, 0]
    seeds = list(data["real"]["splits"])
    base = [0] * len(seeds)
    for kind, color in COLORS.items():
        values = [data["real"]["splits"][seed]["counts"][kind] for seed in seeds]
        ax.bar(seeds, values, bottom=base, color=color, label=kind)
        for i, value in enumerate(values):
            if value:
                ax.text(i, base[i] + value / 2, str(value), ha="center", va="center", color="white")
        base = [b + v for b, v in zip(base, values, strict=True)]
    ax.set_ylabel("Cases (same 38 pairs)")
    ax.set_xlabel("Split seed; dependent sensitivity checks")
    ax.set_title("Split outcomes differ; none replaces primary seed 261")
    ax = axes[1, 1]
    cells = [c for c in data["synthetic"]["compatible_panels"] if c["split_seed"] == 261]
    labels = [f"{c['partition']}\n{c['n_rows']} rows" for c in cells]
    base = [0] * len(cells)
    for kind, color in COLORS.items():
        values = [c["counts"][kind] for c in cells]
        ax.bar(labels, values, bottom=base, color=color, label=kind)
        for i, value in enumerate(values):
            if value:
                ax.text(i, base[i] + value / 2, str(value), ha="center", va="center", color="white")
        base = [b + v for b, v in zip(base, values, strict=True)]
    ax.set_ylabel("Compatible synthetic datasets (32 per partition)")
    ax.set_title("Larger nested samples remove wrong releases here")
    fig.suptitle(
        "ANM failure audit: descriptive evidence, not an identified root cause", fontsize=14
    )
    save(fig, args.output, "overview")
    plt.close(fig)

    groups = data["real"]["source_groups"]
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    base = [0] * len(groups)
    names = list(groups)
    for kind, color in COLORS.items():
        values = [groups[name]["counts"][kind] for name in names]
        ax.barh(names, values, left=base, label=kind, color=color)
        base = [b + v for b, v in zip(base, values, strict=True)]
    ax.set_xlabel("Primary-split cases; family sizes differ")
    ax.set_title("Source families: 38 pairs in 12 groups (exploratory)")
    ax.legend()
    save(fig, args.output, "source-families")
    plt.close(fig)
    manifest = {
        "metrics_sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
        "matplotlib": matplotlib.__version__,
        "new_fits": 0,
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.output.iterdir())
        },
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def save(fig, output, name):
    fig.savefig(output / (name + ".png"), dpi=160)
    fig.savefig(output / (name + ".svg"), metadata={"Date": None})


if __name__ == "__main__":
    main()
