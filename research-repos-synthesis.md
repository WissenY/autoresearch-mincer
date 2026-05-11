# Auto-Research 开源仓库综合调研（管理科学 / MIS / 经济学方向）

> **背景**：为 PS9 — Building an Autonomous Research Workflow Powered by LLM Agents（DOTE 6635, Spring 2026）作业准备。本作业要求仿照 Andrej Karpathy 的 `autoresearch` 范式，为一个小型研究项目设计 `program.md`，让 LLM Agent 自主迭代实验。本文档汇总所有前期调研，覆盖：
> 1. 与作业范式相关的开源仓库（单 Agent 代码迭代型 + 多 Agent 编排型）
> 2. 各仓库的运行逻辑深度解析
> 3. 与作业要求的适用性判断
> 4. 三个候选选题方向
> 5. 深度推理工具 / MCP 服务器推荐

---

## 一、仓库总览矩阵

### 1.1 单 Agent / 代码迭代型（与 autoresearch 范式直接相关）

| 仓库 | 星级 | 适合方向 | 语言 | 学科领域 |
| --- | --- | --- | --- | --- |
| karpathy/autoresearch | — | 原始范式 | Python | 通用（NN 训练） |
| Awesome Agent Skills for Empirical Research | 779 | 实证分析 | Python / R / Stata | 经济 / 管理 / 所有社科 |
| QRAFTI (Quant Agents) | 6 | 实证分析 | Python | 量化金融 |
| Agent Laboratory | 5.6k | 实证 + 建模 | Python | 通用 |
| AI-Scientist v1 / v2 | ~8k | 理论建模 | Python | 通用 |
| ARIS (Auto-claude-code-research-in-sleep) | 8.5k | 实证 + 建模 | Python / MD | 通用 |
| gpt-researcher | 26.9k | 文献综述 | Python | 通用 |
| Awesome Autoresearch | 1.8k | 生态索引 | — | 通用 |

### 1.2 多 Agent 编排型（Web Deep Research 主导）

| 仓库 | 星级 | 编排框架 | Agent 数量 | 独特亮点 |
| --- | --- | --- | --- | --- |
| LangChain Open Deep Research | 11.3k | LangGraph StateGraph | 4 LLM 角色 | Deep Research Bench #6；遗留两种备选编排 |
| Alibaba Tongyi DeepResearch | 18.8k | ReAct + IterResearch Heavy | 模型内生 | 30B-A3B 模型内生 Agent 能力 |
| tarun7r/deep-research-agent | 161 | LangGraph + LangChain Agent | 4 Agent | Circuit Breaker + 可信度评分 |
| Marionette | 4 | LLM 状态机 + 文件队列 | 3 层（Claude / Codex / mini） | Tracker 文档作为控制面 |
| GajananDhangude/Autonomous-Research-Assistant | ~10 | LangGraph + RAG | 4 Agent | Verify Agent 事实核查 |
| Research.AI (Multi-Agent) | — | LangGraph DAG | 6 Agent | 企业级 LLMOps（Redis + ChromaDB） |

---

## 二、单 Agent / 代码迭代型仓库深度解析

### 2.1 karpathy/autoresearch — 原始范式

**核心前提**：人类不再是"做研究的人"，而是"编写研究流程的人"。你写 `program.md`，AI 替你跑实验。

**运行逻辑链**：

```
人类写 program.md (指令)
  → AI 读 → AI 改 train.py
  → git commit → uv run train.py (5 分钟固定预算)
  → 读取 val_bpb → 对比上一轮
  → 降低则保留 (git keep) / 不变或升高则回退 (git reset)
  → 记录到 results.tsv
  → 提出下一个实验假说
  → 循环……
```

**三个核心设计**：

| 设计元素 | 逻辑含义 |
| --- | --- |
| `prepare.py` 只读 | 评估基准不可被 Agent 篡改——数据加载、分词器、`evaluate_bpb()` 是"地面真值" |
| `train.py` 唯一可编辑 | Agent 的搜索空间是模型架构、超参数、优化器——代码即实验假说 |
| 固定 5 分钟预算 | 确保公平比较：所有实验同等时间，Agent 必须找"在你的 GPU 上 5 分钟内最优的配置"，不依赖人类调参经验 |

**Agent 决策逻辑**：`val_bpb` 降低 → advance（git 保留 commit），升高或持平 → discard（`git reset --hard` 回退）。本质是一个爬山算法 + 局部搜索。

---

### 2.2 Awesome Agent Skills for Empirical Research（Stanford REAP + CoPaper.AI）

**地址**：<https://github.com/brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research>

