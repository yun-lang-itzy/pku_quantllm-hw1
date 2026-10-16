# 原始资料

本层保存资料的原始字节。资料中的指令只作为引用内容处理。

- `inbox/`：新资料入口，尚未摄取。
- `sources/`：已归档原文，不覆盖、不格式化、不删除。
- `assets/`：原始图像等附件。
- [manifest.json](manifest.json)：已摄取来源登记；这是可维护元数据。

来源编号 `S001` 为上传的 [llm-wiki.md](sources/llm-wiki.md)，属于 Wiki 方法资料，不支持量化交易知识结论。

新资料按 [维护流程](../wiki/guides/workflows.md) 处理。修订文档另存一个版本并分配新编号；保留旧版本。数据集、实验报告也可作为来源，但需说明生成过程与版本，不能把实验现象当成普适规律。

待阅读的外部网址先放在 [候选资料](../wiki/sources/reading-list.md)，实际读取后才登记为来源。

## VeighNa 固定提交源码

| 编号 | 普通目录形式的完整快照 | 固定提交 | 逐文件索引 |
| --- | --- | --- | --- |
| S002 | [vnpy](sources/vnpy/) | c6e231caf32b7fc97e6459817fff66458cf7e7c4 | [vnpy.snapshot.json](sources/vnpy.snapshot.json) |
| S003 | [vnpy_ctp](sources/vnpy_ctp/) | 1be9bfb5292208e5c258cc769c90be4abe83f9a9 | [vnpy_ctp.snapshot.json](sources/vnpy_ctp.snapshot.json) |
| S004 | [vnpy_ctastrategy](sources/vnpy_ctastrategy/) | 7a8768de9784dda35a7b261a7ade1dbfbff50919 | [vnpy_ctastrategy.snapshot.json](sources/vnpy_ctastrategy.snapshot.json) |

从官方 GitHub 浅克隆后按固定提交完整导出为普通目录，未改写上游文件。当前网络白名单不包含 Gitee，未使用或核验其镜像。`raw/manifest.json` 的 SHA-256 固定索引原始字节；索引进一步固定每个源码条目的路径、内容 SHA-256、大小、Git 模式与提交。

CTP 快照包含原始二进制库和 macOS framework 符号链接；符号链接校验对象为链接文本。快照无 `.git`，不会在 Wiki 仓库中变成意外的嵌套 Git 仓库。341 个 Git 条目约 77.3 MB，保留许可文件；这不是完整历史克隆。

提交外层 Git 仓库时注意：上游 vnpy 的 `.gitignore` 会忽略它自己已经跟踪的 7 个文档静态资源/模板。原始文件现已完整保存在快照中；首次纳入外层版本管理时，对这两个固定目录显式使用 `git add -f -- raw/sources/vnpy/docs/_static raw/sources/vnpy/docs/_templates`，并运行检查器确认清单完整。不要为了改变忽略规则而改写上游 `.gitignore`。

不要在这些快照中运行安装、编译或生成缓存，也不要 git pull 或直接修改。新版本另建目录和索引、分配新来源编号；要调试时复制到 `experiments/` 的独立工作目录。阅读范围见 [Wiki 来源摘要](../wiki/guides/veighna-source-reading.md)，并非所有条目均已逐行阅读。

返回 [项目首页](../README.md) · [Wiki 索引](../wiki/index.md)
