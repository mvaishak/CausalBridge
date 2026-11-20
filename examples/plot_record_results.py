"""Plot saved baseline accuracy/coverage without treating nonanswers as correct."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads((args.results / "baseline-comparisons.json").read_text())
    points, undefined = defaultdict(list), []
    for row in rows:
        if row["selective_accuracy"] is None:
            undefined.append(row["package"] + "/" + row["condition"])
        else:
            key = (row["package"], round(row["coverage"], 12), round(row["selective_accuracy"], 12))
            points[key].append(row["condition"])
    colors = {"E1": "#3b6b9c", "E2": "#b4792a", "E3": "#247f78", "E4": "#77569c"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(10, 6.4))
    used = set()
    for (package, coverage, accuracy), conditions in points.items():
        x, y = coverage * 100, accuracy * 100
        ax.scatter(
            x,
            y,
            s=95,
            color=colors[package],
            label=package if package not in used else None,
            zorder=3,
        )
        used.add(package)
        labels = [
            "gate" if c == "SIMPLE_GATE" else "ANM" if c == "ANM_ONLY" else c for c in conditions
        ]
        label = package + ": " + "/".join(labels)
        if package == "E2":
            label += " (2 answered cases)"
        if package == "E4":
            offset, align = (-12, 18), "right"
        elif accuracy == 0:
            offset, align = (10, 22), "left"
        elif package == "E1" and "S0" in conditions:
            offset, align = (12, -18), "left"
        else:
            offset, align = (10, -18 if accuracy == 1 else 16), "left"
        ax.annotate(
            label,
            (x, y),
            xytext=offset,
            textcoords="offset points",
            ha=align,
            fontsize=10,
            arrowprops={"arrowstyle": "-", "color": colors[package], "linewidth": 0.7},
        )
    ax.set(
        xlim=(0, 100),
        ylim=(-5, 110),
        xlabel="Released direction coverage (% of benchmark weight)",
        ylabel="Accuracy among released directions (% of benchmark weight)",
    )
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.grid(color="#e4e7eb", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False)
    ax.set_title(
        "Coverage and answered accuracy are separate outcomes",
        loc="left",
        fontsize=15,
        fontweight="bold",
        pad=18,
    )
    fig.text(
        0.1,
        0.01,
        "Opened pilot: 17 pairs / 7 source groups. Overlapping baselines are labeled together.\n"
        "Undefined accuracy (no releases): " + ", ".join(undefined),
        fontsize=9,
        color="#555d66",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(args.results / ("accuracy-coverage." + ext), dpi=180, facecolor="white")
    plt.close(fig)
    provenance = json.loads((args.results / "provenance.json").read_text())
    root = Path(__file__).resolve().parents[1]
    provenance["source_sha256"][str(Path(__file__).resolve().relative_to(root))] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    for path in args.results.glob("accuracy-coverage.*"):
        provenance["output_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (args.results / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


if __name__ == "__main__":
    main()
