"""Appendix multiverse — ~200 specifications sweeping OLS and IV.

Produced as a robustness appendix to the documented 13-iteration run.
Does NOT replace `prepare.py::specification_curve` (which stays at 32 specs
to keep the main loop fast). This script is run once, offline, to produce
a deeper multiverse picture for the write-up.

No new dependencies: uses statsmodels only.

Outputs:
  logs/big_multiverse.csv               — raw spec-level results
  logs/big_multiverse_summary.json      — quantile summaries
  logs/big_multiverse_figure.png        — specification-curve figure
"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from prepare import first_stage_f, load_card_data


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "logs"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Multiverse axes
# ---------------------------------------------------------------------------
DEMO = ["black", "south", "smsa"]
REGION = [f"reg66{i}" for i in range(2, 10)]
ABILITY = ["IQ", "KWW"]
FAMILY = ["momdad14"]

CONTROL_MENUS: list[tuple[str, list[str]]] = [
    ("none", []),
    ("demo", DEMO),
    ("demo+married", DEMO + ["married"]),
    ("demo+region", DEMO + REGION),
    ("demo+region+married", DEMO + REGION + ["married"]),
    ("demo+ability", DEMO + ABILITY),
    ("demo+ability+married", DEMO + ABILITY + ["married"]),
    ("demo+family", DEMO + FAMILY),
    ("demo+family+married", DEMO + FAMILY + ["married"]),
    ("demo+region+ability", DEMO + REGION + ABILITY),
    ("demo+region+ability+married", DEMO + REGION + ABILITY + ["married"]),
]

SAMPLE_MENUS: list[tuple[str, callable]] = [
    ("full", lambda d: d),
    ("trim_top1", lambda d: d[d["lwage"] <= d["lwage"].quantile(0.99)]),
    ("trim_top_bot_1", lambda d: d[(d["lwage"] >= d["lwage"].quantile(0.01))
                                   & (d["lwage"] <= d["lwage"].quantile(0.99))]),
    ("trim_top_bot_25", lambda d: d[(d["lwage"] >= d["lwage"].quantile(0.025))
                                    & (d["lwage"] <= d["lwage"].quantile(0.975))]),
    ("momdad14_only", lambda d: d[d.get("momdad14", 1) == 1]),
]

COV_TYPES = ["nonrobust", "HC3"]

INSTRUMENT_MENUS = [
    ("nearc4", ["nearc4"]),
    ("nearc2", ["nearc2"]),
    ("nearc4+nearc2", ["nearc4", "nearc2"]),
]


def _design(sub: pd.DataFrame, controls: list[str]) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    sub = sub.dropna(subset=["lwage", "educ", "exper"] + controls).copy()
    sub["exper_c"] = sub["exper"] - sub["exper"].mean()
    sub["expersq_c"] = sub["exper_c"] ** 2
    cols = ["educ", "exper_c", "expersq_c"] + [c for c in controls if c not in {"exper", "expersq"}]
    y = sub["lwage"].astype(float).values
    X = sm.add_constant(sub[cols].astype(float).values)
    return y, X, sub


def _iv_design(sub: pd.DataFrame, controls: list[str], inst_cols: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    sub = sub.dropna(subset=["lwage", "educ", "exper"] + controls + inst_cols).copy()
    sub["exper_c"] = sub["exper"] - sub["exper"].mean()
    sub["expersq_c"] = sub["exper_c"] ** 2
    exog_cols = ["educ", "exper_c", "expersq_c"] + [c for c in controls if c not in {"exper", "expersq"}]
    exog_no_educ = ["exper_c", "expersq_c"] + [c for c in controls if c not in {"exper", "expersq"}]
    y = sub["lwage"].astype(float).values
    X = sm.add_constant(sub[exog_cols].astype(float).values)
    Z = sm.add_constant(sub[exog_no_educ + inst_cols].astype(float).values)
    return y, X, Z, sub


def run_ols_multiverse(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cname, controls), (sname, restrict), cov in product(CONTROL_MENUS, SAMPLE_MENUS, COV_TYPES):
        try:
            sub = restrict(df)
            y, X, sub = _design(sub, controls)
            if len(y) < 200:
                continue
            fit = sm.OLS(y, X).fit(cov_type=cov)
            rows.append({
                "estimator": "OLS",
                "controls": cname,
                "sample": sname,
                "cov": cov,
                "instrument": "NA",
                "n": int(len(y)),
                "educ_coef": float(fit.params[1]),
                "educ_se": float(fit.bse[1]),
                "educ_p": float(fit.pvalues[1]),
                "first_stage_F": np.nan,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def run_iv_multiverse(df: pd.DataFrame) -> pd.DataFrame:
    # Skip control menus that already contain ability proxies on the
    # non-missing-IQ subsample (over-restrictive); keep menus tractable.
    iv_control_menus = [(n, c) for n, c in CONTROL_MENUS if "IQ" not in c]
    rows = []
    for (cname, controls), (sname, restrict), (iname, icols) in product(
        iv_control_menus, SAMPLE_MENUS, INSTRUMENT_MENUS
    ):
        try:
            sub = restrict(df)
            y, X, Z, sub = _iv_design(sub, controls, icols)
            if len(y) < 200:
                continue
            iv_fit = IV2SLS(endog=y, exog=X, instrument=Z).fit()
            exog_no_educ_cols = ["exper_c", "expersq_c"] + [c for c in controls if c not in {"exper", "expersq"}]
            fs = first_stage_f(
                sub["educ"].astype(float).values,
                sub[icols].astype(float).values,
                sm.add_constant(sub[exog_no_educ_cols].astype(float).values),
            )
            rows.append({
                "estimator": "IV2SLS",
                "controls": cname,
                "sample": sname,
                "cov": "classical",
                "instrument": iname,
                "n": int(len(y)),
                "educ_coef": float(iv_fit.params[1]),
                "educ_se": float(iv_fit.bse[1]),
                "educ_p": float(iv_fit.pvalues[1]),
                "first_stage_F": float(fs),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


def summarise(specs: pd.DataFrame) -> dict:
    out: dict = {"n_specs": int(len(specs))}
    for est in specs["estimator"].unique():
        sub = specs[specs["estimator"] == est]
        coefs = sub["educ_coef"].dropna().values
        out[est] = {
            "n": int(len(coefs)),
            "median": float(np.median(coefs)) if len(coefs) else float("nan"),
            "mean": float(np.mean(coefs)) if len(coefs) else float("nan"),
            "iqr_25": float(np.quantile(coefs, 0.25)) if len(coefs) else float("nan"),
            "iqr_75": float(np.quantile(coefs, 0.75)) if len(coefs) else float("nan"),
            "ci_5": float(np.quantile(coefs, 0.05)) if len(coefs) else float("nan"),
            "ci_95": float(np.quantile(coefs, 0.95)) if len(coefs) else float("nan"),
            "share_significant": float((sub["educ_p"] < 0.05).mean()) if len(coefs) else float("nan"),
        }
        if est == "IV2SLS":
            out[est]["share_strong_F"] = float((sub["first_stage_F"] > 10).mean())
    return out


def make_figure(specs: pd.DataFrame, summary: dict, anchors: dict, png_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ols = specs[specs["estimator"] == "OLS"].sort_values("educ_coef").reset_index(drop=True)
    iv = specs[specs["estimator"] == "IV2SLS"].sort_values("educ_coef").reset_index(drop=True)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=False,
                             gridspec_kw={"height_ratios": [3, 2]})

    # --- top: OLS spec curve with anchors -----------------------------------
    ax = axes[0]
    ax.errorbar(np.arange(len(ols)), ols["educ_coef"],
                yerr=1.96 * ols["educ_se"], fmt="o", ms=3, color="#1f77b4",
                ecolor="#aec7e8", alpha=0.85, label=f"OLS specs (n={len(ols)})")
    o = summary.get("OLS", {})
    if np.isfinite(o.get("median", float("nan"))):
        ax.axhline(o["median"], color="#1f77b4", lw=1, ls="--",
                   label=f"OLS median = {o['median']:.4f}")
        ax.axhspan(o["ci_5"], o["ci_95"], color="#1f77b4", alpha=0.08,
                   label=f"OLS 5/95 band = [{o['ci_5']:.3f}, {o['ci_95']:.3f}]")

    # Anchors: iter06, iter09, iter10 from the documented run
    colours = {"iter06": "#2ca02c", "iter09": "#d62728", "iter10": "#9467bd"}
    for label, val in anchors.items():
        if val is None:
            continue
        ax.axhline(val, color=colours.get(label, "k"), lw=1.5, ls=":",
                   label=f"{label}: educ={val:.4f}")

    ax.set_ylabel("educ coefficient")
    ax.set_xlabel("OLS specifications, sorted by educ coefficient")
    ax.legend(loc="upper left", fontsize=8, ncols=2)
    ax.set_title("Specification curve — OLS multiverse with documented-run anchors")

    # --- bottom: IV spec curve ----------------------------------------------
    ax = axes[1]
    valid_iv = iv[np.isfinite(iv["educ_coef"]) & (np.abs(iv["educ_coef"]) < 1.0)].reset_index(drop=True)
    ax.errorbar(np.arange(len(valid_iv)), valid_iv["educ_coef"],
                yerr=1.96 * valid_iv["educ_se"], fmt="s", ms=3, color="#ff7f0e",
                ecolor="#ffbb78", alpha=0.85, label=f"IV2SLS specs (n={len(valid_iv)})")
    iv_summary = summary.get("IV2SLS", {})
    if np.isfinite(iv_summary.get("median", float("nan"))):
        ax.axhline(iv_summary["median"], color="#ff7f0e", lw=1, ls="--",
                   label=f"IV median = {iv_summary['median']:.4f}")
    # Iter01 anchor
    if anchors.get("iter01") is not None:
        ax.axhline(anchors["iter01"], color="#8c564b", lw=1.5, ls=":",
                   label=f"iter01 (Card 1995 IV): educ={anchors['iter01']:.4f}")
    ax.set_ylabel("educ coefficient")
    ax.set_xlabel("IV2SLS specifications, sorted by educ coefficient")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Specification curve — IV2SLS multiverse")

    plt.tight_layout()
    plt.savefig(png_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = load_card_data()
    print(f"Loaded {len(df)} rows.")

    print("Running OLS multiverse...")
    ols_specs = run_ols_multiverse(df)
    print(f"  OLS specs: {len(ols_specs)}")

    print("Running IV multiverse...")
    iv_specs = run_iv_multiverse(df)
    print(f"  IV specs:  {len(iv_specs)}")

    specs = pd.concat([ols_specs, iv_specs], ignore_index=True)
    specs.to_csv(OUT_DIR / "big_multiverse.csv", index=False)
    print(f"  Saved {OUT_DIR / 'big_multiverse.csv'} ({len(specs)} total rows)")

    summary = summarise(specs)
    with open(OUT_DIR / "big_multiverse_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved {OUT_DIR / 'big_multiverse_summary.json'}")
    print(json.dumps(summary, indent=2))

    # Anchors from results.tsv (iter01, iter06, iter09, iter10)
    anchors = {
        "iter01": 0.1249,   # IV2SLS-nearc4 full sample
        "iter06": 0.0647,   # OLS trim ±1%
        "iter09": 0.0569,   # OLS trim ±2.5%  (kept best)
        "iter10": 0.0510,   # OLS trim ±5%   (hard-rule discard)
    }
    make_figure(specs, summary, anchors, OUT_DIR / "big_multiverse_figure.png")
    print(f"  Saved {OUT_DIR / 'big_multiverse_figure.png'}")


if __name__ == "__main__":
    main()
