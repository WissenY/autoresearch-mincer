# Autoresearch-Mincer: LLM Agent 自主实证研究工作流

> **课程**: DOTE 6635 AI for Business Research — Problem Set 9  
> **范式**: 仿照 Karpathy [autoresearch](https://github.com/karpathy/autoresearch) 的"程序即研究"思想，把人类的角色从"做研究"切换到"编写研究流程"。  
> **数据**: Card (1995) NLSYM extract（3010 obs，1976 wages，含 `nearc4` IV）。  
> **目标**: 让 Agent 在真实数据 + 真实识别问题上做规格搜索。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目架构

```
autoresearch-mincer/
├── data/
│   └── card.csv              # Card 1995 NLSYM, 3010 obs
├── prepare.py                # 只读基础设施（评估 + 诊断 + 多元宇宙）
├── analysis.py               # Agent 唯一可改的文件（规格定义）
├── program.md                # Agent 指令文件（人类编写）
├── results.tsv               # 实验日志
├── logs/
│   └── spec_curve.csv        # 当前 multiverse 系数分布
└── .gitignore
```

---

## 五维评分（每维 0/1，总分 0–5）

| # | 维度 | 1 分的条件 |
|---|---|---|
| 1 | **Identification** | IV: first-stage F > 10 (Stock-Yogo)；OLS: educ 系数在 multiverse 区间内 **且** BP rejecting 时使用 robust SE |
| 2 | **OOS fit** | 5-fold CV-MSE ≤ running best × 1.005 |
| 3 | **Spec stability** | educ 系数落在 multiverse 中位数 ±25% |
| 4 | **Diagnostics** | BP 拒 → 用 HC SE；RESET 不拒；max VIF < 15 |
| 5 | **Parsimony** | n_params ≤ max(6, n_obs/30) |

**Keep / Discard 规则**：

```
KEEP  iff  spec_score ≥ previous_best
       AND identification == 1
       AND cv_mse ≤ running_best × 1.005
DISCARD otherwise
```

---

## 快速开始

```bash
# 1) 数据已包含在仓库中（data/card.csv）
# 2) 跑 baseline
python analysis.py

# 3) 让 Agent 接管
# 把仓库目录交给 Claude Code / Codex / Cursor，提示词：
#   "请阅读 program.md 并启动实验循环。第一步先跑 baseline，触发 Checkpoint 1。"
```

---

## Baseline 结果（已记录在 `results.tsv` 第一行）

| 字段 | 值 |
|---|---|
| Estimator | OLS, HC3 |
| Sample | 3003 obs（drop missing on `lwage, educ, exper, black, south, smsa, married`） |
| Specification | `lwage ~ educ + (exper - mean) + (exper - mean)² + black + south + smsa + married` |
| **educ 系数** | **0.0715** (SE = 0.0036, p ≈ 0) |
| CV-MSE (5-fold) | 0.13577 |
| BIC | 2575.9 |
| Multiverse median | 0.0721（5/95 分位 = 0.0508 / 0.0903） |
| BP p | 0.0055 (异方差 → 已用 HC3) |
| RESET p | 0.9047 (无设定误差) |
| Max VIF | 5.69（已 center exper） |
| **spec_score** | **5/5** |

IV 路径（已 smoke-tested）：替换为 `IV2SLS` with `nearc4` →
- First-stage F = 15.75（强工具）
- IV educ 系数 = 0.1249（与 Card 1995 报告 ~13% 一致）

---

## 关键设计决策

### 1. 为什么 baseline 是 OLS 而不是 IV

OLS baseline 建立 multiverse 的"地面"。Agent 在迭代中**应当**主动尝试 IV——这就是 identification 维度奖励的方向。

### 2. 为什么删除"educ 显著为正"作为奖励

奖励"显著为正"等于把 specification mining 写进 reward function。Card 1995 的核心贡献恰恰是发现 IV > OLS（OLS 对 educ 的估计被 ability bias 向下偏）。让数据说话，不让奖励函数说话。

### 3. 为什么 `results.tsv` 入 git

实验历史是不可重建的资产——version-controlling 实验日志是复现性的基本要求。

### 4. 为什么 multiverse 在 `prepare.py` 内固定

如果让 Agent 自己定义 multiverse，它会通过收缩 multiverse 范围来让自己的 spec 永远"稳定"。放在只读的 `prepare.py` 里 = Agent 不能 game。

---

## 文献锚定

- **Mincer (1974)** — *Schooling, Experience, and Earnings*
- **Card (1995, 1999, 2001)** — NLSYM with `nearc4` IV
- **Heckman, Lochner & Todd (2006)** — 现代返回率估计的方法论评述
- **Angrist & Pischke (2010)** — *The Credibility Revolution*
- **Simonsohn, Simmons & Nelson (2020)** — Specification curve analysis
- **Romano & Wolf (2005)** — Step-down family-wise p-value control
- **Wooldridge (2019, ch. 6.2)** — 多项式 centering 与 VIF

---

## License

MIT
