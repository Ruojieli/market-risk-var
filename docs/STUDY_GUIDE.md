# 学习指南：面试前要能讲清楚的东西

这份指南配合代码看。每一节都标了对应的文件，建议你打开代码逐行对照，确保每一步都能自己讲出来。
文中数字来自 2026-10-09 的运行结果，重新下载数据后会变。

---

## 0. 这个项目和职位的对应关系

RBC 这个职位（Market Risk Governance & Reporting）的日常工作是：做市场风险报告、核查数据、写方法和流程文档、给管理层和监管准备材料。这个项目把这条流程完整走了一遍：

| 职位要求 | 项目里对应的部分 |
|---|---|
| data validation, quality checks, break analysis | `validation.py`：日历对齐、缺失值、陈旧价格、异常收益，全部记录成"问题清单" |
| VaR, sensitivities/Greeks | `var_models.py`、`greeks.py`、`portfolio.py` |
| 报告给管理层 | `report.py` 生成的每日风险报告 |
| 回测、监管框架 | `backtest.py`：Kupiec 检验、Basel 红黄绿灯 |
| Python, SQL, Excel | 全部用 Python（pandas、numpy、scipy） |

---

## 1. VaR 是什么（`var_models.py`）

**定义**：在给定置信水平（比如 99%）和持有期（比如 1 天）下，组合损失不会超过的金额。
"1 天 99% VaR = $22,859" 的意思是：正常情况下，100 个交易日里大约只有 1 天亏损会超过 $22,859。

**VaR 没有告诉你的**：超过 VaR 的那 1% 的日子会亏多少。这就是为什么还要看 ES。

### 三种算法

| 方法 | 怎么算 | 优点 | 缺点 |
|---|---|---|---|
| 历史模拟（Historical simulation） | 把过去 500 天每天的因子变动"重放"到今天的组合上，完全重估价值，取第 1% 分位数 | 不假设分布，自然包含肥尾和非线性 | 完全依赖历史窗口；极端日进出窗口时 VaR 会跳变（悬崖效应） |
| 参数法（Delta-normal） | 用线性敞口 × 协方差矩阵算组合标准差，VaR = 2.326 × σ | 快，能分解到每个风险因子（component VaR） | 假设正态，低估肥尾；忽略期权的凸性（gamma） |
| 蒙特卡洛（Monte Carlo） | 用 Cholesky 分解生成 2 万个相关的正态情景，逐个完全重估 | 能处理非线性产品 | 仍假设正态；计算量大；结果依赖模型设定 |

### 怎么解读你的结果

| 方法 | VaR | ES |
|---|---:|---:|
| 历史模拟 | $22,859 | $36,258 |
| 参数法 | $25,860 | $29,627 |
| 蒙特卡洛 | $24,896 | $28,456 |

- **历史模拟的 ES 比另外两个高很多**：真实收益有肥尾，最差的那几天比正态分布预测的更差。两个正态方法的 ES 低估了尾部。
- **蒙特卡洛和参数法的差别**：两者用同一个协方差矩阵，差别来自期权的非线性。参数法只用了 delta，蒙特卡洛完整重估了期权价值。
- **VIX 的 component VaR 是负的（-21%）**：组合持有看涨期权，是 long vega（波动率上升时赚钱）。而 VIX 通常在股市下跌时上升，所以 vega 敞口部分对冲了股票风险。这是一个很好的面试话题。

---

## 2. Expected Shortfall 和 FRTB

**ES（Expected Shortfall）**：在超过 VaR 的那些最差日子里，平均亏多少。

**为什么监管从 VaR 转向 ES**（FRTB 的核心变化之一）：
1. VaR 只看一个分位点，看不到尾部有多深。
2. VaR 不满足"次可加性"：两个组合合并后的 VaR 可能大于各自 VaR 之和，和分散化的直觉矛盾。ES 满足。

**为什么 FRTB 用 97.5% 的 ES 而不是 99%**：在正态分布下，97.5% ES ≈ 2.338σ，99% VaR ≈ 2.326σ，两者数值接近，所以资本水平大致可比，但 ES 更能反映肥尾。
你的结果里 97.5% ES = $26,265，和 99% VaR 在同一量级，符合这个直觉。

---

## 3. Greeks（`greeks.py`、`portfolio.py`）

| Greek | 含义 | 你的组合（截至 2026-10-09） |
|---|---|---|
| Delta | 标的价格变动 1 单位，期权价值变多少 | 单个期权 0.32；整个组合 SPY 涨 1% 赚约 $12,714 |
| Gamma | delta 本身随标的变化的速度（凸性） | SPY 涨 1%，美元 delta 增加约 $747 |
| Vega | 隐含波动率变动 1 个百分点，期权价值变多少 | 波动率升 1 点赚约 $2,771 |
| Theta | 时间流逝 1 天，期权价值变多少 | 每天约 -$401 |

**Delta-equivalent（delta 等值敞口）**：把期权换算成"相当于多少股股票"。代码里 SPY 的线性敞口 = 股票 + 期权数量 × delta × 价格。

**参数法为什么不够**：它只用 delta，相当于把期权当成直线。股价大幅波动时，gamma 让真实损益偏离直线，所以需要完全重估（历史模拟、蒙特卡洛）。

---

## 4. 回测（`backtest.py`）

**做法**：每天用前 250 天的数据算第二天的 VaR，再看第二天实际的 P&L 有没有突破 VaR。突破一次叫一个"例外"（exception）。

**用的是哪种 P&L**：hypothetical P&L，即假设组合当天不交易、只因市场变动产生的损益。Basel 回测同时看 hypothetical 和 actual P&L，前者能把模型问题和交易活动分开。

