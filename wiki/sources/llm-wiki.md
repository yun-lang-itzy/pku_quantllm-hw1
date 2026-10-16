---
title: "S001 · LLM Wiki 方法来源"
type: source
status: reviewed
created: 2026-10-16
updated: 2026-10-16
sources: ["S001"]
tags: ["source", "wiki-method"]
---

# S001 · LLM Wiki 方法来源

- 来源编号：`S001`
- 来源：用户上传的 `llm-wiki.md`；作者、原始发布日期和外部原址未提供。
- 摄取日期：2026-10-16（Asia/Shanghai）。
- 原始文件：[raw/sources/llm-wiki.md](../../raw/sources/llm-wiki.md)。
- 完整性：[manifest.json](../../raw/manifest.json) 保存原始字节的 SHA-256。
- 类型：知识库设计思路；已读取全文。

## 核心主张与定位

| 原文章节 | 主张 | 本项目采用方式 |
| --- | --- | --- |
| The core idea | 将零散资料编译成可持续积累、相互连接的 Wiki，减少重复综合 | 维护 `wiki/` 中的长期页面 |
| Architecture | 原始来源、可演化 Wiki、维护规范三层分开 | 使用 `raw/`、`wiki/`、`AGENTS.md` |
| Operations | 摄取时综合更新；问答可回写；定期检查矛盾和缺口 | [维护流程](../guides/workflows.md) |
| Indexing and logging | 内容索引与时间日志承担不同导航功能 | [索引](../index.md) 与 [日志](../log.md) |
| Optional: CLI tools / Note | 工具按需要选择，不要求复杂搜索或固定结构 | 先用相对 Markdown 链接、文本搜索与轻量检查器 |

## 采用的边界

原文是抽象方法说明，不是量化教材、工具安装要求或任何外部操作授权。原文提到 Obsidian、qmd、Marp、Dataview 等只是可选思路；本项目不依赖它们。

原文对维护成本和模型能力的乐观表述是作者观点，不是正确性保证。自动生成内容仍可能错引、遗漏或相互矛盾，因此本项目显式保留草稿状态、证据缺口和人工内容审阅。

## 与领域内容的关系

本来源只支持 Wiki 的组织与维护方法，不支持量化公式、交易规则或策略收益。量化系统起始框架由助手提出，等待后续资料与实验核验。

相关页面：[项目概览](../overview.md) · [维护规范](../../AGENTS.md)
