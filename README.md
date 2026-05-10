# Autoresearch-Mincer: LLM Agent 自主实证研究工作流

> **课程**: DOTE 6635 AI for Business Research — Problem Set 9  
> **核心思想**: 仿照 Karpathy 的 [autoresearch](https://github.com/karpathy/autoresearch)，将人类角色从"做研究"转变为"编写研究流程"，让 AI Agent 自主进行 Mincer 工资方程的规格搜索实验。

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目概述

本仓库实现了一个**基于 LLM Agent 的自主实证研究循环**。Agent 通过修改回归规格（变量选择、函数形式、估计器）、运行诊断、评估多维评分卡，自动迭代寻找最优的工资方程规格——人类只需编写 `program.md` 指令文件，无需直接操作代码。

### 与 Karpathy Autoresearch 的范式对比

| | Autoresearch (ML) | Autoresearch-Mincer (实证经济学) |
|---|---|---|
| **研究领域** | 神经网络训练 | 劳动经济学工资方程 |
| **可修改文件** | `train.py` | `analysis.py` |
| **评估指标** | 单一 val_bpb | **5维评分卡**（核心假说+拟合+诊断+稳健性+简洁性） |
| **变化驱动** | 纯指标数字 | **方法论Checklist + 诊断反馈** |
| **时间预算** | 固定5分钟/实验 | 1个规格变化/迭代（秒级运行） |

---

## 项目架构

```
autoresearch-mincer/
├── program.md          # 🤖 Agent 指令文件（人类编写，Agent 执行）
│                       #    - 实验循环定义
│                       #    - 五维评分规则
│                       #    - 人机检查点
│                       #    - 简洁性标准
├── prepare.py          # 🔒 只读基础设施
│                       #    - 合成数据生成（已知 Mincer DGP）
│                       #    - evaluate_specification() 评估函数
│                       #    - BP / VIF / RESET 诊断检验
├── analysis.py         # ✏️ Agent 可修改的实验文件
│                       #    - 回归规格定义
│                       #    - 变量构造
│                       #    - 估计器选择
├── results.tsv         # 📊 实验结果日志（不提交git）
└── .gitignore          # 排除 logs/ .DS_Store __pycache__ *
```

---

## 快速开始

### 环境要求

- Python 3.12+
- numpy, pandas, statsmodels

```bash
# 1. 安装依赖
pip install numpy pandas statsmodels

# 2. 运行基线实验
python analysis.py

# 3. 查看输出结果（spec_score 及诊断详情）
```

### 让 Agent 自主运行

将本仓库目录交给 Claude Code / Codex / Cursor，然后提示：

```
Hi have a look at program.md and let's kick off a new experiment! 
let's do the setup first.
```

Agent 将自动：
1. 读取 `program.md` 了解研究规则
2. 读取 `prepare.py` 了解固定基础设施
3. 读取 `analysis.py` 了解当前基线规格
4. 跑基线实验建立 benchmark
5. 提出假说驱动的修改 → 运行 → 评估 → keep/discard → 循环

---

## 五维评分系统

传统 autoresearch 的 `val_bpb` 是单维度的——改代码、跑、"降低就是好"。实证研究的质量标准是多维度的：

| 维度 | 权重 | 评分规则 |
|------|:----:|----------|
| **核心假说** | 1 | educ 系数 > 0 且 p < 0.05 → 1分 |
| **模型拟合** | 1 | AIC 低于前一轮留存模型 → 1分 |
| **诊断通过** | 1 | BP检验(p≥0.05) + VIF<15 + RESET(p≥0.05) → 1分 |
| **稳健性** | 1 | educ 符号在嵌套规格中保持稳定 → 1分 |
| **简洁性** | 1 | 未引入冗余复杂度(n_params ≤ 合理值) → 1分 |

**Keep/Discard 规则**: score ≥ 3 且改进 → keep；否则 discard。相同分数下，更简洁的模型胜出。

---

## 关键设计决策

### 1. Agent 如何提出实验想法

不同于 autoresearch 完全依赖 LLM 内部知识的"零结构"设计，本工作流将**方法论知识显式编码**进 `program.md`：

- **理论驱动变化**：遗漏变量 → 加入行业/地区固定效应
- **诊断驱动变化**：BP 检验失败 → 切换到 HC3 稳健标准误
- **识别驱动变化**：怀疑内生性 → 考虑工具变量
- **稳健性驱动变化**：检验基准模型敏感度

Agent 不能随机尝试——每次修改必须有计量经济学理由。

### 2. 多维 vs 单维评估

实证研究的"最优"不是单调可排序的：一个模型 AIC 更低但变量不显著 vs 另一个 AIC 略高但核心假说被证实——哪个更好？五维评分卡让 Agent 在多目标间做权衡。

### 3. 人机边界设计

三个检查点确保人类对研究方向的最终控制：
- **基线后**：验证环境和基准规格合理
- **4/5分达成**：确认统计最优与经济意义不冲突
- **5轮无进展**：手动调整搜索方向

---

## 学习资源

本仓库的构建参考了以下 GitHub 自主研究生态：

| 仓库 | 借鉴点 |
|------|--------|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | 原始范式：program.md + 只读基础设施 + 可编辑实验文件 |
| [brycewang-stanford/Awesome-Agent-Skills](https://github.com/brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research) | 实证分析方法论 Skills 编码方式 |
| [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | 文献综述→实验→论文 三阶段管道 |
| [sabrinaxfeng/marionette](https://github.com/sabrinaxfeng/marionette) | Tracker 文档作为多 Agent 共享世界模型 |
| [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | 模板驱动科学发现的实验假说生成 |
| [wanshuiyin/ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | 双模型交叉审阅（对抗式博弈） |

---

## License

MIT
