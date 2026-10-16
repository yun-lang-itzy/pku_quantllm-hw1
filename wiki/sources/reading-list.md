---
title: "候选阅读清单"
type: catalog
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: []
tags: ["quant", "learning"]
---

# 候选阅读清单

**以下网址未在本次初始化中读取或检测；仅是候选入口，不是已摄取来源。** 尚未分配来源编号，不用于支撑 Wiki 量化结论。按基础与市场选择后，一次整理一份具体资料。

| 优先级 | 方向 | 候选入口 | 阅读时要回答的问题 |
| --- | --- | --- | --- |
| 1 | Python 基础 | [Python 官方教程](https://docs.python.org/3/tutorial/) | 能否读取数据、写函数、处理异常并复现运行？ |
| 1 | 数值计算 | [NumPy 文档](https://numpy.org/doc/stable/) | 数组、维度、缺失值与向量化有什么边界？ |
| 1 | 时间序列与表格 | [pandas 用户指南](https://pandas.pydata.org/docs/user_guide/) | 索引对齐、shift、rolling、时区会怎样改变结果？ |
| 2 | 工程验证 | [pytest 文档](https://docs.pytest.org/en/stable/) | 如何用手算预期验证业务规则和错误输入？ |

## 已摄取的源码资料

VeighNa 三模块已从候选转为固定源码来源：[S002 · vnpy](vnpy.md)、[S003 · vnpy_ctp](vnpy-ctp.md)、[S004 · vnpy_ctastrategy](vnpy-ctastrategy.md)。已读取的是来源摘要明确列出的核心路径，仍有未读范围；[学习入口](../guides/veighna-source-reading.md) 汇总消化结果。

## 需要补充的资料类别

- 所选市场的官方交易规则、交易日历、订单类型、交易单位与结算说明。
- 实际数据供应商的字段、复权、历史修订与时间可用性文档。
- 概率统计、时间序列分析、回测偏差和多重试验的可靠资料。
- 实际使用框架的固定版本文档、源码与最小示例。

## 阅读记录如何变为知识

选定具体章节或文件后记录标题、作者/机构、版本与获取时间；可保存的内容原样归档，实际读取后才在 [来源登记](../../raw/manifest.json) 编号，并用 [来源模板](../../templates/source.md) 提炼主张与原文定位。

无法取得全文时如实记录已读取范围，不用书名或首页链接代替内容证据。

相关页面：[学习路线](../roadmap.md) · [问题清单](../open-questions.md) · [维护流程](../guides/workflows.md)