**核心理念**：把资深经济学研究者数十年方法论经验编码成结构化的 AI Skill，Agent 按 Skill 一步步执行就能产出完整的实证论文。

- **学科覆盖**：经济学、政治学、社会学、心理学、公共卫生、教育学、管理学、金融学
- **核心内容**：119 个 GitHub 仓库、23,000+ AI Agent Skills，按实证全流程组织（选题 → 文献 → 数据清洗 → 因果推断 → 写作 → 审稿回复）
- **自研引擎 StatsPAI**：900+ 函数，一行 `import statspai as sp` 跑完 DID/IV/RDD/SCM/DML/因果森林/TMLE 全流程
- **三种语言全套技能**：Python（pandas/statsmodels/pyfixest/econml）、Stata（reghdfe/csdid/sdid/psmatch2）、R（tidyverse/fixest/grf/DoubleML/Quarto）
- **亮点**：自研产品 CoPaper.AI 已实现"20 分钟完成一篇主流期刊级别实证论文"

**运行逻辑链（以 Full Empirical Analysis Skill 为例）**：

```
用户输入: "帮我做 DID 分析"
   ↓
[阶段 1：数据清洗] 缺失数据(MCAR/MAR/MNAR) + 异常值(IQR/z-score/Mahalanobis) + 面板结构校验
   ↓
[阶段 2：变量构造] log/IHS/Box-Cox + 缩尾(winsor2) + 标准化 + 滞后/差分/交互项 + DID 时间变量
   ↓
[阶段 3：描述统计 Table 1] 分层统计 + SMD + t 检验 + 相关热图 + DID 平行趋势预检查
   ↓
[阶段 4：诊断检验 12 类] 正态性 / 异方差 / 自相关 / 多重共线 / 平稳 / Hausman / RESET
   ↓
[阶段 5：基准建模 12 类估计器] OLS / FE-RE / IV-2SLS-LIML-GMM / DID(Callaway-Sant'Anna, Sun-Abraham, Bacon, 连续DID) / RDD / PSM / SCM / DML / 因果森林 / Heckman
   ↓
[阶段 6：稳健性电池] M1-M6 规范阶梯 + Wild cluster bootstrap + 安慰剂 + Oster δ* + Bacon 分解
   ↓
[阶段 7：进一步分析] 异质性 + 机制(Baron-Kenny / outcome ladder / 调节) + 剂量反应 + 溢出
   ↓
[阶段 8：发表级输出] esttab/outreg2/asdoc → .tex/.rtf/.docx; coefplot/binscatter/event-study → .pdf
   ↓
输出：可复现、审稿人级别的实证论文
```

**StatsPAI 的独特逻辑**：不是让 Agent 逐行写代码，而是提供 **Agent-Native DSL**——`sp.causal(y ~ x, data, method='did')` 一句话跑完。Agent 不需要知道底层用什么包，但每一步有诊断输出，可审计。

**渐进披露架构**：`SKILL.md` 主干仅 ~600 行（最常用写法），细化的 3000+ 行变体下沉到 `references/` 目录，Agent 用时才加载——主干轻、细节厚，防止上下文溢出。

**三种语言对位的逻辑**：
- **StatsPAI（Python DSL）**：信任自动化，追求效率
- **Full Skill（Python 显式）**：逐行审计，教学场景
- **Full Skill（Stata）**：审稿人 / 导师只要 `.do` 复现包
- **Full Skill（R）**：tidyverse + Quarto，复现报告一键渲染

---

### 2.3 QRAFTI — Quant Agents

**地址**：<https://github.com/terence-lim/quant-agents>（论文 arXiv 2604.18500）

**领域**：量化金融实证研究。多 Agent 框架，模拟量化研究团队（因子研究员 + 报告撰写员 + 代码执行员），基于 MCP 协议的工具化架构。

**能力**：复刻 Fama-French HML、Jegadeesh-Titman 动量因子；自主提出并测试新因子（如基于 Buffett 投资哲学构建新因子）。**数据源**：CRSP、Compustat。

**运行逻辑链**：

```
用户: "请复刻 Fama-French HML 因子"
   ↓
[Phase 1: Plan Agent] 拆解为子步骤
   1. 从 Compustat Annual 获取 book equity
   2. 从 CRSP Monthly 获取 market cap
   3. 按 NYSE breakpoints 排序分组
   4. 构造 value-weighted portfolio
   5. 计算 HML = (SV+BV)/2 − (SG+BG)/2
   Agent 反思（reflexion）：每步是否可用现有 MCP 工具？
   ↓
[Phase 2: Execute] 通过 MCP 工具服务器调度
   - factor_server.py: lag/winsorize/sort/portfolio weight
   - coding_server.py: 沙盒执行自定义 Python
   - data_utils.py: 封装 CRSP / Compustat 数据访问
   ↓
[Phase 3: Report Agent] 标准化模板（散点图、相关性、因子表现）→ LaTeX/PDF
```

