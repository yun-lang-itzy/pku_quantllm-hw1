---
title: "市场数据与时间"
type: concept
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003", "S004"]
tags: ["quant", "learning"]
---

# 市场数据与时间

通用数据契约仍为草稿，末尾 VeighNa 实例已核对源码。具体交易日历、价格调整和可用时间需依据所选市场及供应商定义确定。

## 先写数据契约

最小字段可包含 `symbol`、`timestamp`、`open`、`high`、`low`、`close`、`volume`。同时记录：时间戳是区间开始还是结束、时区、频率、单位、交易日历、价格复权方式、数据来源、版本或哈希。

`timestamp` 相同不代表信息在同一时点可用。事件发生时间、供应商发布时间与系统接收时间可能不同。财报数据要区分报告期末与实际披露时间，并注意之后的修订。

## 质量检查

- 同一品种与时间戳是否唯一、排序正确、时区明确？
- 价格是否有限且为正，`low <= open/close <= high` 是否满足？
- 成交量是否非负，停牌、休市与数据缺失是否区分？
- 异常跳变是拆股、分红、换月、错误报价还是实际行情？
- 使用历史成分股时是否保留退出样本，避免只挑现在仍存在的对象？

检查失败应说明原因，不默认用前值填补所有缺口；填补本身也是需要记录的研究选择。

## 复权与执行价格

复权序列可用于某些收益与信号计算，但不能未经转换就把它当作真实交易价格，与未调整的持仓数量混合记账。分红、拆股、换月等事件需要明确模型和一致口径。

首个合成数据实验不包含公司行动；此限制不能推导为真实市场里可以忽略公司行动。

## 一个时间线例子

假设日 bar 的收盘价在 `t` 日收盘后可用，用它生成信号后，教学模型将订单放到 `t+1` 日开盘撮合。直接用该信号按 `t` 日收盘价成交，通常会引入不合理的可用性假设。

## 待验证

选择实际市场后补充日历、收盘数据发布时间、供应商字段定义和历史修订规则；登记到 [问题清单](../open-questions.md)。

## 已核对的 VeighNa 时间与聚合实例

[CTP 网关](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py) 的 CtpMdApi.onRtnDepthMarketData 使用 ActionDay/本地维护日期与 UpdateTime 构造 Asia/Shanghai 时间，合约缓存未就绪时跳过行情。不能把这个 datetime 不加核验地当作交易日。

[BarGenerator.update_tick](../../raw/sources/vnpy/vnpy/trader/utility.py) 在新分钟 tick 到来时推送上一根 bar，时间戳会归到分钟起点；数据标签时间与真正可得时间不同。回测 [update_daily_close](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py) 使用 datetime.date 分组，夜盘跨日与交易日口径见 [实盘/回测对照](cta-live-vs-backtest.md)。

这些是固定实现的源码事实；交易所官方规则、供应商修订口径与夜盘实验仍待补充。

相关页面：[回测与偏差](backtesting-bias.md) · [研究流程](../guides/research-workflow.md) · [最小回测器](../projects/minimal-backtester.md)
