# Autonomous Research Workflow: Mincer Wage Equation Specification Search

## Research Problem

**Question**: What specification of the Mincer earnings function best explains log-wage variation across workers, balancing explanatory power against model parsimony and methodological rigor?

**Single metric**: A multi-dimensional **specification score** (0–5 scale) evaluating each model across 5 equally-weighted dimensions.

**Fixed resource budget**: Each experiment has **no explicit wall-clock limit** because regressions run in under 5 seconds. Instead, the budget is **one specification change per iteration** — one hypothesis, one change, one evaluation.

**Why suitable for autonomous experimentation**: Mincer equations are the most replicated empirical model in labor economics. The specification space is well-understood but combinatorially vast (squared terms, interactions, fixed effects, transformations). An agent can systematically navigate this space guided by econometric diagnostics.

---

## File Structure and Boundaries

### READ-ONLY files (DO NOT MODIFY)

| File | Role |
|------|------|
| `prepare.py` | Data loading from public source; variable definitions; the `evaluate_specification()` function that computes the specification score; all diagnostic test functions. |

### EDITABLE file (the agent modifies this)

| File | Role |
|------|------|
| `analysis.py` | Contains the regression specification(s) and the model-fitting logic. The agent modifies: (1) which variables enter the model, (2) functional form (logs, quadratics, interactions), (3) estimator choice (OLS, WLS, robust SE), (4) sample restrictions. |

### Constraints

- No new packages. Use only `numpy`, `pandas`, `statsmodels`.
- Never modify `evaluate_specification()` in `prepare.py`. It is the ground truth.
- Never install new packages or add dependencies.
- Respect the simplicity criterion (see below).

### Design rationale

This separation follows autoresearch: `prepare.py` is the fixed infrastructure (data + evaluation metric), `analysis.py` is the search space. Unlike autoresearch's single val_bpb metric, our evaluation is multi-dimensional — but the agent only modifies one file and receives a scalar score back, preserving the simplicity of the interface.

---

## The Experiment Loop

### Initial Setup (run once)

1. Verify the Python environment has `numpy`, `pandas`, `statsmodels`.
2. Run baseline: `python analysis.py`
3. Read the output printed by `evaluate_specification()`.
4. Create `results.tsv` with header row:
   ```
   commit	spec_score	core_sign	core_sig	adj_r2	aic	diagnostic_fails	status	description
   ```
5. Record the baseline run as the first row, status = `keep`.

### Per-Iteration Loop

LOOP FOREVER (start from step 1):

**Step 1 — Look at state**
Read `results.tsv`. Identify which specifications have been tried, what the best score is, and what diagnostic failures appeared in the last kept model.

**Step 2 — Formulate a hypothesis-driven change**
Modify `analysis.py` with ONE change grounded in econometric reasoning. Valid change categories:

| Category | Examples |
|----------|----------|
| Variable addition | Add `married`, `union`, `industry` dummies, `age²` |
| Functional form | Try `log(hours)` instead of `hours`; add interaction `educ × female` |
| Estimator / SE | Switch to `HC3` robust SE; try Weighted Least Squares |
| Sample restriction | Restrict to full-time workers; exclude outliers by Cook's D |
| Model reduction | Remove insignificant controls (simplicity win) |

**NOT allowed**: random variable fishing. Every change must be accompanied by a 1-line justification in the git commit message.

**Step 3 — Commit the change**
```
git add analysis.py
git commit -m "<short justification for this change>"
```

**Step 4 — Run the experiment**
```
python analysis.py > run.log 2>&1
```

**Step 5 — Parse results**
```
grep "^spec_score:" run.log
grep "^core_sign:" run.log
grep "^core_sig:" run.log
grep "^adj_r2:" run.log
grep "^aic:" run.log
grep "^diagnostic:" run.log
```

If grep returns empty → crash. Run `tail -n 40 run.log` for stack trace. Fix trivial bugs (typos, missing imports) and retry once. If fundamentally broken, log as `crash` and revert.

**Step 6 — Evaluate with multi-dimensional scorecard**

The `evaluate_specification()` function computes a score from 0 to 5:

| Dimension | Weight | Scoring rule |
|-----------|--------|-------------|
| Core hypothesis | 1 | 1 if `educ` coefficient is positive AND statistically significant at 5% level; 0 otherwise |
| Model fit | 1 | 1 if AIC is lower than the previous kept model; 0 otherwise |
| Diagnostics | 1 | 1 if all diagnostic tests pass (BP heteroskedasticity, VIF < 15, RESET test); 0 if any fails |
| Robustness | 1 | 1 if the sign of `educ` remains stable across at least 2 nested specifications; 0 otherwise |
| Simplicity | 1 | 1 if the model achieves its score without gratuitous complexity; 0 if it adds variables that don't improve fit |

**Scoring ranges guide**:
- 5/5: Exceptional — all criteria met, well-specified
- 4/5: Very good — one minor weakness
- 3/5: Acceptable — meaningful but flawed
- 1-2/5: Poor — fundamental problems

**Step 7 — Keep or Discard decision**

```
IF score >= 3 AND (score > previous_best OR 
   (score == previous_best AND model is simpler)):
    → KEEP (git stays on this commit)
ELIF score < 3 OR score < previous_best:
    → DISCARD (git reset --hard HEAD~1)
```

**Crash rule**: If the run crashes and cannot be fixed in one attempt, log status as `crash`, score as `0`, and git reset.

**Simplicity tiebreaker**: Between two models with equal score, prefer the one with fewer independent variables. A simplification that preserves score is ALWAYS a keep.