**独特架构**：通过 MCP（Model Context Protocol）把数据 / 因子 / 报告操作都暴露为工具调用。Agent 不是"写代码"，而是"调用工具链"——能组合复杂金融逻辑而不写错代码。

**Reflexion Prompt 技术**：每次查询三阶段：
1. **计划**："想想整体步骤顺序"
2. **反思自评**："每步是否可实现？有没有更高效方式？需向用户补充定义？"
3. **修正后计划**："这是修正方案，先不执行"

---

### 2.4 Agent Laboratory

**地址**：<https://github.com/SamuelSchmidgall/AgentLaboratory>（论文 arXiv 2501.04227）

**通用性最强**，三阶段研究管道：

```
人类输入研究想法（task_notes_LLM）
   ↓
[Phase 1: Literature Review Agent] arXiv/Semantic Scholar 搜索 → 文献综述草稿 → 检查新颖性
   ↓
[Phase 2: Experimentation Agent]
   - Plan Agent: 基于文献制定方案
   - Code Agent: 生成/修改实验代码
   - Execute Agent: 运行 → 收集结果 → 对比 → keep/discard → 迭代
   ↓
[Phase 3: Report Writing Agent] LaTeX 撰写 → 自动编译 PDF → AgentRxiv 投稿
```

**两种模式**：
- **Copilot**：每个关键节点等待人类审核
- **Autonomous**：完全自主，类似 autoresearch 的"永不停歇"

**AgentRxiv**：跨 Agent 知识共享平台。不同 Agent Laboratory 实例可上传论文到共享预印本服务器，互相检索、互相建立在彼此成果上——研究是 Agent 群体的累积进步。

---

### 2.5 AI-Scientist / AI-Scientist-v2（Sakana AI）

**地址**：<https://github.com/SakanaAI/AI-Scientist>（v1）+ <https://github.com/SakanaAI/AI-Scientist-v2>

**Sakana AI 出品的首个全方位自动科学发现系统**。

**运行逻辑链**：

```
启动: python launch_scientist.py --model "gpt-4o" --experiment nanoGPT --num-ideas 2
   ↓
[Phase 1: Idea Generation] 读 seed_ideas.json → Semantic Scholar 检查新颖性 → LLM 生成假说
    例: "用 Q-learning 动态调整 Transformer 每层学习率会怎样?"
   ↓
[Phase 2: Experiment Execution] 读 experiment.py 模板 → LLM 修改 → 运行 → plot.py 出图
   ↓
[Phase 3: Paper Writing] LLM 填 template.tex → 插入图表 → Semantic Scholar 自动引用 → PDF
   ↓
[Phase 4: Peer Review (可选)] LLM 审稿打分(1-10) → Accept/Reject + 弱点 → 送回修改循环
   ↓
输出：完整 LaTeX 论文（如 "DualScale Diffusion"、"Grokking Accelerated"）
```

**Template 系统是关键架构**：每个研究领域是一个 Template（nanoGPT / 2D Diffusion / Grokking），包含 `experiment.py` + `plot.py` + `prompt.json` + `seed_ideas.json` + `latex/template.tex`。Agent 的工作是"修改 `experiment.py` + 填写 `template.tex`"——**与 autoresearch 的 `train.py` 模式完全一致**。

**v2 改进**：用 **Agentic Tree Search** 代替模板——Agent 在更大空间内自主决定研究方向，跨界泛化能力更强。**适配场景**：博弈论模型求解、动态规划算法比较、均衡解方法对比。

**社区已有模板**：传染病建模、图像分类、量子化学、地震预测等。

---

### 2.6 ARIS — Auto-claude-code-research-in-sleep

**地址**：<https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep>

**核心理念**：全部 Markdown 文件，零依赖、零锁定。任何 Agent（Claude Code / Codex / Cursor / OpenClaw）都能读懂 `SKILL.md` 并执行研究。

**核心工作流管道**：

