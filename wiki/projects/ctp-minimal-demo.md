---
title: "实践 002：底层 CTP 最小连接与行情 Demo"
type: project
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: ["S003"]
tags: ["ctp", "demo", "source-reading"]
---

# 实践 002：底层 CTP 最小连接与行情 Demo

已实现代码、编译验证和离线测试，本机真实登录、自动选约、订阅及快照回调已通过，盘中持续更新仍待验收。代码位于 [experiments/002-ctp-demo](../../experiments/002-ctp-demo/README.md)，入口是 [demo.py](../../experiments/002-ctp-demo/demo.py)。

本地迁移已增加项目根目录的 [run_ctp.py](../../run_ctp.py) 与 [本地说明](../../LOCAL_RUN.md)：`--setup` 在项目 `.venv` 安装原生扩展、保留已有本地账号配置，默认启动持续输出；`--verify` 仅检查扩展，不连接服务器。

## 用户需求与实现

| 需求 | 实现 |
| --- | --- |
| 从底层 Python API 开始 | 直接继承安装包中的 MdApi/TdApi，不经过 MainEngine/Gateway |
| 发起网络连接和账号登录 | TD create/registerFront/init → onFrontConnected → 客户端认证 → 账号登录 |
| 行情登录和订阅 | TD 就绪后默认按柜台成交量快照选择 5 个不同品种合约，再启动 MD 并逐合约订阅确认；支持手动覆盖 |
| 打印行情推送 | onRtnDepthMarketData 选取报价字段并持续输出 JSON；默认无数量/时长限制，Ctrl+C 退出 |

认证和登录请求的本地返回值只表示发送状态，柜台成功以对应回调为准。源码依据：[ctp_gateway.py](../../raw/sources/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py) 的 authenticate/login/subscribe；[原生 MD 绑定](../../raw/sources/vnpy_ctp/vnpy_ctp/api/vnctp/vnctpmd/vnctpmd.cpp) 与 [TD 绑定](../../raw/sources/vnpy_ctp/vnpy_ctp/api/vnctp/vnctptd/vnctptd.cpp) 的请求及 init/exit 方法。

## 学习时抓住三个边界

第一，TD 和 MD 是独立前置、登录与回调。交易登录成功不能代替行情登录成功；MD 订阅应在 MD 登录后进行。

第二，CTP 原生层自带回调工作线程，最小 Demo 可以直接处理回调，不必先构建 Python EventEngine。完整 VeighNa 架构里的事件队列是另一个层次，见 [跨模块链路](../concepts/veighna-event-flow.md)。

第三，原生 `exit()` 会等待工作线程，因此不要从自己的 onRsp/onRtn 回调里调用 exit。本 Demo 的回调只通知停止，由主线程统一释放。断线后退出，不自动反复重试账号。

## 验证状态

- 固定源码在隔离 Linux/Python 3.12 环境成功构建，原始快照不变。
- 实际加载两个原生扩展并创建子类；本地回环的 create/init/exit 探测完成。
- 28 个无网络单元测试通过，覆盖正常链路、失败、报价输出、超时、脱敏、清理、持续运行与自动合约选择。
- 本机真实联调：TD/MD 登录成功，5 个自动选择合约全部订阅并各收到一条快照；午间未观察到后续更新。
- 不传 `--symbols` 时在柜台返回的期货快照范围内按成交量选择 5 个不同品种；查询不可用时使用 rb2701/ag2612/au2612/i2701/m2701 候选池并警告，该池未经实时活跃度核验。可手动指定合约。
- 原生 `reqQryDepthMarketData/onRspQryDepthMarketData` 已核对存在；本机已收到柜台全量快照查询结果并完成按成交量选约。

完整环境、命令与边界见 [实验报告](../../experiments/002-ctp-demo/report.md)。账号配置仅保存在 Git 忽略的本地文件，Wiki 不记录密码或授权码。

## 下一步验收

在可直达 SIMNOW 前置的环境中，直接运行 demo.py，确认自动选出的代码与成交量、TD/MD 登录、订阅确认、持续真实行情，以及 Ctrl+C 正常释放。只有显式有界调试时才设置 --max-ticks/--duration；默认不自动结束。若只有订阅成功却无 tick，检查时段、合约和柜台状态。成功后追加实际证据，保持模拟与真实结果分开。

相关页面：[CTP 模块导读](../modules/vnpy-ctp.md) · [行情时间](../concepts/market-data.md) · [学习看板](../learning-dashboard.md) · [问题清单](../open-questions.md)


## 单次价格触发交易扩展

新增 [交易入口与说明](../../experiments/002-ctp-demo/TRADING.md)：TD 结算确认、合约查询、最新价严格超过阈值后按卖一价买入开仓 1 手，每次运行一次，10 秒未完成申请撤单，不自动追单或平仓。默认 dry-run；实际 SIMNOW 委托需要显式开关和明确的合约、阈值。

2026-10-16 13:48 本机真实 dry-run 已通过：m2701 结算/合约确认成功，20 秒接收 41 条持续更新行情，阈值 1 仅用于测试、触发一次意图、报单次数为 0。此前午间尚未验证的持续行情更新现已补验。47 项离线测试通过，实际柜台报单/成交/撤单仍待确认参数后验收，不能用离线回报替代。证据和运行方法见上述说明。
