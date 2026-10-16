---
title: "跳空动量因子挖掘：最多四轮"
type: project
status: draft
created: 2026-10-16
updated: 2026-10-16
sources: []
tags: ["factor", "momentum", "gap", "research"]
---

# 跳空动量因子挖掘

这是待检验的实验计划，尚无真实数据挖掘结果。用户要求每轮10–20个因子、最多4轮；首轮已设计16个候选，实际执行0轮。市场、标的池、数据源与频率待确认；现有CTP短时日志不够支撑历史统计评估。

[首轮完整定义与评估约束](../../experiments/003-gap-momentum/README.md) 覆盖跳空幅度、区间突破、趋势一致性、波动压缩，以及前5分钟未回补/成交量/VWAP确认。公式均为待验证假设，方向不因回测结果事后翻转。

先确定session定义、数据和信号可得时点，再评估入场后的收益。期货换月、股票除权与数据缺失导致的假跳空需剔除。每轮登记所有尝试，按时间划分开发/验证/最终留出，最多4轮并允许提前停止，不伪造收益或将合成测试视为挖掘完成。

相关：[研究流程](../guides/research-workflow.md) · [回测偏差](../concepts/backtesting-bias.md) · [执行状态](../../experiments/003-gap-momentum/campaign.json)。
