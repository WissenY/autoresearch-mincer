"""Smoke-test the dual-multiverse fix.

Re-runs the iter01 Card 1995 IV2SLS-nearc4 specification under the new
`evaluate_specification` which routes IV iterations to `iv_specification_curve`.
Expected outcome: the IV LATE of ~0.125, which scored 3/5 under v1 (penalised
against the OLS multiverse), now scores higher because it is judged against
the IV multiverse where IV LATEs cluster.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from prepare import (
    evaluate_specification,
    iv_specification_curve,
    load_card_data,
    specification_curve,
)


def main() -> None:
    df = load_card_data()
    controls = ["black", "south", "smsa", "married"]
    sample = df.dropna(subset=["lwage", "educ", "exper"] + controls + ["nearc4"]).copy()
    # Center experience before squaring — matches the baseline convention
    # (Wooldridge 2019, ch. 6.2) so VIF is not inflated by trivial collinearity.
    exper_mean = sample["exper"].mean()
    sample["exper_c"] = sample["exper"] - exper_mean
    sample["expersq_c"] = sample["exper_c"] ** 2

    exog_cols = ["educ", "exper_c", "expersq_c"] + controls
    y = sample["lwage"].astype(float).values
    X = sm.add_constant(sample[exog_cols].astype(float).values)

    # IV: replace educ (the endogenous column) with nearc4 in the instrument matrix.
    exog_no_educ = ["exper_c", "expersq_c"] + controls
    Z_inner = sample[exog_no_educ + ["nearc4"]].astype(float).values
    Z = sm.add_constant(Z_inner)

    iv_fit = IV2SLS(endog=y, exog=X, instrument=Z).fit()

    iv_info = {
        "endog": sample["educ"].astype(float).values,
        "instruments": sample[["nearc4"]].astype(float).values,
        "controls": sm.add_constant(sample[exog_no_educ].astype(float).values),
    }

    print("=== v2 IV path: iter01 Card 1995 IV2SLS-nearc4 ===\n")
    print("Computing OLS multiverse...")
    ols_curve = specification_curve(df)
    print(f"  OLS median = {ols_curve['median']:.4f}, 5/95 = {ols_curve['ci_5_95']}")
    print("Computing IV multiverse...")
    iv_curve = iv_specification_curve(df)
    print(f"  IV median  = {iv_curve['median']:.4f}, 5/95 = {iv_curve['ci_5_95']}, n_specs = {iv_curve['n_specs']}\n")

    result = evaluate_specification(
        fit=iv_fit,
        df=sample,
        educ_index=1,
        cov_type="iv2sls-classical",
        iv_info=iv_info,
        previous_best_cv=0.107336,
        spec_curve=ols_curve,
        iv_spec_curve=iv_curve,
    )
    print()
    print(f">>> v2 spec_score = {result['spec_score']} / 5")
    print(f">>> multiverse_used = {result['multiverse_used']}")
    print(f">>> v1 would have scored 3/5 (educ=0.125 outside OLS multiverse 0.0508-0.0903).")


if __name__ == "__main__":
    main()