**Stagnation rule**: If no improvement for 5 consecutive iterations, broaden the search: try a different category of change (e.g., if you've been adding variables, try functional form changes; if you've been tweaking OLS, try WLS).

**Step 8 — Log to results.tsv**

Append one row (TAB-separated, never commas):
```
<7-char commit>	<score>	<core_sign>	<core_sig>	<adj_r2>	<aic>	<diagnostic_fails>	<keep|discard|crash>	<one-line description>
```

Example:
```
a1b2c3d	4	positive	0.001	0.321	1234.5	none	keep	add experience squared + HC3 robust SE
```

**Step 9 — Loop**
Go to Step 1. **NEVER STOP.** The human may be asleep. Continue until manually interrupted.

---

## Output Format

After each run, `analysis.py` calls `evaluate_specification()` which prints:

```
---
spec_score:        4
core_hypothesis:   1
  core_sign:       positive
  core_sig:        0.001
model_fit:         1
  adj_r2:          0.321
  aic:             1234.5
diagnostics:       1
  bp_test_p:       0.234
  max_vif:         3.2
  reset_p:         0.567
robustness:        1
  sign_stable:     True
simplicity:        1
  n_vars:          5
```

---

## Crash and Error Handling

| Failure type | Handling |
|-------------|----------|
| Python syntax error | Fix trivial typos once. If the idea itself causes the error, discard. |
| Missing import | Add the import (allowed: numpy, pandas, statsmodels only) |
| Singular matrix / perfect collinearity | The model is ill-specified. Discard. |
| All diagnostic tests fail | Discard. The specification is fundamentally flawed. |
| NaN in results | Discard. Check for division by zero or degenerate input. |
| Run exceeds 60 seconds | Kill it. Treat as crash. Regressions should be near-instant. |

---

## Simplicity Criterion (extended)

In empirical research, simpler is better (Occam's razor). The scoring system rewards parsimony:

1. **A simplification that preserves score = automatic keep.** Removing a variable and staying at the same score is an unambiguously good outcome.
2. **Adding a variable must earn its place.** If adj-R² doesn't improve by at least 0.005 and AIC doesn't decrease, the complexity cost outweighs the gain.
3. **Degrees of freedom matter.** A model with n=500 obs and k=25 vars is likely overfit, even if AIC is marginally better. Warn if k > n/20.
4. **Interaction terms must be justified.** Don't add `educ × female` just to inflate R² — there should be a theoretical reason.

---

## Human Stop-and-Check Points

While the loop is designed to run autonomously, three critical points require human review:

### Checkpoint 1: After Baseline Run

- **What to review**: The baseline model specification and its diagnostic profile.
- **Success criterion**: Baseline runs without error; diagnostic output is interpretable.
- **If fails**: The data or environment is broken. Fix before proceeding.

### Checkpoint 2: When Score Reaches 4/5

- **What to review**: The best model so far. Does the specification make theoretical sense? Is there a plausible economic story behind the variables?
- **Success criterion**: The model is both statistically sound AND economically interpretable.
- **If fails**: The agent may have found a spurious specification. Redirect by adding theoretical constraints to the change categories.

### Checkpoint 3: After 5 Iterations Without Improvement

- **What to review**: The full log of attempts. Is the agent stuck in a local optimum? Are all attempts in the same change category?
- **Success criterion**: The agent's next attempt should explore a qualitatively different direction.
- **If fails**: Manually suggest a new change category to the agent via program.md update.

### When is full autonomy appropriate vs. human-in-the-loop?

- **Full autonomy** (like autoresearch): When the evaluation metric is objective, the search space is well-defined, and the cost of a wrong answer is low.
- **Human-in-the-loop**: When the domain requires theoretical interpretation (like economics), when priors matter, and when "best" involves judgment calls.

---

## Logging results

`results.tsv` format (TAB-separated):

```
commit	spec_score	core_sign	core_sig	adj_r2	aic	diagnostic_fails	status	description
```

Columns:
1. `commit`: 7-char git hash
2. `spec_score`: 0–5 overall specification score
3. `core_sign`: "positive" / "negative" / "none" (for education coefficient)
4. `core_sig`: p-value of education coefficient (use "crash" for crashes)
5. `adj_r2`: adjusted R-squared (use "crash" for crashes)
6. `aic`: AIC value (use "crash" for crashes)
7. `diagnostic_fails`: comma-separated list of failed tests, or "none"
8. `status`: keep / discard / crash
9. `description`: one-line description of what this experiment tried

**NOTE**: Do NOT commit `results.tsv` to git. Leave it untracked.

---

## Research Direction and Scope

**Core research question**: What combination of human capital variables (education, experience, tenure), demographic controls (gender, marital status), and job characteristics (union, industry) best explains wage variation, as measured by a balanced score of statistical fit, diagnostic soundness, and specification parsimony?

**Acceptable scope of investigation**:
- Always include `educ` as the core variable of interest
- Always include `exper` (labor market experience)
- Optional: `tenure`, `female`, `married`, `union`, industry dummies
- Allowed transformations: quadratic terms (`exper²`), log transformations where theoretically justified
- Allowed interactions: `educ × female`, `educ × married` (returns to education by group)
- Allowed sample restrictions: full-time workers only, age 25-65

**Out of scope**: 
- Causal identification strategies (IV, DID) — this is a descriptive specification search
- Non-linear models (probit, logit) — the outcome is continuous
- Time-series or panel methods — the data is cross-sectional
