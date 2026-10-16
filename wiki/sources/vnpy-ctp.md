---
title: "S003 · vnpy_ctp 6.7.11.5 源码快照"
type: source
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S003"]
tags: ["veighna", "source-reading"]
---

# S003 · vnpy_ctp 源码快照

## 来源与版本

- 官方仓库：<https://github.com/vnpy/vnpy_ctp>。
- 固定提交：`1be9bfb5292208e5c258cc769c90be4abe83f9a9`，提交时间 2026-10-05T22:21:43+08:00。
- 下载/摄取日期：2026-10-16；[pyproject](../../raw/sources/vnpy_ctp/pyproject.toml) 版本 `6.7.11.5`，声明 `vnpy>=3.0.0`、Python `>=3.10`。README 说明基于 CTP 6.7.11；包版本与 CTP API 版本不能混为一谈。
- [完整源码目录](../../raw/sources/vnpy_ctp/)：93 个 Git 条目，含 8 个 macOS framework 符号链接；[逐文件索引](../../raw/sources/vnpy_ctp.snapshot.json) 对符号链接保存的是链接文本的哈希，未将其改写为重复文件。
- 通过官方 GitHub 浅克隆后原样导出。仓库自带的原生库、头文件和许可文件一并保留，未执行或重新编译。

## 实际阅读范围

| 文件 | 范围与定位 |
| --- | --- |
| [README](../../raw/sources/vnpy_ctp/README.md)、[pyproject](../../raw/sources/vnpy_ctp/pyproject.toml)、[meson.build](../../raw/sources/vnpy_ctp/meson.build) | 版本、依赖、构建后端；Meson 的平台/编译器和库路径相关段落 |
| [包入口](../../raw/sources/vnpy_ctp/vnpy_ctp/__init__.py)、[api 入口](../../raw/sources/vnpy_ctp/vnpy_ctp/api/__init__.py) | CtpGateway、MdApi/TdApi 与常量导出 |
| [ctp_gateway.py](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py) | Python 网关主链：映射表、连接、查询调度、行情回调、认证登录/结算确认、合约/持仓/账户、报单/撤单及订单/成交回报；connect/login 底层调用细节未逐行展开 |
| [vnctpmd.cpp](../../raw/sources/vnpy_ctp/vnpy_ctp/api/vnctp/vnctpmd/vnctpmd.cpp) | OnRtnDepthMarketData、processTask、processRtnDepthMarketData、init/exit 及绑定入口定位 |

交易 C++ 绑定只做目录/符号检索，未逐行审阅；未全面审阅代码生成器、供应商头文件、二进制内部实现或所有错误分支。Python 回调结构不代表已验证 CTP 服务器全部语义。

## 已核对的结论

1. `CtpGateway` 分开管理行情 `CtpMdApi` 与交易 `CtpTdApi`；行情和交易登录状态各自维护。
2. 行情回调构造 `TickData` 后调用 `gateway.on_tick`；未有合约缓存时丢弃行情。时间来自 ActionDay/本地日期与 UpdateTime，设置 Asia/Shanghai。
3. 交易登录后发起结算确认，随后查询合约；合约准备前暂存订单/成交回报，准备后回放（`onRspUserLogin/onRspSettlementInfoConfirm/onRspQryInstrument`）。
4. `send_order` 的返回值是网关订单标识，不是成交证明；异步回报通过 `onRtnOrder/onRtnTrade` 到达。
5. `order_lock` 用于保证本地 SUBMITTING 事件先于相应柜台订单回报入队；不能由此推断整个系统具有全局事务或重启幂等。
6. 原生行情回调先复制数据到 C++ TaskQueue，工作线程获取 GIL、构造字典并调用 Python。此队列与 Python EventEngine 队列是两层不同的队列。

## 限制与后续问题

最初摄取时未编译或运行。后续 [底层 CTP Demo](../projects/ctp-minimal-demo.md) 已从同一固定提交构建原生扩展，核对 TD 创建/认证/登录/期货行情快照查询（reqQryDepthMarketData/onRspQryDepthMarketData）与 MD 订阅接口，并完成本地回环的 create/init/exit 验证和离线测试；真实柜台联调受 TCP 网络条件限制，尚未登录账户或收到行情。

夜盘跨日、跨会话订单恢复、手续费和保证金口径仍未核验。`OrderSysID → 本地 orderid` 映射与回报顺序是后续故障实验重点。

消化入口：[CTP 模块导读](../modules/vnpy-ctp.md) · [事件与订单链路](../concepts/veighna-event-flow.md) · [待确认问题](../open-questions.md)
