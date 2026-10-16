---
title: "S004 · vnpy_ctastrategy 1.5.0 源码快照"
type: source
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S004"]
tags: ["veighna", "source-reading"]
---

# S004 · vnpy_ctastrategy 源码快照

## 来源与版本

- 官方仓库：<https://github.com/vnpy/vnpy_ctastrategy>。
- 固定提交：`7a8768de9784dda35a7b261a7ade1dbfbff50919`，提交时间 2026-10-05T22:22:15+08:00。
- 下载/摄取日期：2026-10-16；[包入口](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/__init__.py) 声明 `1.5.0`；[pyproject](../../raw/sources/vnpy_ctastrategy/pyproject.toml) 声明 `vnpy>=4.4.0`、Python `>=3.10`。
- [完整源码目录](../../raw/sources/vnpy_ctastrategy/)：38 个 Git 条目；[逐文件索引](../../raw/sources/vnpy_ctastrategy.snapshot.json) 固定原始字节与提交。
- 来源是官方 GitHub 默认分支固定提交，不是安装后的运行环境；声明约束满足不等于运行兼容已验证。

## 实际阅读范围

| 文件 | 范围与定位 |
| --- | --- |
| [README](../../raw/sources/vnpy_ctastrategy/README.md)、[pyproject](../../raw/sources/vnpy_ctastrategy/pyproject.toml)、[包入口](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/__init__.py)、[base.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/base.py) | 模块范围、版本、App 挂载和停止单对象 |
| [template.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/template.py) | CtaTemplate 的状态、参数/变量、生命周期、四种买卖接口、交易开关与 load_bar；TargetPosTemplate 未完整阅读 |
| [engine.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/engine.py) | 初始化与事件分发、订单归属、成交去重和 pos、限价/本地停止单、取整、策略添加/初始化/启停、异常包装及变量持久化；策略自动发现等只做定位 |
| [backtesting.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py) | 参数、数据加载与预热、回放、bar/tick 处理、撮合/撤单、DailyResult 盈亏与主要绩效公式；优化器、绘图和部分扩展指标未全面阅读 |
| [double_ma_strategy.py](../../raw/sources/vnpy_ctastrategy/vnpy_ctastrategy/strategies/double_ma_strategy.py) | 全文，追踪 tick→bar→指标→交叉→委托 |
| [test_backtesting.py](../../raw/sources/vnpy_ctastrategy/tests/test_backtesting.py)、[test_cta_engine.py](../../raw/sources/vnpy_ctastrategy/tests/test_cta_engine.py)、[conftest.py](../../raw/sources/vnpy_ctastrategy/tests/conftest.py) | 首个 next-bar 手算测试、测试方法清单、FakeGateway/FakeMainEngine 与临时配置隔离；未运行测试套件，也未逐行阅读所有测试 |

## 已核对的结论

- 同一 `CtaTemplate` 接口可交给实盘 `CtaEngine` 或 `BacktestingEngine`；复用的是策略接口，不是两者的完整执行语义。
- 实盘 `process_trade_event` 在调用 `on_trade` 前更新 `strategy.pos`，按内存中的 `vt_tradeids` 集合过滤重复成交。
- `new_bar/new_tick` 先撮合已有订单，再回调策略。Bar 限价单用 low/high 判断穿越，满足时全量成交；不是一概按下一根开盘成交。
- `DailyResult` 按合约乘数计算逐日持仓/交易盈亏；滑点按价格单位计为额外成本，不是 bps。
- 当前统计使用对数日收益、默认 `annual_days=240`，但 `annual_return` 是总收益的线性年化，不是几何 CAGR。

## 适用边界

这份来源支持特定实现的描述，不证明示例策略能盈利。未安装依赖、执行回测或做实盘联调，关键局限见 [实盘与回测对照](../concepts/cta-live-vs-backtest.md)。

消化入口：[CTA 模块导读](../modules/vnpy-ctastrategy.md) · [源码学习总览](../guides/veighna-source-reading.md)
