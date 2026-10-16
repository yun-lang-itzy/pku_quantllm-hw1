---
title: "vnpy_ctp：柜台适配与异步回报"
type: concept
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003"]
tags: ["veighna", "source-reading"]
---

# vnpy_ctp：柜台适配与异步回报

固定版本及实际阅读范围见 [S003](../sources/vnpy-ctp.md)。它负责把 CTP 字段/调用转换为 VeighNa 请求与事件，策略信号不在这个模块产生。

## 从 Python 到原生库

[api/__init__.py](../../raw/sources/vnpy_ctp/vnpy_ctp/api/__init__.py) 导出 `MdApi`、`TdApi` 与常量；[meson.build](../../raw/sources/vnpy_ctp/meson.build) 组织 pybind11/C++ 与供应商库。原生行情层的 `OnRtnDepthMarketData` 复制结构体入 TaskQueue，`processTask` 的工作线程分派，`processRtnDepthMarketData` 获取 GIL、构造字典后调 Python 回调。

定位：[vnctpmd.cpp](../../raw/sources/vnpy_ctp/vnpy_ctp/api/vnctp/vnctpmd/vnctpmd.cpp) 的对应方法。这是原生行情路径的局部源码证据，未逐行核验交易层所有绑定或供应商二进制。

## 连接与准备阶段

以下均定位到 [ctp_gateway.py](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py)：

1. `CtpGateway.connect` 分别启动 TD 与 MD，并注册定时查询。
2. TD 的 `onFrontConnected` 根据授权码选择认证或登录；成功认证继续登录。
3. `onRspUserLogin` 保存 FrontID、SessionID，发出结算确认请求；`onRspSettlementInfoConfirm` 尝试发送合约查询。
4. `onRspQryInstrument` 生成 ContractData，保存乘数、最小变动价位和交易量等；最后设置 `contract_inited`，回放暂存的订单/成交。
5. MD 登录成功后恢复已登记的订阅。`process_timer_event` 每两个 timer 事件轮换查询账户或持仓，并更新本地日期。

“网络已连接”“已登录”“合约准备好”“策略已初始化”是不同状态；不能用一个布尔值覆盖它们。

## 行情与时间

`onRtnDepthMarketData` 会过滤无 UpdateTime 或尚无合约缓存的行情。时间戳取 ActionDay；当 ActionDay 为空或交易所为 DCE 时使用本地维护日期，拼接 UpdateTime/UpdateMillisec 并设置 Asia/Shanghai。

因此不能直接把 TickData.datetime 等同于 CTP TradingDay。夜盘、节假日、跨午夜和数据回放必须另做验证。完整交易日历并没有由这些拼接规则自动提供。

## 下单与回报

`CtpGateway.send_order → CtpTdApi.send_order` 将方向、开平、订单类型映射为 CTP 字段。`reqOrderInsert` 返回非零表示本地请求发送失败；返回零时创建本地 `SUBMITTING` 订单，发布事件后返回 `vt_orderid`。柜台是否接受、是否成交仍要等异步回报。

本地 `orderid = FrontID_SessionID_OrderRef`；`onRtnOrder` 保存 `OrderSysID → orderid`，`onRtnTrade` 再通过它关联成交。VeighNa 外层标识另带 `gateway_name`（[object.py](../../raw/sources/vnpy/vnpy/trader/object.py)）。

`onRspOrderInsert` 生成拒单状态；`onRtnOrder` 还会把某些“取消 + 报单被拒绝”的组合映射为 REJECTED。`cancel_order` 只是发送撤单请求，不提前把订单强制改为 CANCELLED。

## 状态顺序与故障问题

`order_lock` 保证本地 SUBMITTING 在相应柜台订单事件之前入队。它没有将网络、原生回调、Python 事件分发与磁盘持久化合成一个全局事务。

后续离线演练应覆盖：合约未就绪的暂存、成交找不到 OrderSysID、重复回报、断线后订阅恢复、部分成交与撤单竞争。上述是由代码边界提出的验证任务，尚未复现为确定缺陷。

相关页面：[事件与订单链路](../concepts/veighna-event-flow.md) · [订单生命周期](../concepts/order-lifecycle.md) · [市场数据与时间](../concepts/market-data.md)
