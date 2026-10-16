---
title: "起始术语表"
type: glossary
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003", "S004"]
tags: ["quant", "learning"]
---

# 起始术语表

以下为待核验的入门释义；后续结合选定市场、资料和实验修订。

| 术语 | 起始解释 | 延伸阅读 |
| --- | --- | --- |
| OHLCV | 一个时间区间内的开盘、最高、最低、收盘价与成交量；完整 bar 通常在区间结束后才确定 | [数据与时间](concepts/market-data.md) |
| Alpha / 信号 | 对未来收益或交易机会的假设性判断；信号并不等于已下单 | [系统架构](concepts/system-architecture.md) |
| Position / 仓位 | 当前持有数量或价值；目标仓位与实际持仓可能不同 | [系统架构](concepts/system-architecture.md) |
| Order / 订单 | 向执行系统发出的交易请求，可能被拒绝、撤销或部分成交 | [订单生命周期](concepts/order-lifecycle.md) |
| Fill / 成交 | 实际发生的交易执行记录，应驱动账户和持仓变化 | [订单生命周期](concepts/order-lifecycle.md) |
| Slippage / 滑点 | 实际或模拟成交价相对明确参考价格的偏离，参考点必须说明 | [回测与偏差](concepts/backtesting-bias.md) |
| Look-ahead bias / 前视偏差 | 在决策或成交建模中使用当时尚不可获得的信息 | [回测与偏差](concepts/backtesting-bias.md) |
| Survivorship bias / 幸存者偏差 | 研究样本忽略历史退出、退市或失败对象而产生偏差 | [回测与偏差](concepts/backtesting-bias.md) |
| Drawdown / 回撤 | 净值相对之前高点的跌幅，需要约定符号和采样频率 | [绩效指标](concepts/performance-metrics.md) |
| Sharpe ratio | 超额收益均值与波动的比值，年化需要频率及相关性等假设 | [绩效指标](concepts/performance-metrics.md) |
| Idempotency / 幂等 | 同一事件重复处理不重复产生业务效果，如不重复记账 | [订单生命周期](concepts/order-lifecycle.md) |
| Reconciliation / 对账 | 对比内部账本与外部成交、持仓和资金，定位差异 | [风险控制](concepts/risk-controls.md) |
| bps / 基点 | 1 bps = 0.01% = 0.0001，常用于费用或价格偏移 | [最小回测器](projects/minimal-backtester.md) |
| Walk-forward / 滚动检验 | 按时间向前移动训练/验证窗口，模拟顺序决策；并不自动消除反复试验带来的过拟合 | [研究流程](guides/research-workflow.md) |

## VeighNa 已核对的对象术语

| 术语 | 固定源码中的含义 | 出处 |
| --- | --- | --- |
| vt_symbol / vt_orderid / vt_tradeid | 分别以交易所或网关命名空间组合的标识 | [object.py](../raw/sources/vnpy/vnpy/trader/object.py) |
| Offset | OPEN、CLOSE、CLOSETODAY、CLOSEYESTERDAY 等开平语义，与买卖方向分开 | [constant.py](../raw/sources/vnpy/vnpy/trader/constant.py) |
| strategy.pos | CTA 策略按成交维护的净数量，不等于柜台所有分方向账户持仓 | [CtaEngine.process_trade_event](../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/engine.py) |
| MdApi / TdApi | CTP 行情与交易的两个原生接口，Python 网关分别封装 | [api 入口](../raw/sources/vnpy_ctp/vnpy_ctp/api/__init__.py) |

相关页面：[跨模块链路](concepts/veighna-event-flow.md) · [CTA 导读](modules/vnpy-ctastrategy.md)

返回 [Wiki 索引](index.md)
