/*------------------------------------------------------------------*
 |  replicate_kept_best.do
 |
 |  Reviewer-grade Stata replication of the iter09 kept-best
 |  specification from the autoresearch-mincer run.
 |
 |  Specification:
 |    log(wage) = b0 + b1*educ + b2*exper_c + b3*exper_c^2
 |              + b4*black + b5*south + b6*smsa + b7*married + e
 |
 |    Sample: Card (1995) NLSYM, n=3010 trimmed to top/bottom 2.5%
 |    of lwage (kept best: 2.5% symmetric Winsorisation by drop).
 |
 |    Estimator: OLS with HC3 heteroskedasticity-robust SE.
 |
 |  Expected result: educ_coef ~ 0.0569, SE ~ 0.0033, n ~ 2857.
 |
 |  Run:  stata -b do replicate_kept_best.do
 *------------------------------------------------------------------*/

version 16
clear all
set more off
capture log close
log using replicate_kept_best.log, replace text

* Load data (assumes card.csv lives one directory up)
import delimited using "../data/card.csv", clear varnames(1)

* Sample restrictions ------------------------------------------------
keep if !missing(lwage, educ, exper, black, south, smsa, married)

* Trim top and bottom 2.5% of lwage (the iter09 kept-best move)
quietly summarize lwage, detail
local p025 = r(p2_5)
local p975 = r(p97_5)
keep if lwage >= `p025' & lwage <= `p975'
display "Sample size after trim: " _N

* Center experience before squaring (Wooldridge 2019 §6.2) -----------
egen exper_mean = mean(exper)
generate exper_c   = exper - exper_mean
generate expersq_c = exper_c^2

* Kept-best specification --------------------------------------------
regress lwage educ exper_c expersq_c black south smsa married, vce(hc3)

* Save coefficient table for the appendix ----------------------------
estimates store iter09
estout iter09 using replicate_kept_best.tex, replace ///
    cells(b(fmt(4)) se(par fmt(4))) ///
    stats(N r2_a, labels("Observations" "Adj R-sq") fmt(0 4)) ///
    style(tex) label nonumbers

* Diagnostics --------------------------------------------------------
* Breusch-Pagan
estat hettest, normal
* Ramsey RESET
ovtest, rhs
* VIF (after non-robust regress for VIF — VIF is a function of X only)
quietly regress lwage educ exper_c expersq_c black south smsa married
vif

* Specification curve (recompute the multiverse anchor estimates) ----
* Baseline (full sample, no trim) -- iter00
regress lwage educ exper_c expersq_c black south smsa married, vce(hc3)
display "BASELINE educ coefficient: " _b[educ]

* iter06 — trim ±1%
preserve
    quietly summarize lwage, detail
    local p01 = r(p1)
    local p99 = r(p99)
    keep if lwage >= `p01' & lwage <= `p99'
    regress lwage educ exper_c expersq_c black south smsa married, vce(hc3)
    display "ITER06 (trim 1%) educ: " _b[educ]
restore

* iter09 -- trim ±2.5%  (active sample)
regress lwage educ exper_c expersq_c black south smsa married, vce(hc3)
display "ITER09 (trim 2.5%, kept best) educ: " _b[educ]

* iter01 IV2SLS-nearc4 (re-load full sample for this run)
import delimited using "../data/card.csv", clear varnames(1)
keep if !missing(lwage, educ, exper, black, south, smsa, married, nearc4)
egen exper_mean = mean(exper)
generate exper_c   = exper - exper_mean
generate expersq_c = exper_c^2
ivregress 2sls lwage exper_c expersq_c black south smsa married (educ = nearc4)
display "ITER01 (IV2SLS-nearc4) educ: " _b[educ]
estat firststage, all forcenonrobust

log close
