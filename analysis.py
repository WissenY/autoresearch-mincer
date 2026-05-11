"""
Returns-to-schooling specification — Agent-editable file.

This is the ONLY file the agent modifies. Each iteration changes ONE thing:
the control set, the sample restriction, the estimator, the SE choice, or
swaps OLS for IV2SLS using Card's near-college instrument.

Data: Card (1995) NLSYM, log hourly wage, 3010 prime-age men.
Outcome: lwage. Endogenous regressor of interest: educ.

Run:  python analysis.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS

from prepare import (
    evaluate_specification,
    load_card_data,
    specification_curve,
)

# ---------------------------------------------------------------------------
# Bookkeeping: read previous-best CV-MSE from results.tsv (do not modify).
# ---------------------------------------------------------------------------
RESULTS_PATH = Path(__file__).parent / "results.tsv"


def _previous_best_cv_mse() -> float | None:
    if not RESULTS_PATH.exists():
        return None
    try:
        prior = pd.read_csv(RESULTS_PATH, sep="\t")
        kept = prior[prior["status"] == "keep"]
        if kept.empty:
            return None
        cv = pd.to_numeric(kept["cv_mse"], errors="coerce").dropna()
        return float(cv.min()) if not cv.empty else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Load data (do not modify this section)
# ---------------------------------------------------------------------------
df = load_card_data()

# ---------------------------------------------------------------------------
# MODEL SPECIFICATION — Edit BELOW THIS LINE
# ---------------------------------------------------------------------------
# BASELINE: classic Mincer log-wage equation, OLS with HC3 SE,
# demographic controls, on the full sample.

controls = ["black", "south", "smsa"]  # drop married — parsimony retry on trimmed sample
sample = df.dropna(subset=["lwage", "educ", "exper"] + controls).copy()
# Trim top and bottom 1% of lwage to limit influence of wage-outliers
lo, hi = sample["lwage"].quantile(0.01), sample["lwage"].quantile(0.99)
sample = sample[(sample["lwage"] >= lo) & (sample["lwage"] <= hi)].copy()
# Center experience before squaring — removes the mechanical near-collinearity
# between `exper` and `exper²` that otherwise inflates VIF without economic
# meaning (Wooldridge 2019, ch. 6.2).
exper_mean = sample["exper"].mean()
sample["exper_c"] = sample["exper"] - exper_mean
sample["expersq_c"] = sample["exper_c"] ** 2

# educ is placed FIRST after the constant so educ_index = 1 (the prepare.py
# evaluation function relies on this convention).
regressors = ["educ", "exper_c", "expersq_c"] + controls
X = sm.add_constant(sample[regressors].astype(float).values)
y = sample["lwage"].astype(float).values

cov_type = "HC3"           # diagnostic-aware: heteroskedasticity is expected
fit = sm.OLS(y, X).fit(cov_type=cov_type)

# ----- IV info: leave None for OLS, populate for IV2SLS specifications -----
iv_info: dict | None = None
# Example (uncomment to use Card's near-4-year-college as IV for educ):
# Z = sample[["nearc4"]].astype(float).values
# controls_for_first_stage = sm.add_constant(
#     sample[["exper", "expersq"] + controls].astype(float).values
# )
# iv_info = {
#     "endog": sample["educ"].astype(float).values,
#     "instruments": Z,
#     "controls": controls_for_first_stage,
# }
# fit = IV2SLS(
#     endog=y,
#     exog=X,
#     instrument=np.column_stack([controls_for_first_stage, Z]),
# ).fit()
# cov_type = "iv2sls-classical"

# ---------------------------------------------------------------------------
# MODEL SPECIFICATION — Edit ABOVE THIS LINE
# ---------------------------------------------------------------------------
# Evaluate (do not modify this section)
# ---------------------------------------------------------------------------
spec_curve = specification_curve(df)
result = evaluate_specification(
    fit=fit,
    df=sample,
    educ_index=1,
    cov_type=cov_type,
    iv_info=iv_info,
    previous_best_cv=_previous_best_cv_mse(),
    spec_curve=spec_curve,
)

# Emit a small JSON block at the end so the agent can parse without grep.
print("\n--- json ---")
print(json.dumps(result, default=float, indent=2))