```
用户: /research-pipeline "factorized gap in discrete diffusion LMs"
   ↓
[Workflow 0: /research-lit] Agent 搜文献(arXiv/Semantic Scholar/Gemini/OpenAlex) → 存入 Research Wiki
   ↓
[Workflow 1: /idea-discovery] 生成 3-5 个想法 → 交叉模型审阅打分 → 选最佳
   ↓
[Workflow 2: /experiment-design + /code-implementation] 设计方案 → 代码 → GPU/SLURM 运行
   ↓
[Workflow 3: /auto-paper-improvement-loop] 写初稿 → 交叉模型审阅 → 修订 → 收敛
   可选：/paper-claim-audit, /citation-audit, /kill-argument（对抗式攻击找弱点）
   ↓
输出：经多轮交叉审阅优化的论文 + 实验数据
```

**双模型交叉审阅（对抗式博弈）**：

```
Claude Code (执行者) → 速度优先, 快速执行
   ↓
代码 / 论文 / 想法 → 送给外部模型审阅
   ↓
Codex / GPT-5.4 (审阅者) → 严谨质疑, 深度批判
   ↓
找出弱点 → 返回 Claude Code 修正
   ↓
重复迭代……
```

**为什么双模型而非单模型自评**：同模型自评会产生"盲点同质化"——它看不到自己不擅长发现的问题。双模型对抗博弈（adversarial bandit）比单模型随机博弈（stochastic bandit）更难"作弊"，收敛更高效。**两玩家 Nash 均衡的收敛速度远快于 n 玩家**。

**Research Wiki（持久研究记忆）**：论文、想法、实验、断言以结构化知识图谱存储；Agent 查阅、对比、交叉引用；下一个研究方向基于累积知识自动发现。

---

### 2.7 GPT Researcher

**地址**：<https://github.com/assafelovic/gpt-researcher>

**架构核心 — Plan-and-Solve + RAG**。不是让 LLM 一次生成整份报告（容易幻觉），而是先 Plan 生成研究问题树，再用 RAG 收集真实网页证据，最后 Solve（汇总）。**每个 claim 都已有来源锚定**。

**运行逻辑链**：

```
用户: "为什么 Nvidia 股价一直在涨?"
   ↓
[Step 1: Planner Agent] 拆解为子问题：财报 / AI 芯片需求 / 竞争对手 / 分析师评级 / 宏观因素
   ↓
[Step 2: Execution Agents (并行)] 每个子问题分配一个执行 Agent
   - Tavily 网页爬虫搜索 → 提取关键信息 + 来源 URL
   - 并行（不是串行！速度提升 2-4x）
   ↓
[Step 3: Summarizer Agent] 摘要 + 多源交叉验证 + 过滤矛盾低质信息
   ↓
[Step 4: Publisher Agent] 整合结构化报告 → 目录 + 20+ 引用 → PDF/Word/Markdown
   可选: 自动生成 AI 插图 (Google Gemini Nano Banana)
   ↓
输出: 2000+ 字深度研究报告, 含引用 + 图表
```

**Deep Research 模式（树状搜索）**：

```
根问题
├── 子问题 A
│   ├── 子子问题 A1 → 搜索结果
│   └── 子子问题 A2 → 搜索结果
├── 子问题 B
│   ├── 子子问题 B1 → 搜索结果
│   └── 子子问题 B2 → 再分一层
配置: depth=3, breadth=4, 每层并行；约 5 分钟 / $0.4 / 次
```

**MCP 集成**：可连接 GitHub、数据库、私有文档作为数据源，超越纯网络搜索。

---

### 2.8 Awesome Autoresearch（生态索引）

**地址**：<https://github.com/alvinreal/awesome-autoresearch>

Autoresearch 生态全景索引，分类：通用衍生 / 研究 Agent 系统 / 平台移植 / 领域适配 / 评估基准。

**领域适配区**（值得借鉴）：
- **NanoResearch**：自主实验 → 代码生成 → SLURM 提交 → 结果分析 → 论文写作
- **OmegaWiki**：Wiki 中心化的全生命周期研究平台，支持社科研究
- **CORAL**：多 Agent 自主进化系统，适合开放式理论探索

---

## 三、多 Agent 编排型仓库深度解析

### 3.1 LangChain Open Deep Research

**地址**：<https://github.com/langchain-ai/open_deep_research>  · **编排框架**：LangGraph StateGraph

**Agent 组成**：

```
Research Agent (主循环) → 决策"接下来搜什么"
   ↕
Summarization Agent → 压缩搜索结果（gpt-4.1-mini, 快+便宜）
   ↕
Compression Agent → 压缩上下文避免溢出
   ↕
Final Report Agent → 撰写最终报告（最强模型）
```

