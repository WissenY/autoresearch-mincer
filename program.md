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

### Initial Setup (run once — ends at Checkpoint 1)

1. Verify the Python environment has `numpy`, `pandas`, `statsmodels`.
2. Run baseline: `python analysis.py`
3. Read the output printed by `evaluate_specification()`.
4. Create `results.tsv` with header row (see Logging Results section below).
5. Record the baseline run as the first row, status = `keep`.
6. **IMMEDIATELY trigger Checkpoint 1** — do NOT proceed to the experiment loop until the human confirms.

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
**Step 9 — Checkpoint gate**

Before looping back to Step 1, check if any checkpoint condition has been triggered (see Human Stop-and-Check Points below). If YES → **PAUSE immediately** and output the checkpoint header. Do NOT start a new iteration until the human confirms "proceed" or gives new instructions.

If no checkpoint is triggered → go to Step 1 and continue.

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

The agent does NOT run fully unattended. At three critical checkpoints, the agent MUST pause and present a structured status report to the human. The agent must NOT resume until the human explicitly responds "proceed" or provides new direction.

**Protocol for ALL checkpoints**: When a checkpoint is triggered, the agent MUST:
1. Print `=== CHECKPOINT N TRIGGERED ===` (where N = 1, 2, or 3)
2. Present the review items listed below in a structured format
3. Explicitly ask: `Proceed? Or redirect?`
4. Wait for human response before any further action

---

### Checkpoint 1: After Baseline Run (Trigger: iteration count == 1)

**When**: Immediately after the first experiment (baseline) completes.

**What to review**:
1. The baseline model's `spec_score` and full diagnostic breakdown (from `run.log`).
2. Verify that `core_sign = positive` AND `core_sig < 0.05` — the baseline Mincer equation must confirm returns to education.
3. Verify all diagnostic tests ran without errors (BP test, VIF, RESET all produced numeric output).
4. Confirm `n_params` is between 3 and 10 (baseline should be reasonably parsimonious).

**Success criterion**: ALL of the above pass.

**Agent action on success**: Output `=== CHECKPOINT 1 PASSED === Baseline confirmed. Proceeding to experiment loop.`

**Agent action on failure**: Output `=== CHECKPOINT 1 FAILED ===` with a specific description of what failed. Do NOT proceed. The human must fix the environment or adjust the baseline specification before re-running.

**Why this matters**: If the baseline is broken, every subsequent experiment is meaningless. This is the "smoke test" for the entire research setup.

---

### Checkpoint 2: When spec_score Reaches 4/5 (Trigger: current score == 4 or 5, AND > previous best)

**When**: Agent achieves a spec_score of 4 or 5 that exceeds the previous best score.

**What to review**:
1. The full model specification (list all independent variables and their coefficients/significance).
2. The diagnostic profile: Did diagnostics pass? If VIF was the failure, is it due to polynomial terms (acceptable) or genuinely problematic collinearity?
3. **Economic interpretability audit**: 
   - Does the sign of each coefficient make theoretical sense?
   - Why did this change improve the score — what's the economic mechanism?
   - Is there a plausible story, or did we just find a spurious correlation?
4. Whether the improvement comes from adding substance vs. adding noise (check if adj-R² improvement is > 0.01 or marginal).

**Success criterion**: The specification makes statistical AND economic sense.

**Agent action on success**: Output `=== CHECKPOINT 2 PASSED ===` with a one-paragraph economic interpretation of the model. Ask human to confirm before continuing.

**Agent action on failure** (model is statistically good but economically implausible):
Output `=== CHECKPOINT 2 FAILED === Specification achieves high score but economic interpretation is questionable:` followed by the specific concern. Propose one alternative hypothesis to test. Wait for human direction.

**Why this matters**: In economics, statistical fit without theoretical coherence is worthless. This checkpoint prevents the agent from optimizing toward a spurious "best" model.

---

### Checkpoint 3: After 5 Consecutive Iterations Without Score Improvement (Trigger: score ≤ previous_best for 5 consecutive iterations)

**When**: The agent has discarded 5 consecutive experiments (or 5 experiments failed to improve the best score).

**What to review**:
1. List the last 5 experiments with their descriptions, scores, and discard reasons.
2. Category analysis of failed attempts: Were all attempts in the same category (e.g., all "add a variable")? Or did the agent try diverse approaches?
3. Current best model and its remaining weaknesses (which dimensions score 0?).
4. Propose a **qualitatively different search direction** — e.g., if all attempts were adding variables, propose functional form changes; if all were OLS tweaks, propose WLS or robust SE.

**Success criterion**: Human reviews the log and confirms the proposed new direction.

**Agent action**: Output `=== CHECKPOINT 3 TRIGGERED === 5 iterations without improvement.` then present the analysis above. Explicitly ask: `Suggested new direction: [proposal]. Proceed? Or redirect?`

**Agent action on failure** (human rejects the proposed direction): Accept the human's alternative direction. Record it. Restart loop with the new constraint.

**Why this matters**: Prevents the agent from getting stuck in a local optimum. Forces a "step back and rethink" moment — exactly what a human researcher would do when hitting a wall.

---

### When is full autonomy appropriate vs. human-in-the-loop?

- **Full autonomy** (like autoresearch): When the evaluation metric is fully objective, the search space is a closed engineering system, and "better" has no ambiguity (e.g., `val_bpb ↓` always means improvement).
- **Human-in-the-loop** (this workflow): When the domain requires theoretical interpretation (economics, management science), when priors and domain knowledge constrain the search, and when "better" is multi-dimensional with inherent trade-offs that require judgment. 

In our case, the agent handles the statistical optimization (running regressions, computing diagnostics, ranking by score), while the human retains authority over economic interpretation and research direction — a division of labor that mirrors how a principal investigator works with a research assistant.

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
