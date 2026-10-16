---
title: "CTA：实盘与回测的执行语义对照"
type: concept
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003", "S004"]
tags: ["veighna", "source-reading"]
---

# CTA：实盘与回测的执行语义对照

相同策略类并不意味着回测与实盘等价。以下是对已固定源码的核对；教学推演另行标注，尚未执行平台回测。

## 逐项对照

| 问题 | 实盘 CtaEngine / CTP | BacktestingEngine |
| --- | --- | --- |
| 数据推进 | EventEngine 分发实时 tick，示例自行聚合 bar | new_bar/new_tick 逐条回放历史数据 |
| 订单转换 | 依据合约取整，再经 OffsetConverter，可能拆单 | 价格取整；未执行实盘同一套今昨仓拆分 |
| 限价成交 | 由柜台/市场决定，可能部分成交或拒绝 | Bar 看 low/high 是否穿越；满足时直接全量成交 |
| 停止单 | 支持柜台停止单时走服务器，否则本地触发后发限价单 | 根据 bar high/low 或 tick last 触发并生成模拟成交 |
| 订单回报 | 外部异步回报，撤单也可能失败 | 回放函数直接调用策略的订单/成交回调 |
| pos 更新 | 按收到的成交更新，内存集合去重 | 撮合后修改 pos 再调用 on_trade |
| 成本 | 本次已读路径不构成完整券商清算和费用模型 | DailyResult 按成交额费率及价格单位滑点扣成本 |
| 资金与保证金 | 外部账户查询和柜台规则，额外风控需配置 | capital 用于统计；已读发单/撮合路径未按可用保证金阻止开仓 |

定位：[实盘 engine.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/engine.py) 的 send_order/send_server_order/process_trade_event/check_stop_order；[回测 backtesting.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py) 的 send_order/new_bar/cross_limit_order/cross_stop_order/DailyResult；[CTP 网关](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py) 的订单/成交回报。

## Bar 模式的撮合时间线

`new_bar` 的顺序是：设置当前 bar/时间 → cross_limit_order → cross_stop_order → strategy.on_bar → 写入当日收盘价。

因此**常规 on_bar 回调中新建的订单不会参与这一轮已经完成的撮合**。但不是“所有订单都按下一根 open 成交”，也不是对其他回调中下单路径的全局无前视保证。尤其 on_order/on_trade 内再发单以及同根 bar 多类订单相互作用，需要独立审计。

限价买单：`order.price >= bar.low_price > 0` 时满足穿越，成交价 `min(order.price, bar.open_price)`；卖单相反，使用 high 与 `max(order.price, open)`。只用 OHLC 无法知道区间内完整价格路径，且这里未按成交量限制全量成交。

教学推演：上一根 bar 后挂买限价 100。下一根 open=110、low=105，不成交；之后 open=103、low=99，可按 100 模拟成交。若 open=98、low=97，则可按 98 模拟成交。以上是按分支手推，未运行回测。

上游已有 [next-bar 测试](../../raw/sources/vnpy_ctastrategy/tests/test_backtesting.py) 的 `TestBacktestingCross.test_limit_buy_fills_when_bar_low_crosses` 可作为后续实验入口；存在测试文件不等于本次已运行测试。

## 滑点、手续费与账户模型

`DailyResult.calculate_pnl`：

```text
holding_pnl = start_pos * (close - pre_close) * size
trading_pnl += signed_volume * (close - fill_price) * size
turnover += volume * size * fill_price
commission += turnover_of_trade * rate
slippage_cost += volume * size * slippage
net_pnl = holding_pnl + trading_pnl - commission - slippage_cost
```

这里 `slippage` 是价格单位，经数量与合约乘数转成成本，不是基点，也未直接改写 TradeData.price。与本 Wiki 最小现金回测器中“按 bps 改成交价”的规格不同，比较两套结果前必须换算单位与账户模型。

`update_daily_close` 与成交分组使用 `datetime.date()`；是否等于目标市场的交易日，尤其夜盘，仍需额外验证。

## 统计口径：不要只看字段名称

[backtesting.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py) 的 `set_parameters/calculate_statistics` 在本版本中：

- `annual_days` 默认 240；其他扩展指标中还出现硬编码 252，应逐项核对。
- 日收益为 `log(balance / pre_balance)`，首期 pre_balance 使用 capital。
- `annual_return = total_return / total_days * annual_days`，是线性年化百分比，不是几何 CAGR。
- Sharpe 路径使用 `daily_risk_free = risk_free / sqrt(annual_days)` 后与以百分比表示的日收益比较；需要明确 risk_free 的预期单位，再核验其金融含义，不能直接套用教科书公式。
- highlevel 由每日 balance 滚动最大值生成，未显式把初始 capital 作为高点插入。静态推论：首日亏损的回撤可能与“含初始净值高点”的自定义口径不同，应手算复现后记录。

这些是实现口径与待验证问题，不把源码直接判为某种通用定义的证明。相关通用公式仍保留在 [绩效指标](performance-metrics.md)，使用时明确选择并记录口径。

## 下一步实验

用 3–5 根合成 bar 验证：不穿限价则不成交、穿价全量成交、滑点成本单位、首日亏损回撤、夜盘日期分组。先在独立实验环境准备依赖，保留原始快照不变，结果写入报告。当前均未执行。

相关页面：[CTA 导读](../modules/vnpy-ctastrategy.md) · [回测与偏差](backtesting-bias.md) · [最小回测器规格](../projects/minimal-backtester.md) · [问题清单](../open-questions.md)