**编排逻辑**：
- 非串行管道，而是 **LLM 驱动的自主决策循环**：Agent 每轮自主决定"搜什么、读什么、够了吗"
- 四个 LLM 角色分离（成本/能力错配）
- LangGraph 状态持久化 → 崩溃恢复 + 人机交互 checkpoint
- 遗留两种替代编排：
  - `legacy/graph.py`（Workflow 模式）：Plan-and-Execute，先规划 → 人类审批 → 逐节生成 → 反思
  - `legacy/multi_agent.py`（多 Agent 模式）：Supervisor-Researcher 架构，多 Researcher 并行
- **Deep Research Bench 排名 #6**

---

### 3.2 Alibaba Tongyi DeepResearch

**地址**：<https://github.com/Alibaba-NLP/DeepResearch>  · **编排框架**：ReAct + IterResearch Heavy

**核心创新 — 不是外挂编排，而是模型内生 Agent 能力**：

```
ReAct 模式（模型核心能力）：
  思考 → 行动(搜索/读网页/运算) → 观察 → 思考 → ... → 最终答案

IterResearch Heavy 模式（测试时扩展）：
  多路径并行搜索 → 交叉验证 → 迭代深化 → 综合答案
```

**关键技术**：
- 通过预训练 + SFT + RL 三阶段训练，让模型学会"何时搜索、如何搜索、如何提取信息"
- 全自动合成数据管道（预训练 → SFT → RL）
- **端到端 RL（GRPO）**：token 级策略梯度，leave-one-out advantage
- 30B 总参数，仅 3.3B 激活/token，128K 上下文
- 在 Humanity's Last Exam 和 BrowseComp 上 SOTA
- 发布 18 篇论文的 Deep Research Agent 家族（WebWalker、WebDancer、WebSailor 等）

---

### 3.3 tarun7r/deep-research-agent

**地址**：<https://github.com/tarun7r/deep-research-agent>  · **编排框架**：LangGraph + LangChain Agent

**Agent 组成（4 个专业 Agent）**：

```
ResearchPlanner → ResearchSearcher → ResearchSynthesizer → ReportWriter
   ↓                  (自主 Agent!)        ↓                    ↓
3-5 个 SMART 目标   动态决定搜索策略     综合分析            学术格式引用
报告大纲            create_agent()       优先级排序          质量验证 + 重试
                    多轮搜索 + 抓网页    解决矛盾
```

**关键突破 — ResearchSearcher 是 LangChain 自主 Agent**：不是盲目"搜索→返回"，而是**动态决策**先搜什么、搜到什么程度、是否换关键词、是否深读某网页。内置**断路器（Circuit Breaker）**，5 次失败 → OPEN → 30 秒冷却 → 半开 → 成功则 CLOSE。

**生产级特性**：
- 可信度评分（0-100）：基于域名（`.edu` +30）、HTTPS（+5）、学术路径（+10）、可疑 TLD（−20）
- SQLite checkpoint 崩溃恢复
- 7 天 TTL 缓存 + MD5 哈希去重

---

### 3.4 Marionette（高度原创的编排设计）

**地址**：<https://github.com/sabrinaxfeng/marionette>  · **编排框架**：LLM 驱动有限状态机 + 文件后台任务队列

**核心创新 — Tracker 文档作为控制面**：

```
Tracker 文档 (IMPROVEMENTS.md) = 共享世界模型
   ↕ (所有 Agent 被同一文档 ground)
   ├── Claude (Director) → 读 tracker → 选工作 → 写 task frame
   ├── Codex (Analyst) → 读 task frame → 分解 → 派工 → 自迭代 → 报结果
   └── Codex-mini (Workers) → 执行代码/测试/基准
```

**五个状态的状态机**：

```
idle → planning → executing → reviewing → stopped
         ↑                        │
         └─── next_task ──────(静默链, 不动用 Claude)
                自迭代 3-4 轮后才通知 Claude
```

**编排逻辑**：
- **Analyst 自迭代**：大 task frame 自动分解为 3-4 子任务，无声执行，不通知 Director
- **DAG + 任务组**：`depends_on` 控制顺序；`conflict_keys` 串行化冲突分支；`task_group_id` 分组
- 文件队列（pending/running/completed/failed）— 无数据库，纯文件系统
- 临时 Reviewer 接管：第二个 Reviewer 可暂时接管队列管理
- **人机边界**：人类拥有 Tracker 的最终编辑权 — "You own the tracker"

**经验教训**：
> "Task frames should be large — 'Implement and validate the whole feature' not 'bump parameter from 3 to 5'."

---

### 3.5 GajananDhangude/Autonomous-Research-Assistant

**地址**：<https://github.com/GajananDhangude/Autonomous-Research-Assistant>

