"""
Fixed infrastructure for the Mincer / Card-style returns-to-schooling
specification search.

DO NOT MODIFY THIS FILE. It is read-only and defines the ground truth
for evaluation. The agent edits analysis.py only.

Data: Card (1995, "Using Geographic Variation in College Proximity to
      Estimate the Return to Schooling") NLSYM extract, distributed by
      Wooldridge and mirrored on Rdatasets. Saved to data/card.csv.
      n = 3010 prime-age men, 1976 wage observations.

Key columns used:
  lwage       log hourly wage (1976)
  educ        years of completed schooling
  exper       years of labor market experience (potential)
  expersq     experience squared
  nearc4      lived near a 4-year college at age 14 (Card's instrument)
  nearc2      lived near a 2-year college at age 14 (alt instrument)
  fatheduc    father's education (alt instrument; missing for ~30%)
  motheduc    mother's education (alt instrument; missing for ~13%)
  black, south, smsa, married  controls
  IQ, KWW                       ability proxies (for ability-bias robustness)
  reg661-reg669                 region of residence dummies

Five evaluation dimensions (each 0/1):
  1. Identification        — IV first-stage F > 10 OR estimator stability
  2. Out-of-sample fit     — 5-fold CV MSE improves vs running best
  3. Specification stability — educ coefficient within ±25% of multiverse median
  4. Diagnostic soundness  — heteroskedasticity / specification handled correctly
  5. Parsimony             — BIC penalises gratuitous complexity

The agent receives a scalar 0–5 score plus the full diagnostic block.
References:
  Card (1995); Mincer (1974); Heckman, Lochner & Todd (2006);
  Simonsohn, Simmons & Nelson (2020); Romano & Wolf (2005).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

# ---------------------------------------------------------------------------
# Configuration (fixed)
# ---------------------------------------------------------------------------
RANDOM_SEED = 20260511
DATA_PATH = Path(__file__).parent / "data" / "card.csv"
CV_FOLDS = 5
SPEC_CURVE_REPS = 32       # number of alternative specs in the multiverse
RW_BOOT_REPS = 499         # Romano-Wolf step-down bootstrap reps (study-mode)


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------
def load_card_data() -> pd.DataFrame:
    """Load Card (1995) NLSYM extract.

    Returns the full sample of 3010 observations with experience squared
    pre-computed. Missing values are NOT imputed; the agent is responsible
    for sample restrictions.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"data/card.csv not found at {DATA_PATH}. "
            "Run scripts/fetch_data.sh or download from "
            "https://vincentarelbundock.github.io/Rdatasets/csv/wooldridge/card.csv"
        )
    df = pd.read_csv(DATA_PATH)
    # Recompute expersq for safety (the file has it but values can drift in
    # downstream sample restrictions).
    df["expersq"] = df["exper"] ** 2
    return df


# ---------------------------------------------------------------------------
# Diagnostic test functions (corrected)
# ---------------------------------------------------------------------------
def bp_test(model) -> float:
    """Breusch-Pagan test for heteroskedasticity. Returns p-value (NaN on err)."""
    try:
        _, pval, _, _ = het_breuschpagan(model.resid, model.model.exog)
        return float(pval)
    except Exception:
        return float("nan")


def max_vif(exog: np.ndarray) -> float:
    """Max VIF among non-constant regressors. Returns 0.0 on failure."""
    try:
        arr = np.asarray(exog, dtype=float)
        if arr.shape[1] > 1 and np.allclose(arr[:, 0], 1.0):
            arr = arr[:, 1:]
        if arr.shape[1] < 2:
            return 0.0
        vifs = []
        for i in range(arr.shape[1]):
            try:
                v = variance_inflation_factor(arr, i)
                if np.isfinite(v):
                    vifs.append(v)
            except Exception:
                continue
        return max(vifs) if vifs else 0.0
    except Exception:
        return 0.0


