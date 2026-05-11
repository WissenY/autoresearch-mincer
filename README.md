# Autoresearch-Mincer: LLM Agent Autonomous Empirical Research Workflow

> **Course**: DOTE 6635 AI for Business Research — Problem Set 9  
> **Paradigm**: Adapts Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) "program as research" philosophy — shifting the human role from *doing* research to *programming* the research process.  
> **Data**: Card (1995) NLSYM extract (3,010 obs, 1976 wages, with `nearc4` IV).  
> **Goal**: Let an LLM agent conduct specification search on real data with a real identification problem.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Project Architecture

```
autoresearch-mincer/
├── data/
│   └── card.csv              # Card 1995 NLSYM, 3,010 obs
├── prepare.py                # Read-only infrastructure (evaluation + diagnostics + multiverse)
├── analysis.py               # Agent-editable file (specification definition)
├── program.md                # Agent instruction file (human-written)
├── results.tsv               # Experiment log
├── logs/
│   └── spec_curve.csv        # Current multiverse coefficient distribution
└── .gitignore
```

---

## Five-Dimensional Scoring (0/1 per dimension, total 0–5)

| # | Dimension | Condition for 1 point |
|---|---|---|
| 1 | **Identification** | IV: first-stage F > 10 (Stock-Yogo); OLS: educ coefficient within multiverse range **and** robust SE used when BP rejects |
| 2 | **OOS Fit** | 5-fold CV-MSE ≤ running best × 1.005 |
| 3 | **Spec Stability** | educ coefficient within multiverse median ±25% |
| 4 | **Diagnostics** | BP rejection → HC SE applied; RESET not rejected; max VIF < 15 |
| 5 | **Parsimony** | n_params ≤ max(6, n_obs/30) |

**Keep / Discard Rule**:

```
KEEP  iff  spec_score ≥ previous_best
       AND identification == 1
       AND cv_mse ≤ running_best × 1.005
DISCARD otherwise
```

---

## Quick Start

```bash
# 1) Data is bundled in the repo (data/card.csv)
# 2) Run baseline
python analysis.py

# 3) Hand over to the agent
# Point Claude Code / Codex / Cursor at this repo and prompt:
#   "Read program.md and kick off the experiment loop. Run baseline first, then trigger Checkpoint 1."
```

---

## Baseline Results (recorded in `results.tsv` row 1)

| Field | Value |
|---|---|
| Estimator | OLS, HC3 |
| Sample | 3,003 obs (drop missing on `lwage, educ, exper, black, south, smsa, married`) |
| Specification | `lwage ~ educ + (exper - mean) + (exper - mean)² + black + south + smsa + married` |
| **educ coefficient** | **0.0715** (SE = 0.0036, p ≈ 0) |
| CV-MSE (5-fold) | 0.13577 |
| BIC | 2575.9 |
| Multiverse median | 0.0721 (5th/95th percentile = 0.0508 / 0.0903) |
| BP p | 0.0055 (heteroskedasticity → HC3 applied) |
| RESET p | 0.9047 (no specification error) |
| Max VIF | 5.69 (exper centered) |
| **spec_score** | **5/5** |

IV path (smoke-tested): switch to `IV2SLS` with `nearc4` →
- First-stage F = 15.75 (strong instrument)
- IV educ coefficient = 0.1249 (consistent with Card 1995 ~13%)

---

## Literature

- **Mincer (1974)** — *Schooling, Experience, and Earnings*
- **Card (1995, 1999, 2001)** — NLSYM with `nearc4` IV
- **Heckman, Lochner & Todd (2006)** — Modern returns-to-education estimation survey
- **Angrist & Pischke (2010)** — *The Credibility Revolution*
- **Simonsohn, Simmons & Nelson (2020)** — Specification curve analysis
- **Romano & Wolf (2005)** — Step-down family-wise p-value control
- **Wooldridge (2019, ch. 6.2)** — Polynomial centering and VIF

---

## License

MIT
