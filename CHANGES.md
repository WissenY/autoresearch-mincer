# Post-run changes (v2 artifacts produced after the documented 13-iteration loop)

The artifacts in this file were added *after* the 13-iteration run in
`results.tsv` was complete. They do not modify that run; they implement the
fixes the reflection in section 4.3 of the write-up proposes.

## 1. Dual-multiverse fix (`prepare.py`)

**Bug in v1.** The OLS multiverse was the only reference set for the
specification-stability dimension. IV iterations were judged against the OLS
distribution, which the credibility-revolution literature explicitly predicts
should *differ* from the IV LATE on compliers (Card 1999). As a result,
iter01 (IV2SLS-nearc4, first-stage F = 15.7, educ = 0.125) scored 3/5 instead
of recognising a defensible identification strategy.

**v2 fix.**

- Added `iv_specification_curve(df, instruments=("nearc4",))` next to the
  existing `specification_curve(df)`. Sweeps control set × sample restriction
  × instrument choice (`nearc4`, `nearc2`, `nearc4+nearc2`) using IV2SLS.
- Modified `evaluate_specification` to detect IV iterations (`is_iv == True`)
  and route them to the IV multiverse for the `spec_stability` dimension.
  OLS iterations continue to use the OLS multiverse.
- Added `multiverse_used` to the returned JSON so the evaluation log is
  self-documenting.

**Smoke test** (`scripts/smoke_iv_v2.py`):

| Iter | v1 score | v2 score | Δ on which dimension |
|---|---|---|---|
| iter01 (IV2SLS-nearc4, full) | 3/5 | 4/5 | `spec_stability` now passes (educ 0.125 within IV 5/95 band 0.091–0.575) |

The remaining `oos_fit = 0` for IV is structural: 2SLS training MSE is
expected to exceed OLS CV-MSE because IV trades efficiency for consistency.
A future v3 would stratify the `oos_fit` running-best by estimator class.

## 2. Appendix multiverse (`appendix/big_multiverse.py`)

215 specifications (110 OLS + 105 IV2SLS) sweeping eleven control menus, five
sample restrictions, two cov types, and three instrument choices. Uses
statsmodels only — no new dependencies. Outputs:

- `logs/big_multiverse.csv` — raw spec-level results
- `logs/big_multiverse_summary.json` — quantile summaries by estimator
- `logs/big_multiverse_figure.png` — two-panel specification curve

**Key numbers from the deeper multiverse:**

| Estimator | n | median | 5/95 band | share significant |
|---|---|---|---|---|
| OLS | 110 | 0.0627 | [0.041, 0.086] | 100% |
| IV2SLS | 105 | 0.162 | [0.110, 0.376] | 74% |

The kept-best iter09 estimate (0.0569) sits at the **lower edge** of the
expanded OLS 5/95 band, confirming the documented run's conclusion: it is
defensible but not central in the multiverse. The hard identification rule
that blocked iter10 (educ = 0.051) is vindicated by the deeper sweep —
iter10 sits *below* even the 110-spec 5% bound.

## 3. Annotated specification curve (`logs/multiverse_curve.png`)

Re-rendered from `logs/spec_curve.csv` with documented-run anchors marked:
baseline, iter06 (KEEP), iter09 (KEEP, best), iter10 (DISCARD, hard-rule).
This is the figure referenced in Q3.2 of the write-up.

## 4. Reviewer-grade replication packages (`replication/`)

- `replicate_kept_best.do` (Stata 16+) — base Stata, no ado dependencies.
  Reproduces baseline, iter06, iter09, iter10, iter01-IV.
- `replicate_kept_best.qmd` (R + Quarto) — uses `fixest`, `modelsummary`,
  `estimatr`. Renders HTML/PDF with a publication-ready regression table.
- `README.md` — expected outputs and run instructions.

These add a non-Python reviewer path to the artifact, which is the most
common ABS3-tier referee request.

## What was NOT changed

- The `results.tsv` 13-iteration journal is unchanged. The v1 evaluator
  is the one those rows were produced under.
- `program.md` is unchanged. The v2 dual-multiverse fix is a redesign for
  a future v2 program.md; using v2 inside the original loop would invalidate
  the comparability of the documented iterations.
- The hard identification rule and the parsimony tiebreaker are unchanged.
  Both fired in the run and both fired correctly.