def reset_test(model) -> float:
    """Ramsey RESET test (joint F-test of fitted^2 and fitted^3).

    Fixed implementation:
      * Does NOT add a second constant (the original exog already has one).
      * Tests fitted^2 AND fitted^3 jointly via an F-test.
      * Returns the joint F-test p-value.
    """
    try:
        y = np.asarray(model.model.endog)
        exog = np.asarray(model.model.exog)
        yhat = np.asarray(model.fittedvalues)
        # Augmented design: original exog + fitted^2 + fitted^3
        aug = np.column_stack([exog, yhat ** 2, yhat ** 3])
        aug_model = sm.OLS(y, aug).fit()
        # Joint F-test on the last two columns (fitted^2, fitted^3).
        k_aug = aug.shape[1]
        R = np.zeros((2, k_aug))
        R[0, k_aug - 2] = 1.0
        R[1, k_aug - 1] = 1.0
        f_test = aug_model.f_test(R)
        return float(np.asarray(f_test.pvalue).item())
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Cross-validated MSE
# ---------------------------------------------------------------------------
def _kfold_indices(n: int, k: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    return [fold for fold in np.array_split(idx, k)]


def cv_mse_5fold(y: np.ndarray, X: np.ndarray, *, seed: int = RANDOM_SEED) -> float:
    """5-fold CV MSE for a (y, X) OLS spec. X must already include a constant."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n = len(y)
    if n < CV_FOLDS * 5:
        return float("nan")
    folds = _kfold_indices(n, CV_FOLDS, seed)
    sse = 0.0
    n_used = 0
    for held in folds:
        mask = np.ones(n, dtype=bool)
        mask[held] = False
        try:
            beta, *_ = np.linalg.lstsq(X[mask], y[mask], rcond=None)
            yhat = X[held] @ beta
            sse += float(np.sum((y[held] - yhat) ** 2))
            n_used += len(held)
        except Exception:
            return float("nan")
    return sse / n_used if n_used else float("nan")


# ---------------------------------------------------------------------------
# Specification curve (Simonsohn, Simmons & Nelson 2020)
# ---------------------------------------------------------------------------
def _build_design(df: pd.DataFrame, controls: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Build (y, X) for log-wage regression with given controls. educ first
    among regressors so its index is always 1 (after the constant)."""
    sub = df.dropna(subset=["lwage", "educ", "exper"] + controls).copy()
    sub["expersq"] = sub["exper"] ** 2
    cols = ["educ", "exper", "expersq"] + [c for c in controls if c not in {"exper", "expersq"}]
    X = sm.add_constant(sub[cols].astype(float).values)
    y = sub["lwage"].astype(float).values
    return y, X


def specification_curve(df: pd.DataFrame) -> dict:
    """Run a small multiverse of plausible specifications and return the
    distribution of educ coefficients. Used both for scoring and reporting.

    The multiverse is defined HERE (read-only) so the agent cannot game it.
    Each spec varies one or more of:
      - control set (none / demographics / +region / +ability)
      - sample restriction (full / non-missing-IQ / dropped top-1% wage)
      - estimator (OLS-classical / OLS-HC3)

    Returns dict with:
      'coefs'       np.ndarray of educ coefficients across specs
      'median'      median educ coefficient
      'iqr'         (25th, 75th) quantile pair
      'ci_5_95'     (5th, 95th) quantile pair
      'n_specs'     total number of specs (== SPEC_CURVE_REPS)
    """
    rows = []
    base_controls = []
    demo = ["black", "south", "smsa"]
    region_dummies = [f"reg66{i}" for i in range(2, 10)]   # reg662..reg669 (reg661 omitted)
    ability_proxies = ["IQ", "KWW"]

    control_menus = [
        base_controls,
        demo,
        demo + region_dummies,
        demo + ability_proxies,
        demo + region_dummies + ability_proxies,
        demo + ["married", "fatheduc", "motheduc"],
        demo + region_dummies + ["married"],
        demo + region_dummies + ability_proxies + ["married"],
    ]

    sample_restrictions = [
        ("full", lambda d: d),
        ("trim_top1_wage", lambda d: d[d["lwage"] <= d["lwage"].quantile(0.99)]),
        ("trim_top_bot_1", lambda d: d[(d["lwage"] >= d["lwage"].quantile(0.01))
                                     & (d["lwage"] <= d["lwage"].quantile(0.99))]),
        ("non_missing_iq", lambda d: d.dropna(subset=["IQ"])),
    ]

    cov_types = ["nonrobust", "HC3"]

    n_specs = 0
    for controls in control_menus:
        for sample_name, restrict in sample_restrictions:
            for cov in cov_types:
                if n_specs >= SPEC_CURVE_REPS:
                    break
                try:
                    sub = restrict(df)
                    y, X = _build_design(sub, controls)
                    if len(y) < 100:
                        continue
                    fit = sm.OLS(y, X).fit(cov_type=cov)
                    rows.append(
                        {
                            "controls": ",".join(controls) if controls else "none",
                            "sample": sample_name,
                            "cov": cov,
                            "n": len(y),
                            "educ_coef": float(fit.params[1]),
                            "educ_se": float(fit.bse[1]),
                            "educ_p": float(fit.pvalues[1]),
                        }
                    )
                    n_specs += 1
                except Exception:
                    continue
            if n_specs >= SPEC_CURVE_REPS:
                break
        if n_specs >= SPEC_CURVE_REPS:
            break

    coefs = np.array([r["educ_coef"] for r in rows])
    out_dir = Path(__file__).parent / "logs"
    out_dir.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "spec_curve.csv", index=False)
    return {
        "coefs": coefs,
        "median": float(np.median(coefs)),
        "iqr": (float(np.quantile(coefs, 0.25)), float(np.quantile(coefs, 0.75))),
        "ci_5_95": (float(np.quantile(coefs, 0.05)), float(np.quantile(coefs, 0.95))),
        "n_specs": int(len(coefs)),
        "share_significant": float(np.mean(np.array([r["educ_p"] for r in rows]) < 0.05)),
    }


