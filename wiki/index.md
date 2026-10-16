# 量化交易系统开发 · Wiki 索引

从问题出发阅读，通过资料与实验逐步核验。**已摄取 VeighNa 三个官方源码快照并完成核心路径静态阅读；通用草稿与未运行实验仍明确标注。**

新入口：[VeighNa 三模块源码学习](guides/veighna-source-reading.md)。

## 学习导航

| 页面 | 内容 |
| --- | --- |
| [项目概览](overview.md) | 目标、学习默认起点、知识状态与整体工作方式 |
| [学习路线](roadmap.md) | 六个阶段及各自的可验收成果 |
| [学习看板](learning-dashboard.md) | 实际进度、下一步和复盘入口 |
| [待确认问题与知识缺口](open-questions.md) | 市场选择、前置知识、证据缺口和冲突登记 |
| [术语表](glossary.md) | 常用中英文术语及其概念入口 |
| [维护日志](log.md) | 按时间追加的真实操作记录 |

## 系统概念

| 页面 | 内容 |
| --- | --- |
| [系统架构](concepts/system-architecture.md) | 从行情到信号、订单、成交、持仓与对账 |
| [市场数据与时间](concepts/market-data.md) | 数据契约、时间可用性、质量与复权口径 |
| [回测与偏差](concepts/backtesting-bias.md) | 成交时序、成本、样本划分与常见偏差 |
| [绩效指标](concepts/performance-metrics.md) | 收益、回撤、Sharpe 与指标假设 |
| [订单生命周期](concepts/order-lifecycle.md) | 部分成交、撤单竞态、幂等与恢复 |
| [风险控制](concepts/risk-controls.md) | 订单前检查、账户约束与故障处理 |

## 流程与实践

| 页面 | 内容 |
| --- | --- |
| [摄取、问答与检查](guides/workflows.md) | 持续维护 Wiki 的具体步骤与请求示例 |
| [可复现研究流程](guides/research-workflow.md) | 从可证伪假设到实验记录和复盘 |
| [最小回测器实践规格](projects/minimal-backtester.md) | 首个离线开发项目的范围、时序和验收用例 |
| [底层 CTP 最小 Demo](projects/ctp-minimal-demo.md) | TD/MD 连接登录、订阅与行情打印；离线验证和真实联调边界 |

## VeighNa 源码消化

| 页面 | 内容 |
| --- | --- |
| [三模块源码学习入口](guides/veighna-source-reading.md) | 模块拼接方式、推荐阅读顺序和第一轮结论 |
| [vnpy 平台核心导读](modules/vnpy.md) | 事件、MainEngine、OMS、数据对象和开平转换 |
| [vnpy_ctp 导读](modules/vnpy-ctp.md) | 原生桥、行情/交易连接、时间处理、报单与回报 |
| [vnpy_ctastrategy 导读](modules/vnpy-ctastrategy.md) | 模板、策略状态、回调、归属映射与双均线示例 |
| [跨模块事件与订单链路](concepts/veighna-event-flow.md) | 从 CTP 行情经过策略下单，再到成交更新 pos |
| [CTA 实盘与回测对照](concepts/cta-live-vs-backtest.md) | 限价撮合、成本单位、账户与绩效统计差异 |

## 来源

| 页面 | 内容 |
| --- | --- |
| [S001 · LLM Wiki](sources/llm-wiki.md) | 已摄取的方法来源摘要、原文定位及适用边界 |
| [S002 · vnpy](sources/vnpy.md) | 4.5.0 固定提交、已读核心文件与未读范围 |
| [S003 · vnpy_ctp](sources/vnpy-ctp.md) | 6.7.11.5 固定提交、CTP 适配与原生桥阅读范围 |
| [S004 · vnpy_ctastrategy](sources/vnpy-ctastrategy.md) | 1.5.0 固定提交、策略与回测阅读范围 |
| [候选阅读清单](sources/reading-list.md) | 尚未读取的资料入口、已摄取源码与选择标准 |

## 项目工具

- [维护规范](../AGENTS.md)：后续助手的工作约定。
- [原始资料说明](../raw/README.md) 与 [来源登记](../raw/manifest.json)。
- 模板：[来源摘要](../templates/source.md)、[概念页](../templates/concept.md)、[问答沉淀](../templates/query.md)、[实验记录](../templates/experiment.md)。
- [实验目录说明](../experiments/README.md)：后续代码与报告如何组织。
- [检查脚本](../scripts/wiki_lint.py)：执行 `python3 scripts/wiki_lint.py`。
- [本地运行说明](../LOCAL_RUN.md) 与 [启动入口](../run_ctp.py)：在自己的电脑安装并持续运行 CTP Demo。
