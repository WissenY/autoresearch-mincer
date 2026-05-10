"""
Fixed infrastructure for Mincer wage equation specification search.
DO NOT MODIFY THIS FILE. It is read-only.
Generates synthetic wage data from known DGP and provides evaluation.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan

# ---------------------------------------------------------------------------
# Configuration (fixed)
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
N_OBS = 500

# ---------------------------------------------------------------------------
# Data Generation from Known Mincer DGP
# ---------------------------------------------------------------------------

def generate_wage_data(seed=RANDOM_SEED, n=N_OBS):
    """
    Generate synthetic wage data from a known Mincer earnings function.
    Ground truth: log(wage) = 1.0 + 0.08*educ + 0.04*exper - 0.0006*exper²
                              + 0.02*tenure - 0.15*female + 0.10*married
                              + 0.08*union + ε,  ε ~ N(0, 0.25)

    Returns: pd.DataFrame with columns:
        wage, educ, exper, tenure, female, married, union
    """
    rng = np.random.default_rng(seed)
    educ = rng.integers(8, 21, n).astype(float)
    exper = rng.uniform(0, 45, n)
    tenure = rng.exponential(5, n)
    female = rng.binomial(1, 0.48, n).astype(float)
    married = rng.binomial(1, 0.55, n).astype(float)
    union = rng.binomial(1, 0.18, n).astype(float)

    log_wage = (1.0 + 0.08 * educ + 0.04 * exper - 0.0006 * exper**2
                + 0.02 * tenure - 0.15 * female + 0.10 * married
                + 0.08 * union + rng.normal(0, 0.25, n))
    wage = np.exp(log_wage)

    return pd.DataFrame({
        'wage': wage,
        'educ': educ,
        'exper': exper,
        'tenure': tenure,
        'female': female,
        'married': married,
        'union': union,
    })

# ---------------------------------------------------------------------------
# Diagnostic Test Functions
# ---------------------------------------------------------------------------

def _run_bp_test(model, exog):
    """Breusch-Pagan test for heteroskedasticity. Returns p-value."""
    try:
        _, pval, _, _ = het_breuschpagan(model.resid, exog)
        return pval
    except Exception:
        return 0.0

def _run_vif(exog):
    """Compute VIF for each variable (excluding constant). Returns max VIF.
    Note: polynomial/interaction terms naturally have high VIF with their
    base terms. We only flag if VIF > 15 (lenient threshold for this case)."""
    try:
        # exog from model may already include constant; strip it to avoid
        # double-constant collinearity
        arr = np.asarray(exog)
        if arr.shape[1] > 1 and np.all(np.abs(arr[:, 0] - 1.0) < 1e-10):
            arr = arr[:, 1:]  # remove constant column
        ncols = arr.shape[1]
        if ncols < 2:
            return 0.0
        vifs = []
        for i in range(ncols):
            try:
                v = variance_inflation_factor(arr, i)
                if np.isfinite(v):
                    vifs.append(v)
            except Exception:
                pass
        return max(vifs) if vifs else 0.0
    except Exception:
        return 0.0

def _run_reset(model):
    """Ramsey RESET test for specification error. Returns p-value."""
    try:
        reset_result = model.resid  # simplified placeholder
        # Actual RESET implementation would add fitted² as regressor
        y_fitted = model.fittedvalues
        y = model.model.endog
        exog_reset = sm.add_constant(np.column_stack([model.model.exog, y_fitted**2]))
        reset_model = sm.OLS(y, exog_reset).fit()
        # F-test for added squared term
        from statsmodels.stats.anova import anova_lm
        # Simpler: check if squared fitted term is significant
        pval = reset_model.pvalues[-1]
        return pval
    except Exception:
        return 0.0

# ---------------------------------------------------------------------------
# Evaluation Function (GROUND TRUTH — DO NOT MODIFY)
# ---------------------------------------------------------------------------

def evaluate_specification(model, previous_best_aic=None, previous_best_score=0,
                           prev_sign_stable=True):
    """
    Evaluate a fitted OLS model on a 0-5 multi-dimensional score.

    Dimensions:
      1. Core hypothesis: educ coefficient positive AND significant (p < 0.05)
      2. Model fit: AIC improved vs. previous best (or baseline)
      3. Diagnostics: BP test passes (p >= 0.05), VIF < 10, RESET passes (p >= 0.05)
      4. Robustness: educ sign is stable across specifications
      5. Simplicity: model achieves results without gratuitous complexity

    Returns dict with scores and diagnostic details.
    """
    results = model
    exog = model.model.exog
    endog = model.model.endog
    n_obs = len(endog)
    n_params = len(model.params)
    adj_r2 = model.rsquared_adj
    aic = model.aic

    # --- Dimension 1: Core hypothesis ---
    educ_pos = -1
    educ_pval = 1.0
    core_sign = "none"
    core_score = 0
    param_names = list(model.params.index)
    if 'educ' in param_names:
        idx = param_names.index('educ')
        coef = model.params.iloc[idx]
        pval = model.pvalues.iloc[idx]
        educ_pos = coef
        educ_pval = pval
        if coef > 0 and pval < 0.05:
            core_sign = "positive"
            core_score = 1
        elif coef < 0 and pval < 0.05:
            core_sign = "negative"
    else:
        core_sign = "educ not in model"

    # --- Dimension 2: Model fit ---
    fit_score = 0
    if previous_best_aic is None:
        fit_score = 1  # baseline always scores 1
    elif aic < previous_best_aic:
        fit_score = 1

    # --- Dimension 3: Diagnostics ---
    bp_pval = _run_bp_test(model, exog)
    max_vif = _run_vif(exog)
    reset_pval = _run_reset(model)
    diag_fails = []
    if bp_pval < 0.05:
        diag_fails.append("BP")
    if max_vif >= 15:
        diag_fails.append(f"VIF={max_vif:.1f}")
    if reset_pval < 0.05:
        diag_fails.append("RESET")
    diag_score = 1 if len(diag_fails) == 0 else 0

    # --- Dimension 4: Robustness ---
    robust_score = 1 if prev_sign_stable else 0

    # --- Dimension 5: Simplicity ---
    # Penalize if n_params > n_obs / 20 (overfitting risk)
    # and if adj_r2 improvement vs baseline is negligible
    if n_params > n_obs / 20:
        simplicity_score = 0
    elif n_params > 10:
        simplicity_score = 1 if adj_r2 > 0.25 else 0
    else:
        simplicity_score = 1

    total_score = core_score + fit_score + diag_score + robust_score + simplicity_score

    print("---")
    print(f"spec_score:        {total_score}")
    print(f"core_hypothesis:   {core_score}")
    print(f"  core_sign:       {core_sign}")
    print(f"  core_sig:        {educ_pval:.4f}")
    print(f"model_fit:         {fit_score}")
    print(f"  adj_r2:          {adj_r2:.4f}")
    print(f"  aic:             {aic:.1f}")
    print(f"diagnostics:       {diag_score}")
    print(f"  bp_test_p:       {bp_pval:.4f}")
    print(f"  max_vif:         {max_vif:.1f}")
    print(f"  reset_p:         {reset_pval:.4f}")
    print(f"robustness:        {robust_score}")
    print(f"simplicity:        {simplicity_score}")
    print(f"  n_params:        {n_params}")

    return {
        'spec_score': total_score,
        'core_sign': core_sign,
        'core_sig': educ_pval,
        'adj_r2': adj_r2,
        'aic': aic,
        'diagnostic_fails': ','.join(diag_fails) if diag_fails else 'none',
        'n_params': n_params,
    }