# ---------------------------------------------------------------------------
# Romano-Wolf step-down family-wise p-values
# ---------------------------------------------------------------------------
def romano_wolf_pvalues(
    y: np.ndarray,
    X_full: np.ndarray,
    test_idx: list[int],
    *,
    n_boot: int = RW_BOOT_REPS,
    seed: int = RANDOM_SEED,
) -> list[float]:
    """Family-wise p-values (Romano & Wolf 2005) via residual bootstrap.

    Tests H_j: beta_j = 0 for j in test_idx (multiple regressors of interest).
    Returns FWE-controlled p-values aligned with test_idx.

    Implementation: residual resampling under the null (subtract test betas
    from y), recompute t-statistics, take the step-down maxT distribution.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X_full, dtype=float)
    n, k = X.shape
    rng = np.random.default_rng(seed)
    fit = sm.OLS(y, X).fit()
    t_obs = np.abs(np.asarray(fit.tvalues)[test_idx])
    # Null: zero out tested coefficients, residuals from constrained fit.
    keep = [j for j in range(k) if j not in test_idx]
    X_null = X[:, keep]
    null_fit = sm.OLS(y, X_null).fit()
    resid = np.asarray(null_fit.resid)
    yhat_null = np.asarray(null_fit.fittedvalues)

    boot_t = np.zeros((n_boot, len(test_idx)))
    for b in range(n_boot):
        eb = resid[rng.integers(0, n, size=n)]
        yb = yhat_null + eb
        try:
            fb = sm.OLS(yb, X).fit()
            boot_t[b] = np.abs(np.asarray(fb.tvalues)[test_idx])
        except Exception:
            boot_t[b] = np.nan

    # Step-down: order observed |t| descending; FWE adjusted p_j is the
    # probability that the maxT over the not-yet-rejected set exceeds t_obs_j.
    order = np.argsort(-t_obs)
    pvals = np.zeros(len(test_idx))
    remaining = list(order)
    while remaining:
        active = boot_t[:, remaining]
        max_b = np.nanmax(active, axis=1)
        head = remaining[0]
        pvals[head] = float(np.mean(max_b >= t_obs[head]))
        remaining.pop(0)
    # Enforce monotonicity (step-down).
    for i in range(1, len(order)):
        prev = order[i - 1]
        cur = order[i]
        pvals[cur] = max(pvals[cur], pvals[prev])
    return [float(pvals[j]) for j in range(len(test_idx))]


# ---------------------------------------------------------------------------
# IV first-stage diagnostic (Stock-Yogo style F-statistic)
# ---------------------------------------------------------------------------
def first_stage_f(y_endog: np.ndarray, instruments: np.ndarray, controls: np.ndarray) -> float:
    """Compute the F-statistic on the excluded instruments in the first stage.

    Returns the partial F. Stock-Yogo rule of thumb: F > 10 → not weak.
    """
    try:
        Z = np.column_stack([controls, instruments])
        full = sm.OLS(y_endog, Z).fit()
        small = sm.OLS(y_endog, controls).fit()
        n = len(y_endog)
        k_full = Z.shape[1]
        q = instruments.shape[1] if instruments.ndim == 2 else 1
        rss_r = float(np.sum(small.resid ** 2))
        rss_u = float(np.sum(full.resid ** 2))
        f = ((rss_r - rss_u) / q) / (rss_u / (n - k_full))
        return float(f)
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# Master evaluation function (GROUND TRUTH — DO NOT MODIFY)
# ---------------------------------------------------------------------------
def evaluate_specification(
    *,
    fit,
    df: pd.DataFrame,
    educ_index: int = 1,
    cov_type: str | None = None,
    iv_info: dict | None = None,
    previous_best_cv: float | None = None,
    spec_curve: dict | None = None,
    history_signs: list[str] | None = None,
) -> dict:
    """Compute the 5-dimension specification score for a fitted model.

    Required arguments are keyword-only to keep the call site explicit.

    Args:
      fit               Fitted statsmodels OLS / IV2SLS results object.
      df                The dataframe used (post any sample restrictions).
      educ_index        Column index of `educ` in fit.params (default 1
                        because column 0 is the constant).
      cov_type          The covariance type passed to .fit() ('nonrobust',
                        'HC3', 'cluster', None for IV which uses GMM).
      iv_info           Optional dict with keys:
                        endog (np.ndarray), instruments (np.ndarray),
                        controls (np.ndarray) — used for first-stage F.
      previous_best_cv  Best CV-MSE so far (None for baseline).
      spec_curve        Output of specification_curve(); if None, recomputed.
      history_signs     List of educ-coef signs in prior kept models.

    Dimensions:
      1. Identification        first-stage F > 10 (IV) OR cov_type matches
                              diagnostic verdict OR estimator-stable
      2. Out-of-sample fit     CV-MSE ≤ previous_best_cv * 1.005 (within 0.5%)
                              OR strictly improved
      3. Specification stability educ coef within ±25% of spec-curve median
      4. Diagnostic soundness  if BP rejects → robust SE used; if RESET
                              rejects → flagged as misspecification
      5. Parsimony             BIC penalty: rewards fewer params for given
                              CV-MSE (BIC ≤ baseline OR k ≤ n/30)
    """
    print("---")  # delimiter the agent grep'd for

    # ------ Pull standardised quantities ------------------------------------
    params = np.asarray(fit.params)
    bse = np.asarray(fit.bse)
    pvalues = np.asarray(fit.pvalues)
    educ_coef = float(params[educ_index])
    educ_se = float(bse[educ_index])
    educ_p = float(pvalues[educ_index])
    educ_sign = "positive" if educ_coef > 0 else ("negative" if educ_coef < 0 else "zero")

    # CV-MSE (only well-defined for OLS-style; for IV we report training MSE).
    # IV2SLS.fit() returns an IV2SLSResults wrapper — detect via the underlying
    # model rather than the results class.
    is_iv = isinstance(getattr(fit, "model", None), IV2SLS)
    y_arr = np.asarray(fit.model.endog)
    X_arr = np.asarray(fit.model.exog)
    if is_iv:
        cv_mse = float(np.mean(np.asarray(fit.resid) ** 2))
    else:
        cv_mse = cv_mse_5fold(y_arr, X_arr)

    n_obs = int(len(y_arr))
    n_params = int(X_arr.shape[1])

    def _safe(attr):
        try:
            return float(getattr(fit, attr))
        except Exception:
            return float("nan")

    aic = _safe("aic")
    bic = _safe("bic")
    adj_r2 = _safe("rsquared_adj")
    if not np.isfinite(bic):
        # IV2SLS: build a Schwarz-style penalty from the residual variance so
        # parsimony can still discriminate among IV specs.
        try:
            rss = float(np.sum(np.asarray(fit.resid) ** 2))
            if rss > 0 and n_obs > 0:
                bic = n_obs * np.log(rss / n_obs) + n_params * np.log(n_obs)
        except Exception:
            pass

    # ------ Diagnostics -----------------------------------------------------
    if is_iv:
        bp_p = float("nan")
        max_v = max_vif(X_arr)
        reset_p = float("nan")
    else:
        bp_p = bp_test(fit)
        max_v = max_vif(X_arr)
        reset_p = reset_test(fit)
    bp_reject = (bp_p == bp_p) and bp_p < 0.05      # NaN-safe
    reset_reject = (reset_p == reset_p) and reset_p < 0.05
    high_vif = max_v >= 15

    # ------ Spec-curve consistency -----------------------------------------
    if spec_curve is None:
        spec_curve = specification_curve(df)
    sc_median = spec_curve["median"]
    sc_lo, sc_hi = sc_median * 0.75, sc_median * 1.25
    sc_consistent = (sc_lo <= educ_coef <= sc_hi)

    # ------ Dimension 1: Identification ------------------------------------
    fs_f = float("nan")
    if iv_info is not None:
        fs_f = first_stage_f(
            np.asarray(iv_info["endog"], dtype=float),
            np.asarray(iv_info["instruments"], dtype=float),
            np.asarray(iv_info["controls"], dtype=float),
        )
        ident_score = 1 if (fs_f == fs_f and fs_f > 10) else 0
        ident_reason = f"IV first-stage F={fs_f:.1f}"
    else:
        # Non-IV models: identification is judged by stability across the
        # spec-curve PLUS appropriate response to diagnostics.
        appropriate_se = True
        if bp_reject and (cov_type is None or cov_type.lower() == "nonrobust"):
            appropriate_se = False
        ident_score = 1 if (sc_consistent and appropriate_se) else 0
        ident_reason = (
            f"stability={sc_consistent}, BP-aware-SE={appropriate_se}"
        )

    # ------ Dimension 2: Out-of-sample fit ---------------------------------
    if previous_best_cv is None:
        oos_score = 1
        oos_reason = "baseline"
    else:
        oos_score = 1 if cv_mse <= previous_best_cv * 1.005 else 0
        oos_reason = f"cv_mse={cv_mse:.5f} vs best={previous_best_cv:.5f}"

    # ------ Dimension 3: Specification stability ---------------------------
    stab_score = 1 if sc_consistent else 0
    stab_reason = (
        f"educ={educ_coef:.4f}, multiverse median={sc_median:.4f}, "
        f"5/95={spec_curve['ci_5_95'][0]:.4f}/{spec_curve['ci_5_95'][1]:.4f}"
    )

    # ------ Dimension 4: Diagnostic soundness ------------------------------
    diag_fails = []
    if bp_reject and (cov_type is None or cov_type.lower() == "nonrobust"):
        diag_fails.append("BP-not-handled")
    if reset_reject:
        diag_fails.append("RESET")
    if high_vif:
        diag_fails.append(f"VIF={max_v:.1f}")
    diag_score = 1 if not diag_fails else 0

    # ------ Dimension 5: Parsimony -----------------------------------------
    parsimony_score = 1 if (n_params <= max(6, n_obs // 30)) else 0

    total = ident_score + oos_score + stab_score + diag_score + parsimony_score

    # ------ Print structured output the agent will grep --------------------
    print(f"spec_score:        {total}")
    print(f"identification:    {ident_score}")
    print(f"  reason:          {ident_reason}")
    print(f"  first_stage_F:   {fs_f:.4f}" if fs_f == fs_f else f"  first_stage_F:   NA")
    print(f"oos_fit:           {oos_score}")
    print(f"  cv_mse:          {cv_mse:.6f}")
    print(f"  prev_best_cv:    {previous_best_cv if previous_best_cv is not None else 'NA'}")
    print(f"spec_stability:    {stab_score}")
    print(f"  educ_coef:       {educ_coef:.4f}")
    print(f"  multiverse_med:  {sc_median:.4f}")
    print(f"  multiverse_5_95: {spec_curve['ci_5_95'][0]:.4f}/{spec_curve['ci_5_95'][1]:.4f}")
    print(f"diagnostics:       {diag_score}")
    print(f"  bp_p:            {bp_p:.4f}" if bp_p == bp_p else f"  bp_p:            NA")
    print(f"  reset_p:         {reset_p:.4f}" if reset_p == reset_p else f"  reset_p:         NA")
    print(f"  max_vif:         {max_v:.2f}")
    print(f"  cov_type:        {cov_type}")
    print(f"  diag_fails:      {','.join(diag_fails) if diag_fails else 'none'}")
    print(f"parsimony:         {parsimony_score}")
    print(f"  n_params:        {n_params}")
    print(f"  n_obs:           {n_obs}")
    print(f"  aic:             {aic:.2f}" if aic == aic else "  aic:             NA")
    print(f"  bic:             {bic:.2f}" if bic == bic else "  bic:             NA")
    print(f"  adj_r2:          {adj_r2:.4f}" if adj_r2 == adj_r2 else "  adj_r2:          NA")
    print(f"core_sign:         {educ_sign}")
    print(f"core_p:            {educ_p:.4f}")

    return {
        "spec_score": int(total),
        "identification": int(ident_score),
        "oos_fit": int(oos_score),
        "spec_stability": int(stab_score),
        "diagnostics": int(diag_score),
        "parsimony": int(parsimony_score),
        "educ_coef": educ_coef,
        "educ_se": educ_se,
        "educ_p": educ_p,
        "core_sign": educ_sign,
        "cv_mse": cv_mse,
        "first_stage_F": fs_f,
        "bp_p": bp_p,
        "reset_p": reset_p,
        "max_vif": max_v,
        "diagnostic_fails": ",".join(diag_fails) if diag_fails else "none",
        "n_params": n_params,
        "n_obs": n_obs,
        "aic": aic,
        "bic": bic,
        "adj_r2": adj_r2,
        "multiverse_median": sc_median,
        "multiverse_5": spec_curve["ci_5_95"][0],
        "multiverse_95": spec_curve["ci_5_95"][1],
        "spec_curve_n": spec_curve["n_specs"],
    }
