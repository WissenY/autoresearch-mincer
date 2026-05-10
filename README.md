# Autoresearch-Mincer: LLM Agent 自主实证研究工作流（ABS3 级别）

> **课程**: DOTE 6635 AI for Business Research — Problem Set 9
> **范式**: 仿照 Karpathy [autoresearch](https://github.com/karpathy/autoresearch) 的"程序即研究"思想，把人类的角色从"做研究"切换到"编写研究流程"。
> **数据**: Card (1995) NLSYM extract（3010 obs，1976 wages，含 `nearc4` IV）。
> **目标**: 让 Agent 在真实数据 + 真实识别问题上做规格搜索，且**奖励函数本身不奖励 p-hacking**。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 与 v1（合成数据 + 单维 educ-显著奖励）相比的关键变化

| 维度 | v1 (合成 DGP) | v2 (现版本，ABS3 级别) |
|---|---|---|
| **数据** | `numpy.random` 合成已知 DGP | Card 1995 NLSYM 真实数据 (`data/card.csv`) |
| **识别** | 不在 scope | **`IV2SLS` with `nearc4` 在 scope**；first-stage F 写进打分 |
| **奖励中的核心** | `educ` 系数 > 0 且显著 ⇒ +1 (p-hacking 激励) | **删除**。改为 IV first-stage F、CV-MSE、multiverse 稳定性、诊断响应、parsimony |
| **样本外评估** | 无 | 5-fold CV-MSE |
| **Specification curve** | 无 | 每轮自动跑 32 个 multiverse spec，输出 `logs/spec_curve.csv`（Simonsohn et al. 2020） |
| **多重检验校正** | 无 | `prepare.romano_wolf_pvalues()` 提供 Romano-Wolf step-down family-wise p-values |
| **RESET 实现** | 双常数 bug，仅 fitted² 单变量 t | 修复：joint F-test on fitted² + fitted³，无双常数 |
| **`results.tsv`** | `.gitignore` 排除 | **入 git**（Karpathy convention） |
| **VIF 阈值** | 死板 ≥ 15 | 同样 ≥ 15，但 baseline 已 center experience 消除多项式人造共线性 |

---

## 项目架构

```
autoresearch-mincer/
├── data/
│   └── card.csv              # 🔒 Card 1995 NLSYM, 3010 obs, 真实数据
├── prepare.py                # 🔒 只读基础设施
│                             #    - load_card_data()
│                             #    - evaluate_specification()      ← 5维评分
│                             #    - cv_mse_5fold()                ← 样本外
│                             #    - specification_curve()         ← 多元宇宙
│                             #    - romano_wolf_pvalues()         ← 多重检验
│                             #    - reset_test() (修复版)
│                             #    - first_stage_f()               ← IV 强弱
├── analysis.py               # ✏️ Agent 唯一可改的文件
│                             #    - 控制变量 / 样本限制 / OLS↔IV
├── program.md                # 📜 Agent 指令（人类编写）
├── results.tsv               # 📊 实验日志（入 git，研究 artifact）
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

**Keep / Discard 规则**（重点）：

```
KEEP  iff  spec_score ≥ previous_best
       AND identification == 1
       AND cv_mse ≤ running_best × 1.005
DISCARD otherwise — 不可识别即丢弃，再好的拟合也不要
```

---

## 快速开始

```bash
# 1) 数据已包含在仓库中（data/card.csv）。如果需要重新下载：
curl -fsSL "https://vincentarelbundock.github.io/Rdatasets/csv/wooldridge/card.csv" -o data/card.csv

# 2) 跑 baseline
python analysis.py
# spec_score: 5/5
# educ_coef: 0.0715  (Card OLS baseline ≈ 7.15% Mincer return — 与 Card 1995 一致)

# 3) 让 Agent 接管
# 把仓库目录给 Claude Code / Codex / Cursor，提示词：
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

可用作对比的 IV 路径（已 smoke-tested）：替换为 `IV2SLS` with `nearc4` →
- First-stage F = 15.75（强工具）
- IV educ 系数 = 0.1249（Card 1995 报告 ~13%，一致）
- spec_stability = 0（IV > OLS multiverse band — 这恰是 Card 著名发现，Agent 应该报告而非掩盖）

---

## 关键设计决策

### 1. 为什么 baseline 是 OLS 而不是 IV

OLS baseline 是研究者通常先看的；它建立 multiverse 的"地面"。Agent 在迭代中**应当**主动尝试 IV——这就是 identification 维度奖励的方向。把 IV 设为 baseline 会让 OLS 永远输（因为 IV F 默认 NA），这不公平。

### 2. 为什么删除"educ 显著为正"作为奖励

详见 program.md 中 Checkpoint 1 的说明。要点：
- **奖励"显著为正" = 把 specification mining 写进 reward function**
- Card 1995 的核心贡献恰恰是发现 IV > OLS（即 OLS 对 educ 的估计被 ability bias *向下*而非向上偏)
- 让数据说话，不让奖励函数说话

