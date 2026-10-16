---
title: "vnpy：平台核心源码导读"
type: concept
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S002"]
tags: ["veighna", "source-reading"]
---

# vnpy：平台核心源码导读

固定版本与阅读边界见 [S002](../sources/vnpy.md)。先把它理解为多个模块共享的事件、数据契约和服务入口。

## 先读哪些对象

| 对象 | 作用 | 源码定位 |
| --- | --- | --- |
| Event / EventEngine | 用类型和数据描述事件；队列驱动分发、定时器产生事件 | [event/engine.py](../../raw/sources/vnpy/vnpy/event/engine.py)：Event、EventEngine |
| TickData / BarData | 标准行情与 K 线数据，使用统一合约标识 | [object.py](../../raw/sources/vnpy/vnpy/trader/object.py) |
| OrderRequest / OrderData / TradeData | 交易请求、订单最新状态、实际成交三个对象 | [object.py](../../raw/sources/vnpy/vnpy/trader/object.py) |
| MainEngine | 挂载 App 与 Gateway，按网关名称路由请求 | [engine.py](../../raw/sources/vnpy/vnpy/trader/engine.py)：MainEngine |
| OmsEngine | 缓存行情、订单、成交、持仓、账户、合约与活跃订单 | 同文件：OmsEngine |
| BaseGateway | 外部接口适配契约，统一向 EventEngine 发布数据 | [gateway.py](../../raw/sources/vnpy/vnpy/trader/gateway.py) |
| OffsetConverter / PositionHolding | 根据持仓和冻结量转换开平请求 | [converter.py](../../raw/sources/vnpy/vnpy/trader/converter.py) |

`vt_symbol = symbol.exchange`；`vt_orderid = gateway_name.orderid`；`vt_tradeid = gateway_name.tradeid`。这些是当前对象构造中的命名空间，不应假设已经解决了所有跨日/跨会话唯一性问题（`OrderData/TradeData.__post_init__`）。

## 一条事件如何被处理

`BaseGateway.on_tick` 先发通用 `EVENT_TICK`，再发 `EVENT_TICK + vt_symbol`；这是两条事件。`EventEngine._run` 从 Queue 取事件，`_process` 先顺序调用该类型的 handlers，再调用 general handlers。

因此，同一类型处理函数通常在一个分发线程中依次运行；耗时策略会拖慢后续事件。这里的依据是同步调用结构，具体吞吐和延迟尚未测量。`_run` 只捕获队列 Empty，不能把它理解成替每个处理函数自动隔离任意异常；CTA 自己另有回调异常包装。

## MainEngine 和 OMS 没有包办什么

`MainEngine.__init__` 启动事件引擎并切换工作目录到 `TRADER_DIR`。`add_app` 创建应用与对应 engine，但没有自动调用 `CtaEngine.init_engine`；后者需要另行触发初始化。这解释了“模块已挂载”和“业务已经就绪”的区别。

`MainEngine.send_order` 的核心是找到网关并转发。默认引擎初始化中有日志、OMS、邮件和微信等组件，不能因此假设已有账户级仓位/损失/频率的完整风控；README 将 risk_manager 列为单独应用，未在本次下载范围内。

OMS 的账户、持仓快照来自外部事件；成交缓存与开平转换更新不等于建立了一个覆盖费用、保证金、结算和外部现金流的独立清算系统。

## 平今/平昨为何会拆单

`OffsetConverter.convert_order_request` 在需要转换且非 lock/net 优先分支时，对 SHFE/INE 调用 `PositionHolding.convert_order_request_shfe`。该方法先考虑可平量和冻结量，再优先平今，余量平昨，可能返回零、一或多笔请求。

教学推演：某方向可平今 1、可平昨 2，无冻结，要平 2，转换后可得到平今 1 与平昨 1。这是对代码分支的手工解释，尚未作为运行用例执行；交易所当期规则仍需官方资料补充。

## 下一次阅读的产物

画出 TickData、OrderData、TradeData 三种对象的字段差异；用一张表记录通用事件与专用事件的订阅者；再设计一个重复成交回报的离线实验，分别观察 OMS 与 CTA 的更新边界。

相关页面：[事件与订单链路](../concepts/veighna-event-flow.md) · [CTP 导读](vnpy-ctp.md) · [CTA 导读](vnpy-ctastrategy.md) · [风险控制](../concepts/risk-controls.md)
