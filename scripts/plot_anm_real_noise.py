"""Plot frozen residuals and calibration counts, without changing any test."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    m = json.loads((a.analysis / "metrics.json").read_text())
    records = json.loads((a.analysis / "real-records.json").read_text())
    a.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size": 9, "svg.hashsalt": "anm-real-noise-v1"})
    selected = []
    for panel, pair in [("pilot17", 56), ("pilot17", 88), ("validation38", 92)]:
        selected.append(
            next(
                r
                for r in records
                if r["panel"] == panel
                and r["pair_id"] == pair
                and r["split_seed"] == 261
                and r["direction_tested"] == r["reference"]
            )
        )
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey="col", constrained_layout=True)
    for col, r in enumerate(selected):
        for row, mode in enumerate(("raw", "mean_detrended")):
            v = r["vectors"]
            check = r["modes"][mode]["iid"]
            x = np.asarray(v["cause"])
            xt = np.asarray(v["cause_training"])
            x = (x - xt.mean()) / xt.std()
            residual = np.asarray(v["residual"] if mode == "raw" else v["mean_detrended_residual"])
            axes[row, col].scatter(x, residual, s=19, alpha=0.75, color="#237c69")
            for edge in check.get("edges", []):
                axes[row, col].axvline(edge, color="#777777", ls="--", lw=0.8)
            axes[row, col].axhline(0, color="#555555", lw=0.6)
            pvalue = check.get("pvalue_holm_nominal")
            label = "unavailable" if pvalue is None else f"{pvalue:.3g}"
            axes[row, col].set_title(
                f"{r['panel']} pair {r['pair_id']}: {mode}\nHolm nominal IID p={label}"
            )
            axes[row, col].set_xlabel("Reference cause, training-standardized")
            axes[row, col].set_ylabel("Residual in standardized effect units")
    fig.suptitle(
        "Two candidate pilot cases and one persistently wrong case without a primary flag\n"
        "Residual spread is not proof of structural noise or a causal explanation",
        fontsize=13,
    )
    save(fig, a.output, "case-residuals")
    plt.close(fig)
    labels = ["independent_additive", "constant_noise_quadratic_mean_error", "heteroscedastic"]
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    x = np.arange(3)
    for shift, mode, color in [(-0.2, "raw", "#bb5145"), (0.2, "mean_detrended", "#237c69")]:
        values = [
            next(
                c["nominal_flags"]
                for c in m["calibration"]
                if c["label"] == label and c["mode"] == mode and c["scheme"] == "iid"
            )
            for label in labels
        ]
        bars = ax.bar(x + shift, values, width=0.4, label=mode, color=color)
        ax.bar_label(bars, padding=3)
    ax.set_xticks(
        x, ["Constant noise", "Constant noise +\nquadratic mean error", "Changing noise spread"]
    )
    ax.set_ylim(0, 29)
    ax.set_ylabel("Nominal flags out of 24 paired base worlds")
    ax.set_title("Why residual-mean controls matter: fixed synthetic calibration")
    ax.legend(loc="upper center", ncol=2)
    save(fig, a.output, "calibration")
    plt.close(fig)
    (a.output / "manifest.json").write_text(
        json.dumps(
            {
                "metrics_sha256": hashlib.sha256(
                    (a.analysis / "metrics.json").read_bytes()
                ).hexdigest(),
                "matplotlib": matplotlib.__version__,
                "new_fits": 0,
                "files": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(a.output.iterdir())
                },
            },
            indent=2,
        )
        + "\n"
    )


def save(fig, output, name):
    fig.savefig(output / (name + ".png"), dpi=160)
    fig.savefig(output / (name + ".svg"), metadata={"Date": None})


if __name__ == "__main__":
    main()
