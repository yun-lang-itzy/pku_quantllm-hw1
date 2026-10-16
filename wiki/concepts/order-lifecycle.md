---
title: "订单生命周期与幂等"
type: concept
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003", "S004"]
tags: ["quant", "learning"]
---

# 订单生命周期与幂等

本页为教学草稿，不对应具体券商接口。实际状态名称、撤改单语义和事件编号需按官方接口核验。

## 一个简化模型

```text
created → risk-approved → submitted → acknowledged → partially-filled → filled
              │               │               └→ cancelled / expired
              │               └→ rejected / 状态未知待查询
              └→ risk-rejected
```

图中省略了部分路径。收到确认后可以直接全部成交；部分成交后仍可能撤销剩余量；发起撤单请求也不表示已经撤单成功。拒单与取消后的已成交部分仍需保留。

## 必须区分的对象

- 订单意图：希望做什么，尚未产生外部订单。
- 订单状态：请求是否接受、还有多少未成交、是否进入终态。
- 成交事件：实际成交的数量、价格、时间和费用，用于驱动账本。

持仓不应因“已提交订单”就改变。资金或仓位占用可以在订单创建时预留，但需与真实成交和释放规则区分。

## 容易出错的场景

| 场景 | 需要定义的行为 |
| --- | --- |
| 成交回报重复到达 | 依据稳定成交编号去重，同一成交只记一次账 |
| 请求超时 | 状态未知；先查询、对账或按接口幂等键重试，避免盲目重复下单 |
| 撤单与成交同时发生 | 以外部实际回报核算累计成交，不能把已发生的成交抹掉 |
| 进程重启 | 恢复未完成订单，核对外部成交、持仓、资金与本地账本 |
| 消息乱序 | 保留原始事件，依据接口序号或查询快照做确定性处理 |

建议保存客户端订单编号、外部订单编号、成交编号、请求/接收时间和原始回报定位，形成可回放事件记录。

## 已核对的 VeighNa 状态与成交路径

[constant.py](../../raw/sources/vnpy/vnpy/trader/constant.py) 定义 SUBMITTING、NOTTRADED、PARTTRADED、ALLTRADED、CANCELLED、REJECTED；本页上方的 expired 等教学状态不应直接当作该枚举成员。

[CTP send_order/onRtnOrder/onRtnTrade](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py) 分离本地发送、订单状态和实际成交。返回 vt_orderid 不意味着已成交；撤单请求不等于撤单成功。`order_lock` 解决一部分本地提交事件与柜台回报入队顺序，不代表全局事务。

[CTA process_trade_event](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/engine.py) 用内存 vt_tradeids 集合去重，再更新 pos 并回调策略。它不是重启后可恢复的完整幂等账本；订单归属与外部账户对账仍需验证。详见 [事件与订单链路](veighna-event-flow.md)。

相关页面：[系统架构](system-architecture.md) · [风险控制](risk-controls.md) · [研究流程](../guides/research-workflow.md)