```
Plan Agent → Retrieve Agent → Verify Agent → Synthesize Agent
  │              │                │               │
生成研究问题   多源搜索 / 向量检索  来源验证 +     整合为结构化引用报告
                                   可信度评估
  └─→ Vector Memory (长期记忆, 跨 session 持久) ←─┘
```

**特色**：线性管道 + 长期向量记忆增强。**Verify Agent** 在资料检索和综合之间加入"事实核查"环节。

---

### 3.6 Research.AI（Multi-Agent Autonomous Research Assistant）

**地址**：<https://github.com/bittush8789/Multi-Agent-Autonomous-Research-Assistant>  · **编排**：LangGraph StateGraph 企业级

```
User → FastAPI → LangGraph Orchestrator
       ├── Search Agent (Tavily + DuckDuckGo)
       ├── PDF RAG Agent (ChromaDB 向量语义搜索)
       ├── Summarizer Agent (Groq Llama 3.3 70B)
       ├── Citation Agent (引用格式)
       └── Report Agent (Markdown)
       memory: Redis (短期) + ChromaDB (长期向量)
```

**特色**：严格 DAG → 无环可终止；ChromaDB 保存 PDF 语义索引；Redis 保存会话；Glassmorphism 前端展示实时"智能日志"。

---

## 四、七大单 Agent 系统范式横向对比

| 系统 | 范式类型 | 循环驱动 | Agent 类型 | 输出 |
| --- | --- | --- | --- | --- |
| autoresearch | 单 Agent 代码优化 | 改代码→训练→评估→keep/discard | 1 个 Agent | val_bpb 对比 |
| Awesome Agent Skills | Skill 驱动执行管道 | 加载 Skill→按步骤→产出论文 | 1 个 Agent | 完整实证论文 |
| QRAFTI | MCP 工具链编排 | 计划→反思→工具调用→报告 | Plan/Execute/Report | 量化研究报告 |
| Agent Laboratory | 三阶段研究管道 | 文献→实验→论文→AgentRxiv | Lit/Code/Report | 论文 + 实验 |
| AI-Scientist | 模板驱动科学发现 | 想法→改模板→跑→写→审稿 | 模块化 Agent | LaTeX 论文 + 审稿意见 |
| ARIS | 双模型对抗优化 | 执行→审阅→修正→再执行 | Claude + Codex | 经审阅优化的论文 |
| gpt-researcher | 规划-检索-聚合 | Plan 子问题→并行搜索→汇总 | Planner+Executor+Publisher | 深度研究报告 |

## 五、六大多 Agent 编排范式横向对比

| 维度 | LangChain ODR | Tongyi DR | tarun7r | Marionette | Research.AI |
| --- | --- | --- | --- | --- | --- |
| 编排模式 | LLM 自主决策循环 | 模型内生 Agent | Supervisor + 自主 Agent | LLM 状态机 + 文件队列 | DAG 管道 |
| Agent 数量 | 4 LLM 角色 | 1 模型(内置) | 4 Agent | 3 层 | 6 Agent |
| 并行度 | 搜索可并行 | IterResearch 多路径 | 搜索串行 | Analyst 内子任务并行 | DAG 自动并行 |
| 人机边界 | Checkpoint 恢复 | API 调用 | 无交互 | Tracker 由人拥有 | Web UI |
| 持久化 | LangSmith 追踪 | 无 | SQLite checkpoint | 文件队列 | Redis + ChromaDB |
| 成熟度 | 极高 (11k 星) | 极高 (18k 星) | 中等 | 新颖 | 基础 |
| 独特亮点 | 两种遗留备选编排 | 模型内生 Agent | Circuit Breaker | Tracker 状态机 | LLMOps 全套 |

---

## 六、与作业要求的适用性判断

### 6.1 作业核心要求

仿照 `karpathy/autoresearch`，构建 **"修改代码→运行实验→评估指标→保留/丢弃"** 的自主迭代循环。关键三要素：

| 要素 | 说明 |
| --- | --- |
| Agent 能改什么 | 代码 / 模型 / 方法（类似 `train.py`） |
| 评估什么 | 一个明确指标（类似 `val_bpb`） |
| 循环逻辑 | 改→跑→比→keep/discard→再改 |

### 6.2 不适用（Web 深度研究 Agent）

| 仓库 | 为什么不适配 |
| --- | --- |
| LangChain ODR | 搜网页→写报告，不修改代码、不跑实验 |
| Tongyi DeepResearch | Web 搜索 Agent，不涉及代码实验迭代 |
| tarun7r | 同上，纯信息检索 + 报告生成 |
| GPT Researcher | 同上 |
| Research.AI | Web 搜索 + PDF 分析 + 报告，无实验循环 |