**Kupiec POF 检验**：检验"例外的频率是不是等于 1%"。
你的结果：500 天 8 次例外（预期 5 次），p = 0.215 > 0.05，不能拒绝模型。

**Basel 红黄绿灯（99% VaR，250 天）**：

| 区间 | 例外次数 | 资本乘数加点（plus factor） |
|---|---|---|
| 绿 | 0–4 | 0 |
| 黄 | 5–9 | 0.40 / 0.50 / 0.65 / 0.75 / 0.85 |
| 红 | 10 次及以上 | 1.00 |

你最近 250 天是绿灯。

**从图里能讲的故事**：例外集中在 2025 年 4 月（关税冲击）。之后 VaR 明显上升，因为冲击日进入了 250 天窗口；到 2026 年 4 月，冲击日移出窗口，VaR 又突然下降。这就是历史模拟的"悬崖效应"（cliff effect）。例外集中出现也说明例外不独立，Kupiec 检验不看这一点，Christoffersen 独立性检验会看。

---

## 5. Basel 框架速览

**Basel 2.5（2009 年后）**
- 内部模型法的市场风险资本 = max(昨日 VaR, 乘数 × 过去 60 天平均 VaR) + max(昨日 stressed VaR, 乘数 × 60 天平均 stressed VaR)。
- 乘数至少为 3，再加上回测红黄绿灯的 plus factor。
- VaR：99%、10 天；stressed VaR：用一段历史压力时期（如 2008 年）校准。

**FRTB（Fundamental Review of the Trading Book，Basel III 最终方案里的市场风险部分，常被称为"Basel IV"）**
- 内部模型法（IMA）：用 97.5% ES，并按不同风险因子的流动性设置 10 到 120 天的持有期（liquidity horizons），用压力时期校准。
- 内部模型需要按交易台（desk）审批，每个交易台要通过回测和 P&L 归因测试（PLAT，用 Spearman 相关和 KS 检验比较风险模型 P&L 与前台 P&L）。
- 缺乏足够真实报价的风险因子（non-modellable risk factors）要单独计提。
- 标准法（SA）：基于敏感度的方法（delta、vega、curvature），加上违约风险资本（DRC）和剩余风险附加（RRAO）。
- 美国通过"Basel III Endgame"规则落地，最终规则和实施时间以监管最新公告为准。

---

## 6. 治理与报告（这个职位的日常）

- **定期报告**：每日、每周、每月汇报 VaR、敏感度、限额使用率，以及当天发生的变化及原因。
- **限额与超限**：每个交易台有 VaR 和敏感度限额；超限要上报、解释原因、记录处理结果。
- **数据质量与差异分析（break analysis）**：风险系统和前台或财务的数字对不上时，要找出原因（数据缺失、价格陈旧、头寸不一致等）。项目里的 `validation.py` 就是一个简化版。
- **RCSA（风险与控制自我评估）**：各部门定期评估自己的风险和控制是否有效。
- **模型风险管理（美联储 SR 11-7 指引）**：模型要由独立团队验证，包括概念是否合理、持续监控和结果分析（回测就属于结果分析），并要有"有效质疑"（effective challenge）。

---

## 7. 面试常见问题和回答要点

1. **VaR 的定义和局限？** 见第 1 节；局限：看不到尾部深度，不满足次可加性，依赖历史或分布假设。
2. **三种 VaR 方法怎么选？** 见第 1 节表格；含期权的组合需要完全重估。
3. **为什么 FRTB 用 97.5% ES？** 见第 2 节。
4. **回测出现太多例外怎么办？** 先查数据和头寸是否有误，再看是否市场环境变化（如波动率上升），最后才考虑模型本身，比如窗口长度、加权方法、是否要用 stressed 数据。
5. **Kupiec 检验在检验什么？它的不足？** 检验例外频率；不足：不检验例外是否扎堆（独立性）。
6. **Delta、gamma、vega 分别是什么？** 见第 3 节。
7. **你的组合里 VIX 为什么是对冲？** 见第 1 节最后一条。
8. **历史模拟的悬崖效应是什么？** 见第 4 节；缓解方法：加权历史模拟、和 stressed VaR 一起看。
9. **报告里的数字和前台对不上，你会怎么查？** 头寸 → 市场数据（缺失、陈旧、时间点不同）→ 定价参数 → 模型差异，逐层排查并记录原因。
10. **讲讲你的项目。** 见下面的介绍。

### 60 秒项目介绍（英文）

> I built a small end-to-end market risk workflow in Python. It starts with data validation: aligning the equity and FX calendars, flagging stale prices and outlier returns. Then it measures 1-day 99% VaR and Expected Shortfall for a multi-asset book with options three ways: historical simulation, delta-normal, and Monte Carlo with full revaluation. It reports Greeks and component VaR, and backtests the model over 500 days with the Kupiec test and the Basel traffic light. One finding I like: the long-vega option position partly hedges equity risk because volatility rises when stocks fall, so its component VaR is negative. The backtest also shows the cliff effect of historical simulation around the April 2025 shock.

---

## 8. 面试前的自查清单

- [ ] 能不看代码讲出三种 VaR 方法的区别
- [ ] 能解释为什么历史模拟的 ES 比正态方法高
- [ ] 能手算正态分布下的 99% VaR（2.326σ）
- [ ] 能解释 delta、gamma、vega、theta，以及 VIX 为什么是对冲
- [ ] 能解释回测、Kupiec 检验和红黄绿灯
- [ ] 能讲清 Basel 2.5 到 FRTB 的主要变化
- [ ] 能流畅说出 60 秒项目介绍
