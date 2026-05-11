# Reviewer-grade replication packages

This folder reproduces the autoresearch-mincer kept-best specification
(`iter09`: OLS+HC3, top/bottom 2.5% of `lwage` trimmed) in Stata and R,
alongside the iter01 IV2SLS-nearc4 anchor.

| File | Tool | Output |
|---|---|---|
| `replicate_kept_best.do` | Stata 16+ | `replicate_kept_best.log`, `replicate_kept_best.tex` |
| `replicate_kept_best.qmd` | R + Quarto | HTML / PDF render with regression table and diagnostics |

## Stata

```bash
cd replication
stata -b do replicate_kept_best.do
# or in Stata:
# do replicate_kept_best.do
```

Requires base Stata. The script intentionally avoids ado packages so a
clean install reproduces the run.

## R / Quarto

```bash
cd replication
quarto render replicate_kept_best.qmd --to html
quarto render replicate_kept_best.qmd --to pdf
```

Required R packages (install once): `tidyverse`, `fixest`, `broom`,
`modelsummary`, `sandwich`, `lmtest`, `car`, `estimatr`.

## Expected results

| Specification | `educ` | SE | n |
|---|---|---|---|
| baseline (OLS, full) | 0.0715 | 0.0036 | 3003 |
| iter06 (trim 1%) | 0.0647 | 0.0035 | 2947 |
| **iter09 (trim 2.5%, kept best)** | **0.0569** | **0.0033** | **2857** |
| iter10 (trim 5%, hard-rule discard) | 0.0510 | 0.0030 | 2715 |
| iter01 (IV2SLS-nearc4, full) | 0.1249 | 0.0497 | 3003 |

All four OLS anchors should match the Python results in `results.tsv` to
four decimal places. The IV estimate matches Card (1995) to within
rounding.