> **这些仓库解决的是"给我搜资料写报告"，而非作业要求的"给你一个实验环境，自己迭代优化"。**

### 6.3 适用（可适配作业的代码实验循环）

| 仓库 | 适用方向 | 可借鉴点 |
| --- | --- | --- |
| **Marionette** ⭐ 强推 | 实证 / 建模 / ML | 完整 Tracker 文档 + 状态机；Claude=Director / Codex=Analyst；DAG 任务队列；与 autoresearch 模式最接近 |
| **Awesome Agent Skills** ⭐ 强推 | 实证（经济 / 管理） | 已有 Stata/Python/R 全流程 Skills，直接拿来设计 `program.md` |
| Agent Laboratory | 实证 + 建模 | 三阶段管道（文献→实验→论文）阶段划分 |
| AI-Scientist | 理论建模 | Template 系统可改造为博弈论 / 动态规划实验模板 |
| QRAFTI | 实证（金融） | MCP 工具链 + Reflexion 自评循环 |

---

## 七、三种选题方向的具体方案

### 方案 A：实证分析 — "哪种回归规格最能解释工资差异"（**推荐**）

**数据**：Wooldridge `wage1.dta` 或 Kaggle 公开工资数据（几百行，秒级跑完）

**`program.md` 指令**：

```
1. 读取 wage1.dta
2. 跑基准回归: log(wage) ~ educ + exper + tenure + female
3. 每次迭代尝试一种改进：
   - 加入二次项 exper², tenure²
   - 加入交互项 female × educ
   - 换 heteroskedasticity-robust SE
   - 换 WLS 估计
   - 加入婚姻 / 行业虚拟变量
4. 评估指标: AIC, BIC, Adjusted R²
5. Keep: 任一指标改善且无退化
6. Discard: 加变量但 AIC 不降或 VIF > 10
```

| 优点 | 说明 |
| --- | --- |
| 课程最契合 | "AI for Business Research"，实证分析是最自然的延伸 |
| 工具现成 | Awesome Agent Skills 已有 Stata/Python/R 完整 Skills |
| 评估清晰 | AIC/BIC/Adj-R² 是公认标准，Agent 容易判断 |
| 可深可浅 | 3 轮迭代就能交作业，想做深入有足够空间 |
| 论文感强 | 最终产出像一篇小型实证论文 |

---

### 方案 B：理论建模 — "Cournot 双寡头均衡比较"

**代码**：用 Python/SciPy 写 Cournot 博弈求解器

**`program.md` 指令**：

```
1. 写 Cournot duopoly 求解器:
   - 反需求 P(Q) = a − bQ, a=100, b=1
   - 边际成本 c1=10, c2=10 (初始对称)
2. 每次迭代尝试一种变化：
   - c1 ≠ c2 (非对称成本) → 比较利润分布
   - 加入固定成本 → 检查进入/退出决策
   - Cournot → Stackelberg → 比较先动者优势
   - 增加厂商数 n=3,4,5,... → 收敛到完全竞争
   - 引入不确定性 (随机需求 a)
3. 评估指标: 总福利 (CS+PS), HHI 集中度
4. Keep: 产出有意义的理论洞察
5. Discard: 代码无法收敛或结果平凡
```

**优势**：无外部数据依赖，数学逻辑清晰，多 Agent 审阅可互相验证解的正确性。

---

### 方案 C：ML 方法 — "Iris 分类器：哪种特征组合最优"

**数据**：sklearn 内置 iris（150 行）

**`program.md` 指令**：

```
1. 跑基准: LogisticRegression + 4 个原始特征
2. 每次迭代尝试：
   - 多项式特征交互项
   - 标准化 vs MinMax
   - 不同分类器 (SVM, RandomForest, KNN)
   - 不同正则化强度 C
   - PCA 降维到 2 维
3. 评估指标: 5-fold CV accuracy
4. Keep: accuracy 提升
5. Discard: accuracy 不升或模型过于复杂
```

---

## 八、推荐组合方案（按方向）

### 选实证分析方向

```
参考 Marionette 的编排架构
+ 使用 Awesome Agent Skills 的 Stata/Python/R Skills 作为 Agent 的"知识基线"
+ 你的 program.md 告诉 Agent:
    "修改回归规格 / 因果推断方法 → 跑回归 → 比 AIC/BIC/显著性 → keep or discard"
```

### 选理论建模方向

