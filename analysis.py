"""
Mincer wage equation specification — Agent-editable file.
Modify this file to change the regression specification.
Only one file to edit: this is the agent's sandbox.

Usage: python analysis.py
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from prepare import generate_wage_data, evaluate_specification

# ---------------------------------------------------------------------------
# Load data (do not modify this section)
# ---------------------------------------------------------------------------
df = generate_wage_data()

# ---------------------------------------------------------------------------
# MODEL SPECIFICATION — Edit below this line
# ---------------------------------------------------------------------------

# Baseline: simple Mincer equation
# log(wage) ~ educ + exper + exper² + tenure + female + married + union

# Construct variables
df['log_wage'] = np.log(df['wage'])
df['exper_sq'] = df['exper'] ** 2

# Define model
X = df[['educ', 'exper', 'exper_sq', 'tenure', 'female', 'married', 'union']]
X = sm.add_constant(X)
y = df['log_wage']

# Estimate
model = sm.OLS(y, X).fit()

# ---------------------------------------------------------------------------
# Evaluate (do not modify this section)
# ---------------------------------------------------------------------------
result = evaluate_specification(model)
