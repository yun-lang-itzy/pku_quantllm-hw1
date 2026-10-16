---
title: "VeighNa 三模块源码学习入口"
type: guide
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S002", "S003", "S004"]
tags: ["veighna", "source-reading"]
---

# VeighNa 三模块源码学习入口

三个仓库已完整下载并固定版本，完成第一轮核心路径静态阅读。此入口将源码转成可按顺序学习的知识，而不是把完整下载当成全部理解。

## 三个模块怎样拼起来

| 模块 | 本次版本 / 提交前缀 | 核心责任 | 深入入口 |
| --- | --- | --- | --- |
| vnpy | 4.5.0 / c6e231caf32b | 统一事件、对象、MainEngine、OMS 与网关契约 | [平台核心导读](../modules/vnpy.md) |
| vnpy_ctp | 6.7.11.5 / 1be9bfb52922 | CTP 原生接口和 Python 网关，转换请求与回报 | [CTP 导读](../modules/vnpy-ctp.md) |
| vnpy_ctastrategy | 1.5.0 / 7a8768de9784 | 策略模板、实盘策略调度、历史回测与示例 | [CTA 导读](../modules/vnpy-ctastrategy.md) |

版本声明见各 [来源摘要](../sources/vnpy.md)、[CTP 来源](../sources/vnpy-ctp.md)、[CTA 来源](../sources/vnpy-ctastrategy.md)。三个快照共 341 个 Git 条目，含 8 个符号链接，约 77.3 MB 原始条目内容；每个条目有字节哈希。不是 release 组合认证，也未执行安装兼容性测试。

## 推荐按这个顺序读

| 顺序 | 问题 | 阅读位置 | 学习产物 |
| --- | --- | --- | --- |
| 1 | 什么是行情、订单、成交，标识如何构造？ | vnpy object.py / constant.py / trader/event.py | 一张对象字段与标识对照表 |
| 2 | 一个事件如何到达策略？ | EventEngine、BaseGateway、OmsEngine | 手绘发布→入队→分发顺序，标出线程与队列 |
| 3 | 同一策略如何进入实盘或回测？ | CtaTemplate、CtaEngine、BacktestingEngine | 写出两套 engine 相同接口与不同语义 |
| 4 | 一个简单信号怎样变成委托？ | DoubleMaStrategy、BarGenerator、ArrayManager | 逐回调记录预热、交叉、撤单与开平意图 |
| 5 | 订单真的成交了吗？ | CtaEngine.send_server_order、MainEngine、CtpTdApi | 追一笔 buy 和一笔成交回报，区别请求与成交 |
| 6 | 回测假设与真实执行差在哪？ | new_bar、cross_limit_order、DailyResult、统计公式 | 用合成 bar 手算预期，并列出待运行用例 |

详细文件链接、已读范围和未读区域分别保存在 S002/S003/S004，避免以后重复声称已读完整仓库。

## 第一轮消化的关键结论

1. **事件是模块之间的连接方式。** CTP 原生桥的 TaskQueue 与 vnpy EventEngine 队列分开；策略回调不是直接在原生行情回调中运行。
2. **订单和成交是不同对象。** 返回 vt_orderid 只提供追踪身份；策略 pos 的变化依据成交回报。
3. **MainEngine 的路由不能替代完整风控。** 价格取整、平今平昨转换、OMS 缓存也分别有各自职责。
4. **复用策略接口，不代表实盘与回测等价。** 限价穿越、部分成交、资金约束、滑点单位、夜盘日期和统计口径都需要检查。
5. **源码是具体版本的证据。** 示例双均线的存在、测试用例的存在或 README 的宣传都不能证明策略收益。

结论定位：[跨模块链路](../concepts/veighna-event-flow.md) · [实盘/回测对照](../concepts/cta-live-vs-backtest.md)。

## 现在可做的第一个学习任务

只追踪 DoubleMaStrategy，不运行交易连接。画出 `on_init → 预热 → on_tick → BarGenerator → on_bar → buy/sell/short/cover → engine.send_order`；解释为什么 `bar.close_price` 作为限价不等于收盘成交，以及为什么 ArrayManager 的 100 根预热与 20 根慢均线不是同一条件。

然后手算“挂 100 的买单，下一根最低 105，再下一根最低 99”会怎样。运行验证留待后续离线实验；不得把手推结果记录成已执行测试。

## 当前完成与未完成

第一轮完成下载、版本固定、原始条目哈希登记、核心链路阅读与 Wiki 综合，当时没有执行安装或运行。随后已开发 [底层 CTP Demo](../projects/ctp-minimal-demo.md)，在隔离环境完成 C++ 扩展构建、加载、本地回环生命周期和离线测试；真实 SIMNOW 登录/行情尚未验证。

完整平台、上游测试套件、回测仍未运行；UI、ML/alpha、其他框架应用和原生交易全部回调尚未全面阅读。

后续待验证事项见 [问题清单](../open-questions.md)，实际个人学习进度在 [学习看板](../learning-dashboard.md) 记录。

返回 [Wiki 索引](../index.md)

下一阶段：[从 CTP Demo 到完整系统分层](veighna-system-layers.md)，学习标准化接口、事件总线、OMS、指令路由及 CTA/投组/价差应用。