### 3. 为什么 `results.tsv` 入 git

Karpathy 原版就是入 git 的。**实验历史是不可重建的资产**——同样的代码下次跑可能因为 thermal noise / 依赖更新而不同。version-controlling 实验日志是复现性的第一公理（AEA Data Editor 的硬要求）。

### 4. 为什么 multiverse 在 `prepare.py` 内固定

如果让 Agent 自己定义 multiverse，它会通过收缩 multiverse 的范围来让自己的 spec 永远"稳定"。把 multiverse 定义在只读的 `prepare.py` 里 = Agent 不能 game。

---

## 文献锚定

- **Mincer (1974)** — *Schooling, Experience, and Earnings*。原始理论。
- **Card (1995, 1999, 2001)** — Card Handbook chapter；NLSYM with `nearc4` IV。返回率 ≈ 6–15% 的来源。
- **Heckman, Lochner & Todd (2006, Handbook)** — 现代返回率估计的方法论评述；MTE 框架。
- **Angrist & Pischke (2010)** — *The Credibility Revolution*；解释为何 identification 优于 fit。
- **Simonsohn, Simmons & Nelson (2020, Nat. Hum. Behav.)** — Specification curve analysis；本工作流多元宇宙的方法学源头。
- **Romano & Wolf (2005, Econometrica)** — Step-down family-wise p-value control。
- **Wooldridge (2019, ch. 6.2)** — 多项式 centering 与 VIF 教学。

---

## 相关仓库 & 实现状态

本仓库直接实现的范式只有一个：

| 仓库 | 实现状态 |
|------|----------|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | **已实现** — program.md 指令文件 + prepare.py（只读基础设施）+ analysis.py（Agent 可编辑文件）+ git keep/discard 循环 |

以下仓库的架构在**前期调研**阶段被研究过，但其核心逻辑**未在本仓库实现**：

| 仓库 | 提供了什么 | 为什么暂未实现 |
|------|-----------|---------------|
| [brycewang-stanford/Awesome-Agent-Skills](https://github.com/brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research) | 实证研究全流程 Skills（DID/IV/RDD 等 8 步闭环） | 本仓库聚焦单一规格搜索，不需要全流程 Skills |
| [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | 文献综述→实验→论文 三阶段多 Agent 管道 | 本仓库仅做实验迭代，不含文献综述和论文写作 |
| [sabrinaxfeng/marionette](https://github.com/sabrinaxfeng/marionette) | Tracker 文档作为多 Agent（Claude/Codex/Worker）共享世界模型 | 本仓库是单 Agent 循环，未做多 Agent 编排 |
| [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | Template-driven idea generation + Semantic Scholar novelty check | 本仓库的 Agent 通过修改 analysis.py 直接提出假说，未使用外部模板或文献 novelty check |
| [wanshuiyin/ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | 双模型对抗审阅（Claude 执行 + Codex/GPT 审稿） | 本仓库是单 Agent 自评，无跨模型审阅 |

---

## License

MIT