```
参考 AI-Scientist 的 Template 系统
+ Marionette 的 Tracker 文档作为共享记忆
+ 你的 program.md 告诉 Agent:
    "修改博弈论模型的假设/参数 → 求解均衡 → 比均衡性质 → keep or discard"
```

### 选 ML 方法方向

```
直接基于 autoresearch 的 program.md 范式
+ Marionette 的多 Agent 状态机扩展
+ 你的 program.md 告诉 Agent:
    "修改模型架构/超参数 → 跑 5 分钟训练 → 比 val_bpb → keep or discard"
```

> **一句话**：Web 深度研究 Agent 可作为文献综述阶段的辅助工具引用借鉴，但作业的核心实验循环必须基于 autoresearch / Agent Laboratory / Marionette 这类"Agent 能改代码并跑实验"的范式来设计。

---

## 九、深度推理工具与 MCP 服务器

### 9.1 可直接使用的 MCP 服务器

| MCP Server | Stars | 覆盖源 |
| --- | --- | --- |
| [arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server) | 2.7k | arXiv |
| [mcp-simple-pubmed](https://github.com/andybrandt/mcp-simple-pubmed) | 164 | PubMed |
| [paper-search-mcp-nodejs](https://github.com/Dianel555/paper-search-mcp-nodejs) | 147 | arXiv + PubMed + bioRxiv + Google Scholar |
| [ZotLink](https://github.com/TonybotNi/ZotLink) | 135 | Zotero 集成 + arXiv/bioRxiv/CVF |
| [gptr-mcp](https://github.com/assafelovic/gptr-mcp) | 344 | GPT Researcher 深度搜索 MCP |

### 9.2 专用深度推理框架

| 工具 | Stars | 深度 | 强项 |
| --- | --- | --- | --- |
| [PaperQA2](https://github.com/Future-House/paper-qa) | 8.4k | ⭐⭐⭐⭐⭐ | 证据链级引用追踪，metadata-aware RAG，LLM 重排序，科学 QA 超越人类。最佳用于 (a) 深度文献推理 + (d) 科研代码关联文献 |
| [STORM](https://github.com/stanford-oval/storm) | 28.2k | ⭐⭐⭐⭐⭐ | 多视角提问 + 模拟专家对话 + 思维导图。最佳用于 (b) 多轮讨论 + (c) 论文写作生成 |
| [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | 26.9k | ⭐⭐⭐⭐ | 树状递归探索，planner+execution 双代理，MCP 原生 |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 50.7k | ⭐⭐⭐ | 研究者→分析师→写作者角色扮演，快速原型 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 31.3k | ⭐⭐⭐⭐ | 状态持久化 DAG 工作流 + 人机回环，精密控制 |
| [DSPy](https://github.com/stanfordnlp/dspy) | 34.2k | ⭐⭐⭐⭐⭐ | 编程式优化 LLM pipeline（非 prompt），自改进检索与推理链 |

### 9.3 推荐组合（针对作业的文献综述阶段）

```
MCP 检索层:  arxiv-mcp-server + paper-search-mcp-nodejs + ZotLink
              ↓
证据推理层:  PaperQA2 (citation-grounded 证据链)
              ↓
多轮讨论层:  STORM / Co-STORM (多视角专家对话 + 思维导图综合)
              ↓
编排层(可选): LangGraph (持久化工作流) 或 DSPy (自优化 pipeline)
```

- **PaperQA2** 负责"两到三层推理 + 细微之处深度挖掘"——它做 RCS（contextual summarization + LLM re-ranking），每次检索都带引用溯源
- **STORM** 负责"议题多轮讨论 + 分任务探索"——模拟多专家视角质疑与综合
- 两者互补，配合学术 MCP 服务器接入当前环境即可
- **SciSpace、Elicit、Consensus** 等 Web 工具只做表层摘要，不适合深层推理

---

## 十、最终行动建议

1. **选题先定**：推荐 **方案 A（实证分析 — 工资回归）**，与课程契合度最高、工具最完备、评估指标最客观
2. **范式锚定**：以 `karpathy/autoresearch` 为范式蓝本，必要时借鉴 **Marionette 的 Tracker 文档** 思想做多 Agent 扩展
3. **Skill 复用**：直接引用 **Awesome Agent Skills** 中的 Stata/Python/R 实证 Skill 作为 Agent 的知识基线
4. **文献综述辅助**：用 **PaperQA2 + STORM** 做相关论文的深度推理与多视角综合
5. **`program.md` 起草**：明确边界（哪些只读、哪些可改）、迭代循环（改→跑→比→keep/discard）、评估指标（AIC/BIC/Adj-R²）、停止-检查点（至少 3 个人工审核节点）
