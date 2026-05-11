# Autonomous Research Workflow: Returns to Schooling — Specification & Identification Search

## Research Problem

**Question**: What specification of a Mincer log-wage equation best estimates the returns to one additional year of schooling on Card's (1995) NLSYM sample, balancing identification credibility, out-of-sample fit, and methodological transparency?

**Why this question and not "best fit"**: A pure descriptive search would invite specification mining. Following the credibility-revolution framing (Angrist & Pischke 2010), we score every specification on whether it is *defensible* — not just whether it fits in-sample. The agent searches over OLS *and* IV (Card's near-college instrument), and we report the entire specification curve so the reader can audit the search.

**Single (composite) metric**: A 5-dimension `spec_score` (0–5), produced by the read-only `evaluate_specification()` in `prepare.py`. Each dimension is binary (0/1), so the score is integer-valued and fully reproducible.

**Fixed resource budget**: One specification change per iteration (one hypothesis at a time). Each `python analysis.py` run takes < 30 s on a laptop because everything is in-memory. There is no wall-clock budget; the budget is *idea per iteration*.

**Why suitable for autonomous experimentation**: Card's NLSYM has 3010 observations of 1976 wages with a celebrated instrument (`nearc4`, indicator for living near a 4-year college at age 14). The Mincer / Card specification space is large but well-understood: control sets, sample restrictions, estimator choice (OLS vs IV2SLS), and SE handling. An agent navigating this space with the right reward function produces a *specification curve* — the modern way to report robustness (Simonsohn, Simmons & Nelson 2020).

---

## File Structure and Boundaries

### READ-ONLY files (DO NOT MODIFY)

| File | Role |
|------|------|
| `data/card.csv` | Card (1995) NLSYM extract from Rdatasets/Wooldridge mirror, 3010 obs |
| `prepare.py` | Data loading, `evaluate_specification()`, `cv_mse_5fold()`, `specification_curve()`, `romano_wolf_pvalues()`, fixed `reset_test()`, `first_stage_f()` |

### EDITABLE file (the agent modifies this — and only this)

| File | Role |
|------|------|
| `analysis.py` | Defines the regression specification: variable selection, transformations, sample restrictions, estimator (OLS / IV2SLS), and SE choice. The agent edits between the marked `MODIFY BELOW / MODIFY ABOVE` lines. |

### Constraints

- No new packages. Only `numpy`, `pandas`, `statsmodels` (already available).
- Never modify `prepare.py`. Never modify `data/card.csv`. They are the ground truth.
- Never invent data: only use columns that are already in `card.csv`.
- Always keep `educ` as the regressor of interest, indexed at column 1 (after the constant). The evaluator depends on this.
- Respect the parsimony rule and the multiverse-stability rule (see Reward dimensions below).

### Design rationale

This separation is the same as Karpathy's `autoresearch`: `prepare.py` defines the *evaluation*, `analysis.py` defines the *experiment*. The agent's search space is the model specification; the evaluator is fixed and cannot be gamed.

What makes this version *empirical-research grade* rather than autoresearch's *engineering grade*:

1. **Real data**, not synthetic — there is no hidden DGP for the agent to memorize.
2. **The reward function refuses to reward a "positive significant educ"** — reward is on identification credibility, out-of-sample fit, multiverse stability, diagnostic correctness, and parsimony. This blocks the most obvious p-hacking incentive.
3. **The full specification curve is computed every iteration** and saved to `logs/spec_curve.csv`. Any single specification is judged against this multiverse, not against itself.
4. **IV (Card 1995) is in scope.** The agent can swap in `IV2SLS` with `nearc4` as the instrument; identification scores reward a Stock-Yogo-strong first stage (F > 10).

---

## The Experiment Loop

### Initial Setup (run once — ends at Checkpoint 1)

1. Verify `numpy`, `pandas`, `statsmodels` are available (`python -c "import numpy, pandas, statsmodels"`).
2. Verify `data/card.csv` exists and has 3010 rows.
3. Run baseline: `python analysis.py > run.log 2>&1`.
4. Read the structured output (text block + JSON block).
5. Confirm `results.tsv` has the baseline row already populated (it ships pre-populated).
6. **IMMEDIATELY trigger Checkpoint 1** — do NOT proceed to the loop until the human confirms.

### Per-Iteration Loop

LOOP FOREVER (start from step 1):

**Step 1 — Look at state**
Read `results.tsv`. Identify the running best `cv_mse`, the best `spec_score`, the diagnostic profile of the last kept model, and which change categories have been tried recently.

**Step 2 — Formulate one hypothesis-driven change**
Modify `analysis.py` (between the `MODIFY BELOW / MODIFY ABOVE` markers) with **one** change grounded in econometric reasoning. Valid change categories:

| Category | Examples |
|----------|----------|
| Identification | Switch to `IV2SLS` using `nearc4` (Card 1995); try `nearc2` or parental education as alternative IV; over-identified IV with both `nearc4` and `nearc2`; add ability proxies (`IQ`, `KWW`) as Heckman-style controls for omitted ability bias |
| Control set | Add region dummies (`reg662`–`reg669`); add family-structure controls (`momdad14`, `sinmom14`); restrict to the non-missing `IQ` subsample for ability-bias robustness |
| Sample restriction | Trim top/bottom 1% of `lwage`; restrict to `momdad14 == 1`; restrict by `exper` range |
| Functional form | Replace `educ` (linear) with credential dummies; interact `educ × black` (heterogeneous returns); spline in `exper` |
| SE / inference | Switch to `cov_type='HC3'` if BP rejects; cluster on region (`reg66*`); bootstrap SE |
| Model reduction | Drop a control whose CV-MSE contribution is null — a parsimony win |

**NOT allowed**: random variable fishing. Every change must come with a 1-line econometric justification in the git commit message.

**Step 3 — Commit the change**
```
git add analysis.py
git commit -m "<short justification>"
```

**Step 4 — Run the experiment**
```
python analysis.py > run.log 2>&1
```

**Step 5 — Parse results**
The structured output contains both a human-readable block (lines starting with `spec_score:`, `identification:`, …) and a JSON block at the bottom (after `--- json ---`). Parse the JSON for typed fields; use grep on the text block for quick sanity checks.

If parsing fails or the run crashed → run `tail -n 50 run.log` for the traceback. Fix trivial bugs (typos, missing imports) once. If the idea itself causes the failure → log status `crash` and revert.

**Step 6 — Read the score**
The 5 dimensions (each binary, total 0–5):

| # | Dimension | What 1 means |
|---|-----------|--------------|
| 1 | **Identification** | If IV: first-stage F > 10 (Stock-Yogo). If OLS: educ coef stable in the multiverse AND BP-rejecting models use a robust SE |
| 2 | **Out-of-sample fit** | 5-fold CV MSE within 0.5% of (or better than) the running best `cv_mse` |
| 3 | **Specification stability** | educ coef within ±25% of the multiverse median (the multiverse is fixed by `prepare.py`, so the agent cannot game it) |
| 4 | **Diagnostic soundness** | BP rejection handled (HC SE used); RESET does not reject; max-VIF < 15 (after centering polynomials, this should be easy) |
| 5 | **Parsimony** | Model has at most `max(6, n_obs / 30)` parameters |

The composite `spec_score` is the sum.

**Step 7 — Keep / Discard decision**

```
IF spec_score >= previous_best_score AND
   (identification == 1) AND
   (cv_mse <= running_best_cv_mse * 1.005):
   → KEEP (git stays on this commit)
ELIF spec_score == previous_best_score AND model is strictly simpler (fewer params, same CV-MSE):
   → KEEP (parsimony win)
ELSE:
   → DISCARD (git reset --hard HEAD~1)
```

**Hard rule**: identification == 0 always discards, regardless of fit. We do not reward econometrically indefensible models even if they predict well.

**Crash rule**: if a fix fails on the first attempt, log `status=crash`, append the row, then `git reset --hard HEAD~1`.

**Simplicity tiebreaker**: between two models with equal `spec_score` AND equal CV-MSE, prefer the one with fewer parameters. Always.

**Stagnation rule**: if no improvement (i.e. no `keep`) for 5 consecutive iterations, you have hit a plateau — trigger Checkpoint 3.

**Step 8 — Log to results.tsv**
Append one TAB-separated row matching the header. The full schema is below in *Logging Results*. Then commit `results.tsv` along with the next analysis change (results.tsv IS tracked in git — it is the experiment journal).

**Step 9 — Checkpoint gate**
Before looping back to Step 1, check whether any checkpoint condition has triggered. If yes → **PAUSE** and emit the checkpoint header. Do NOT iterate further until the human responds.

---

## Output Format

After each run, `analysis.py` calls `evaluate_specification()` which prints first a text block:

```
---
spec_score:        4
identification:    1
  reason:          IV first-stage F=15.7
  first_stage_F:   15.7486
oos_fit:           1
  cv_mse:          0.135772
  prev_best_cv:    NA
spec_stability:    1
  educ_coef:       0.0715
  multiverse_med:  0.0721
  multiverse_5_95: 0.0508/0.0903
diagnostics:       1
  bp_p:            0.0055
  reset_p:         0.9047
  max_vif:         5.69
  cov_type:        HC3
  diag_fails:      none
parsimony:         1
  n_params:        8
  n_obs:           3003
  bic:             2575.93
  adj_r2:          0.3117
core_sign:         positive
core_p:            0.0000
```

…followed by a `--- json ---` block with the same fields as a JSON object. The agent SHOULD prefer the JSON for parsing.

---

## Crash and Error Handling

| Failure type | Handling |
|--------------|----------|
| Python syntax error | Fix once. If the idea itself causes the error → discard. |
| Missing import | Add it (allowed: `numpy`, `pandas`, `statsmodels` only). |
| Singular matrix / perfect collinearity | The model is ill-specified — discard. |
| All diagnostic tests fail | Discard. |
| NaN in `cv_mse` or `educ_coef` | Discard. Check sample size, missing values. |
| First-stage F < 10 (IV path) | The instrument is weak in this subsample — discard. Document in `description`. |
| Run > 60 s | Kill it. Treat as crash. |

---

## Parsimony / Simplicity Criterion (extended)

Empirical research rewards parsimony for two reasons: degrees-of-freedom inflation and over-fitting. The reward implements both:

1. **Hard cap on parameter count**: `n_params ≤ max(6, n_obs/30)`. With n=3010 this is ≤ 100 — generous, but rules out absurd specifications.
2. **A simplification that preserves CV-MSE = automatic keep.** Removing a control that does not help out-of-sample is unambiguously good.
3. **Adding a variable must lower CV-MSE by enough to keep `oos_fit = 1`** (within 0.5% of the running best). Marginal in-sample gains do not survive cross-validation.
4. **Interaction terms must be *theoretically* justified** in the commit message — e.g., `educ × black` because Card-Krueger document heterogeneous returns by race.

---

## Human Stop-and-Check Points

The agent does NOT run unattended. At each of three critical checkpoints, the agent MUST pause and present a structured status report. The agent must NOT resume until the human explicitly responds "proceed" or gives new direction.

**Protocol for ALL checkpoints**: when triggered, the agent:
1. Prints `=== CHECKPOINT N TRIGGERED ===` (N ∈ {1, 2, 3}).
2. Presents the review items below in a structured format.
3. Asks: `Proceed? Or redirect?`
4. Waits for human response before any further action.

---

### Checkpoint 1: After Baseline Run (Trigger: iteration count == 1)

**When**: immediately after the baseline experiment completes.

**What to review**:
1. The baseline `spec_score` and full diagnostic block.
2. The baseline `educ_coef` lies within the multiverse 5/95 band (sanity check: the baseline is itself a member of the multiverse, so this is a smoke test of the scoring code, not the model).
3. CV-MSE is finite and reasonable (Card NLSYM baselines: ≈ 0.13–0.16).
4. `n_obs` is what we expect after sample restrictions (≈ 3000 with the default control set).
5. The first-stage F is reported as NA (baseline is OLS) — a non-NA value here means the baseline accidentally specified IV, which is a setup error.

**Removed from v1**: the v1 of this checkpoint required `core_sign == positive AND core_p < 0.05` — that has been deleted. Hard-coding "positive significant educ" as a baseline acceptance gate would re-introduce the p-hacking incentive the reward function is designed to remove. The sign should *come out of the data*, not be required at the gate.

**Success criterion**: every check above passes.

**Agent action on success**: emit `=== CHECKPOINT 1 PASSED === Baseline confirmed. Proceeding to experiment loop.`

**Agent action on failure**: emit `=== CHECKPOINT 1 FAILED ===` with the specific failure. Do NOT proceed. The human fixes the environment / data path before re-running.

**Why this matters**: if the baseline is broken or the multiverse is mis-computed, every subsequent score is meaningless.

---

### Checkpoint 2: When `spec_score` reaches 5/5 OR Identification Strategy Changes (Trigger: spec_score == 5 AND > previous_best, OR estimator switches OLS↔IV)

**When**:
- (a) the agent first achieves a 5/5 specification, OR
- (b) any iteration switches estimator class (OLS → IV2SLS, or vice versa, or changes the IV).

**What to review**:
1. The full kept specification (variables, sample, estimator, SE).
2. Identification audit:
   - If IV: the first-stage F (must be > 10), the sign of the first-stage coefficient on `nearc4` (must be positive — proximity should *raise* schooling), and an English statement of the exclusion restriction.
   - If OLS: an explicit statement of the *assumed* exogeneity of `educ` and what the omitted-variable threats are (ability bias, measurement error).
3. Compare `educ_coef` to the multiverse median and to canonical literature: Card 1999 (6–15%), Heckman-Lochner-Todd 2006 (≈ 10%). If outside that range, why?
4. Whether the score gain came from substance (better identification, lower CV-MSE) or from cosmetic changes.

**Success criterion**: the specification is *both* statistically well-scored *and* economically defensible (the agent can articulate the identification assumption in plain English).

**Agent action on success**: emit `=== CHECKPOINT 2 PASSED ===` with a one-paragraph economic interpretation.

**Agent action on failure**: emit `=== CHECKPOINT 2 FAILED === high score but identification story is thin: <reason>`. Propose one alternative spec that would address the concern. Wait for human direction.

**Why this matters**: reward functions reward what they can measure; identification credibility is partially about *narrative*, which the human still owns.

---

### Checkpoint 3: After 5 Consecutive Iterations Without `keep` (Trigger: 5 consecutive `discard`)

**When**: 5 consecutive experiments fail to advance the running best.

**What to review**:
1. List of last 5 experiments, their `spec_score`, the dimension(s) they failed, and the change category.
2. Category diversity: were all 5 attempts in the same category (e.g., all "control set")? If so, the agent has exhausted that direction.
3. The current best model's weakest dimension — that is the next direction to push on.
4. Propose a *qualitatively different* change. For example, if all 5 failures were OLS control-set tweaks, propose IV with `nearc4`. If all 5 were IV variations with weak first-stage F, propose returning to OLS with ability-proxy controls.

**Success criterion**: human reviews and confirms the next direction.

**Agent action**: emit `=== CHECKPOINT 3 TRIGGERED === plateau after 5 iterations.` Present the analysis and explicitly ask `Suggested new direction: [proposal]. Proceed or redirect?`.

**On rejection**: accept the human's alternative direction and restart the loop with that constraint.

**Why this matters**: prevents getting stuck in a narrow corner of the search space — the same "step back" instinct that a human researcher has when ideas dry up.

---

### When is full autonomy appropriate vs. human-in-the-loop?

- **Full autonomy** (Karpathy `autoresearch`): when the metric is fully objective, the search space is closed-system engineering, and "better" is unambiguous (`val_bpb ↓`).
- **Human-in-the-loop** (this workflow): empirical economics requires *narrative defensibility* — exclusion restrictions, identification assumptions, the choice of population. A composite score gets us 90% of the way; the last 10% is judgment. Hence three checkpoints, not zero.

Division of labor: the agent handles statistical optimization (running regressions, computing diagnostics, multiverse sweeps); the human owns identification narrative and decides when the empirical case is publishable.

---

## Logging results

`results.tsv` is **tracked in git**. The full experiment journal is the research artifact.

Schema (TAB-separated, in this order):

```
commit	spec_score	identification	oos_fit	spec_stability	diagnostics	parsimony	educ_coef	educ_se	educ_p	cv_mse	first_stage_F	bp_p	reset_p	max_vif	cov_type	estimator	n_params	n_obs	bic	multiverse_median	multiverse_5	multiverse_95	status	description
```

Columns:

| # | Column | Meaning |
|---|--------|---------|
| 1 | `commit` | 7-char git hash (or `baseline` for the seed row) |
| 2 | `spec_score` | 0–5 composite |
| 3–7 | `identification` … `parsimony` | 0/1 dimension scores |
| 8 | `educ_coef` | Estimated coefficient on `educ` |
| 9 | `educ_se` | SE of `educ` |
| 10 | `educ_p` | p-value of `educ` |
| 11 | `cv_mse` | 5-fold CV MSE (or training MSE for IV) |
| 12 | `first_stage_F` | First-stage F (NA for OLS) |
| 13 | `bp_p` | Breusch-Pagan p (NA for IV) |
| 14 | `reset_p` | Ramsey RESET p (NA for IV) |
| 15 | `max_vif` | Max VIF among non-constant regressors |
| 16 | `cov_type` | `HC3`, `nonrobust`, `cluster`, `iv2sls`, … |
| 17 | `estimator` | `OLS` or `IV2SLS-<instrument>` |
| 18 | `n_params` | Including the constant |
| 19 | `n_obs` | After sample restriction |
| 20 | `bic` | Schwarz criterion |
| 21–23 | `multiverse_median`, `5`, `95` | Multiverse summary at this iteration |
| 24 | `status` | `keep` / `discard` / `crash` |
| 25 | `description` | One-line English summary of the change |

---

## Research Direction and Scope

**Core research question**: what is the credible return to one additional year of schooling on Card's NLSYM, and how robust is that estimate across plausible specifications?

**In-scope changes**:
- Variable choices from `card.csv`: any subset of {`black`, `south`, `smsa`, `married`, `IQ`, `KWW`, `momdad14`, `sinmom14`, `step14`, `libcrd14`, `motheduc`, `fatheduc`, `reg662`–`reg669`}.
- Functional form: linear or with credential-style dummies; centred polynomials in `exper`; interactions with theoretical motivation.
- Sample restrictions: trim outliers, restrict by `exper` range, restrict by `momdad14`, drop missing `IQ`/`KWW` for ability-controlled subsamples.
- Estimator: `OLS` with `cov_type ∈ {nonrobust, HC3, cluster}`; `IV2SLS` with instruments from {`nearc4`, `nearc2`, `motheduc`, `fatheduc`} (single or over-identified).

**Out-of-scope changes**:
- Synthesising new variables or merging in external data.
- Non-linear binary models (probit/logit) — the outcome is continuous log-wage.
- Time-series / panel methods — the data is cross-sectional 1976.

**Final deliverable** (when the human terminates the loop):
1. The kept `analysis.py` (the best specification).
2. The full `results.tsv` (the search journal).
3. `logs/spec_curve.csv` (the multiverse from the last iteration) plus a 1-page summary of where the kept specification sits within it.
4. A short narrative (≤ 1 page) on the identification strategy and what it assumes.
