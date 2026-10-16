# pku_quantllm-hw1 · 量化交易系统开发学习 Wiki

一个按 LLM Wiki 思路组织的学习项目：原始资料保留原样，知识在 Markdown 页面中持续积累，每次整理都有出处、交叉链接和日志。

本机运行入口：先按 [本地运行说明](LOCAL_RUN.md) 准备 Python/C++ 环境，执行 `python run_ctp.py --setup`，填写本地配置后执行 `python run_ctp.py`。默认持续打印行情，按 Ctrl+C 退出。

## 从这里开始

1. 打开 [Wiki 索引](wiki/index.md)，了解已有内容。
2. 阅读 [学习路线](wiki/roadmap.md)，从第一阶段的验收任务开始。
3. 在 [学习看板](wiki/learning-dashboard.md) 记录实际进度。
4. 阅读 [VeighNa 三模块源码学习入口](wiki/guides/veighna-source-reading.md)，沿调用链理解事件、订单和回测。
5. 新资料放入 `raw/inbox/`，再让助手按 [维护流程](wiki/guides/workflows.md) 整理。
6. 运行 [底层 CTP 最小 Demo](experiments/002-ctp-demo/README.md)，理解异步认证、登录、订阅和行情回调。

可以直接用编辑器阅读，也可以将本项目目录作为 Obsidian 仓库打开。全部使用相对 Markdown 链接，无须插件、数据库或网站服务。

## 目录

```text
.
├── AGENTS.md                 # 后续助手的项目规范
├── raw/                      # 不改写的原始资料与哈希登记
│   ├── inbox/                # 待处理资料
│   ├── sources/              # 已归档原文、源码快照及逐文件哈希索引
│   ├── assets/               # 原始图像等附件
│   └── manifest.json         # 来源编号、路径、SHA-256
├── wiki/
│   ├── index.md              # 内容总入口
│   ├── log.md                # 只追加的维护记录
│   ├── overview.md           # 学习目标与边界
│   ├── roadmap.md            # 分阶段路线与验收条件
│   ├── learning-dashboard.md # 进度和学习记录
│   ├── open-questions.md     # 待确认问题、冲突和缺口
│   ├── glossary.md           # 起始术语表
│   ├── concepts/             # 概念草稿与有出处的源码实例
│   ├── modules/              # VeighNa 三模块源码导读
│   ├── guides/               # 维护与研究流程
│   ├── projects/             # 实践项目规格
│   └── sources/              # 来源摘要、候选阅读资料
├── templates/                # 来源、概念、问答、实验模板
├── experiments/              # 后续实验代码和运行记录
├── scripts/wiki_lint.py      # 无第三方依赖的结构检查
└── Makefile
```

## 当前知识状态

已登记四个来源：**S001** 是上传的 Wiki 方法文档；**S002–S004** 为官方 `vnpy`、`vnpy_ctp`、`vnpy_ctastrategy` 的固定提交源码快照，存放在 `raw/sources/`。完成了核心路径静态阅读，详细已读/未读范围见各来源摘要。

[源码学习入口](wiki/guides/veighna-source-reading.md) 汇总模块职责、事件/订单链路和实盘与回测差异。原有通用概念仍保留草稿状态，其中新增的 VeighNa 实例有就近源码引用。

新增的 [CTP Demo](experiments/002-ctp-demo/README.md) 默认按柜台成交量选择合约并持续打印，按 Ctrl+C 退出；已在隔离环境完成原生扩展构建和 28 个离线测试，本机 macOS 已验证真实 SIMNOW 登录、自动选约、订阅和 5 条快照回调；已补验盘中 m2701 连续 41 条行情，见 [联调报告](experiments/002-ctp-demo/report.md)。未运行完整平台、上游测试套件或回测。

学习默认起点为 Python、日频、单资产、无杠杆的离线实验；市场、经验水平和实际学习节奏见 [待确认问题](wiki/open-questions.md)。这只是可调整的学习安排。

## 常用请求

```text
请摄取 raw/inbox/ 中的 xxx.md：保留原文，登记来源，更新摘要、相关概念、索引、问题清单和日志，然后运行检查。
请基于现有 Wiki 解释“为什么收盘价信号不能直接按同一收盘价成交”，给出引用，并将有价值的结论保存到 Wiki。
请对 Wiki 做一次 lint：检查断链、孤立页、来源、过时内容和相互矛盾的结论，记录未解决的问题。
请按学习路线带我完成第一阶段，并把实际完成的练习记录到学习看板。
```

## 检查与搜索

需要 Python 3.10+；无依赖安装步骤。在本项目根目录运行：

```bash
python3 scripts/wiki_lint.py
# 或
make check

# CTP Demo 的离线测试，不连接网络
make test

# 如果已安装 ripgrep
rg -n '前视|滑点|风险' wiki
```

检查器验证本地文件链接、Wiki 目录覆盖、孤立页面、元数据、来源编号与原文哈希；源码快照还逐条核验文件内容、符号链接文本与条目清单。内容是否正确、结论是否矛盾、外部链接是否可访问，仍需实际阅读和核验。详细约定见 [AGENTS.md](AGENTS.md)。

交易扩展：[单次价格触发下单](experiments/002-ctp-demo/TRADING.md)，默认只打印意图；已验证结算确认、合约查询和单次触发，实际仿真委托待确认参数后联调。
