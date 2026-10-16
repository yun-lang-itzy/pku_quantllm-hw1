---
title: "vnpy_ctastrategy：策略接口、实盘与回测"
type: concept
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S004"]
tags: ["veighna", "source-reading"]
---

# vnpy_ctastrategy：策略接口、实盘与回测

固定版本、阅读范围见 [S004](../sources/vnpy-ctastrategy.md)。README 将此应用定位为单标的 CTA；跨多个合约的完整组合管理不能仅凭单个 `strategy.pos` 推导出来。

## 策略接口是如何复用的

[CtaTemplate](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/template.py) 保存 engine、策略名、vt_symbol、`inited/trading/pos`，提供生命周期与 tick/bar/order/trade 回调。`buy/sell/short/cover` 分别组合 LONG/OPEN、SHORT/CLOSE、SHORT/OPEN、LONG/CLOSE。

这些方法通过 `self.cta_engine.send_order` 委派给当前 engine；`trading=False` 时返回空列表。这一层共享接口，使相同策略类可用于实盘引擎与回测引擎，但两者可能产生不同订单数量、价格、状态和成本。

## 实盘 CtaEngine 的三张映射

[engine.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/engine.py) 中：

- `symbol_strategy_map`：合约对应哪些策略，用于分发行情。
- `orderid_strategy_map`：订单对应哪个策略，用于回报归属。
- `strategy_orderid_map`：每个策略的未完成订单编号集合，用于跟踪和撤单。

`process_tick_event` 先检查本地停止单，再给已初始化的策略调用 on_tick；是否允许策略发新单还由模板的 trading 开关控制。

`process_trade_event` 先对内存集合 `vt_tradeids` 去重，再按订单找策略、更新净 pos，随后调用 on_trade 并保存变量。这个 pos 是策略视角的净数量；柜台账户的分方向持仓是另一组对象。去重集合与订单归属映射没有在此路径中形成重启后的完整持久事件日志。

## 启停和错误边界

`init_strategy` 使用单工作线程执行初始化；`_init_strategy` 调 on_init、恢复变量、订阅合约，然后设置 inited。`start_strategy` 调 on_start 后设 trading；`stop_strategy` 调 on_stop、关 trading、撤策略订单并同步变量。

`call_strategy_func` 捕获异常，将 trading/inited 设为 False 并写日志；该包装自身没有像 `stop_strategy` 一样调用 cancel_all。因此“策略异常标记停止”不能直接理解为“所有在途单已撤、仓位已平”。初始化/启动函数在回调异常后是否又设置成功标记，需作为后续故障用例核对；此处不把静态观察升级为已复现故障。

## 跟一遍 DoubleMaStrategy

源码：[double_ma_strategy.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/strategies/double_ma_strategy.py)。

1. `on_init` 创建 BarGenerator、ArrayManager 并请求预热历史。
2. `on_tick` 调 BarGenerator.update_tick，将 tick 合成分钟 bar；跨分钟收到新 tick 时推送上一根完成的 bar。
3. `on_bar` 先撤旧单，再更新数组。ArrayManager 默认 size=100，`inited` 取决于填满数组，并不只是等 slow_window=20（[utility.py](../../raw/sources/vnpy/vnpy/trader/utility.py) 的 ArrayManager）。
4. 用快慢均线当前/前值的严格不等式判断交叉。若由空转多，先 cover 再 buy；反向则 sell 后 short。
5. 示例按 bar.close_price 提交限价；实际是否、何时成交由 engine 与市场决定，不是立刻按该收盘价成交。

示例中一笔开平反转可以产生两个意图，再叠加实盘开平转换，返回的订单列表可能更多。示例策略是一份接口示范，不是盈利证据。

继续阅读：[实盘与回测对照](../concepts/cta-live-vs-backtest.md) · [事件与订单链路](../concepts/veighna-event-flow.md) · [源码阅读路线](../guides/veighna-source-reading.md)
