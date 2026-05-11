"""Render the 32-spec OLS multiverse curve with documented-run anchors.

Re-creates logs/multiverse_curve.png with iter06, iter09 (kept best) and
iter10 (hard-rule discard) marked on the curve. This is the figure
referenced in Q3.2 of the write-up.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_CURVE_CSV = REPO_ROOT / "logs" / "spec_curve.csv"
OUT_PNG = REPO_ROOT / "logs" / "multiverse_curve.png"

ANCHORS = [
    ("iter06: trim ±1% (KEEP)",        0.0647, "#2ca02c", "o"),
    ("iter09: trim ±2.5% (KEEP, best)", 0.0569, "#d62728", "*"),
    ("iter10: trim ±5% (DISCARD, hard-rule)", 0.0510, "#9467bd", "X"),
    ("baseline (KEEP)",                 0.0715, "#1f77b4", "s"),
    ("multiverse 5% bound",             0.0508, None, None),
    ("multiverse 95% bound",            0.0903, None, None),
]


def main() -> None:
    curve = pd.read_csv(SPEC_CURVE_CSV).sort_values("educ_coef").reset_index(drop=True)
    n = len(curve)
    print(f"Loaded {n} multiverse specs.")

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Spec curve with 95% CI
    ax.errorbar(np.arange(n), curve["educ_coef"],
                yerr=1.96 * curve["educ_se"], fmt="o", ms=4,
                color="#7f7f7f", ecolor="#cccccc", alpha=0.85,
                label=f"OLS multiverse (n={n})")

    # Median and 5/95 band
    med = float(np.median(curve["educ_coef"]))
    p5, p95 = float(np.quantile(curve["educ_coef"], 0.05)), float(np.quantile(curve["educ_coef"], 0.95))
    ax.axhline(med, color="black", lw=1, ls="--", label=f"multiverse median = {med:.4f}")
    ax.axhspan(p5, p95, color="#cccccc", alpha=0.35,
               label=f"5/95 band = [{p5:.4f}, {p95:.4f}]")

    # Anchors
    label_iter, val_iter, col_iter, mark_iter = ANCHORS[0]
    ax.axhline(val_iter, color=col_iter, lw=1.5, ls=":", label=label_iter)
    label_iter, val_iter, col_iter, mark_iter = ANCHORS[1]
    ax.axhline(val_iter, color=col_iter, lw=2.0, ls="-", label=label_iter)
    label_iter, val_iter, col_iter, mark_iter = ANCHORS[2]
    ax.axhline(val_iter, color=col_iter, lw=1.5, ls=":", label=label_iter)
    label_iter, val_iter, col_iter, mark_iter = ANCHORS[3]
    ax.axhline(val_iter, color=col_iter, lw=1.0, ls="-.", label=label_iter)

    # Annotations for iter09 (kept best) and iter10 (hard-rule discard)
    ax.annotate("iter09 (KEEP, 5/5) —\nkept best", xy=(n - 1, 0.0569),
                xytext=(n - 1, 0.045), fontsize=9, ha="right",
                arrowprops=dict(arrowstyle="->", color="#d62728"))
    ax.annotate("iter10 (DISCARD) —\neduc=0.051 < 5%-bound 0.0508\nhard identification rule fired",
                xy=(0, 0.0510), xytext=(0.5, 0.040), fontsize=9, ha="left",
                arrowprops=dict(arrowstyle="->", color="#9467bd"))

    ax.set_xlabel("OLS multiverse specifications, sorted by educ coefficient")
    ax.set_ylabel("educ coefficient (return to one additional year of schooling)")
    ax.set_title("Specification curve — Card 1995 multiverse with documented-run anchors\n"
                 "(iter09 kept best, iter10 blocked by hard identification rule)")
    ax.legend(loc="upper left", fontsize=8, ncols=2)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {OUT_PNG}")


if __name__ == "__main__":
    main()
