"""Render frozen mechanism-study metrics; no fitting or parameter selection."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metrics", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.metrics.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 10, "svg.hashsalt": "anm-mechanism-v1"})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for col, regime in enumerate(("independent_additive", "heteroscedastic")):
        cells = [c for c in data["cells"] if c["regime"] == regime]
        labels = [f"train {c['n_train']}\neval {c['n_eval']}" for c in cells]
        base = [0] * 4
        for kind, color in (
            ("correct", "#237c69"),
            ("wrong", "#bb5145"),
            ("abstention", "#92989d"),
        ):
            vals = [c["counts"][kind] for c in cells]
            axes[0, col].bar(labels, vals, bottom=base, color=color, label=kind)
            for i, n in enumerate(vals):
                if n:
                    axes[0, col].text(
                        i, base[i] + n / 2, str(n), ha="center", va="center", color="white"
                    )
            base = [a + b for a, b in zip(base, vals, strict=True)]
        axes[0, col].set_ylim(0, 30)
        axes[0, col].set_ylabel("Scheduled base datasets (N=24 per cell)")
        axes[0, col].set_title(regime.replace("_", " ").title())
        axes[0, col].legend(fontsize=8, loc="upper right")
        for name, style, key in (
            ("Learned forward", "o-", "learned_forward_rejections"),
            ("Oracle forward", "s--", "oracle_forward_rejections"),
        ):
            axes[1, col].plot(labels, [c[key] for c in cells], style, label=name)
        axes[1, col].set_ylim(-0.5, 25)
        axes[1, col].set_ylabel("Forward dependence rejections out of 24")
        axes[1, col].grid(alpha=0.2)
        axes[1, col].legend(fontsize=8)
    fig.suptitle(
        "ANM: fitting, evaluation size and one assumption violation\n"
        "Paired synthetic pilot; not a diagnosis of specific real datasets",
        fontsize=14,
    )
    fig.savefig(args.output / "mechanism-overview.png", dpi=160)
    fig.savefig(args.output / "mechanism-overview.svg", metadata={"Date": None})
    plt.close(fig)
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "metrics_sha256": hashlib.sha256(args.metrics.read_bytes()).hexdigest(),
                "matplotlib": matplotlib.__version__,
                "new_fits": 0,
                "files": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(args.output.iterdir())
                },
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
