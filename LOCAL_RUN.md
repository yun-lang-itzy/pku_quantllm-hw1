# 在本机运行量化学习项目

项目中的 Wiki 可以直接用编辑器或 Obsidian 打开；CTP Demo 使用本机 Python 和本机网络。入口是 [run_ctp.py](run_ctp.py)，不依赖 `/workspace`、云环境代理或云端虚拟环境。

## 获取项目

需要完整的项目目录，而不是只有初始 README 的 GitHub 版本。云工作区文件尚未提交/推送时，GitHub 不会自动出现这些文件；将修改发布到远程分支后，在本机下载/克隆该分支，或在 PR 合并后更新 main。

本地目录至少应能看到 `run_ctp.py`、`experiments/002-ctp-demo/demo.py`、`config.example.json` 和 `requirements.txt`。完整项目还包含 Wiki 和 `raw/sources/` 的固定源码快照。

`.gitattributes` 保留原始快照字节，避免 Windows Git 的换行转换破坏哈希。Windows 未启用符号链接时，Git 可能将 macOS framework 的链接签出为链接文本文件；检查器会核验其原始文本哈希，Windows CTP 构建不使用这些 macOS framework 别名。

## 准备环境

建议使用 64 位 Python 3.12，支持的最低版本为 3.10。源码安装需要 Git（仅从远程安装时）、网络和平台 C++ 编译工具：

- Windows：Visual Studio Build Tools 的 C++ 桌面开发工具与 Windows SDK。
- Linux：GCC/G++ 等基础构建工具，例如 Debian/Ubuntu 的 build-essential。
- macOS：Xcode Command Line Tools；使用与 Python 架构匹配的工具链。

安装程序会在项目根目录建立 `.venv`。有源码快照时，复制到 `work/` 的临时目录构建；不会在 raw 目录中编译。没有快照时按固定提交从官方仓库安装。构建依赖由 pip 的隔离构建安装。

## 安装与启动

Windows PowerShell，在项目根目录运行：

```powershell
py -3 run_ctp.py --setup
```

Linux/macOS：

```bash
python3 run_ctp.py --setup
```

首次安装会从示例创建 `experiments/002-ctp-demo/config.local.json`。在本机编辑它，填写用户编号、密码和授权码；账号字段使用字符串。已有配置会保留。该文件被 Git 忽略，因此从 GitHub 下载项目后需要自己填写；密码不要写进 Wiki 或运行命令。

配置完成后，Windows：

```powershell
py -3 run_ctp.py
```

Linux/macOS：

```bash
python3 run_ctp.py
```

默认按柜台成交量快照选择最多 5 个不同品种合约，持续打印真实行情，按 Ctrl+C 退出。查询不可用时会说明原因并使用文档中的候选池。可以手动覆盖，例如：

```bash
python run_ctp.py --symbols rb2701 ag2612 au2612 i2701 m2701
```

没有默认条数/时长上限。`--max-ticks`、`--duration` 只在显式传入时限制运行。完整参数与备用月份的适用边界见 [Demo 说明](experiments/002-ctp-demo/README.md)。

## 验证本机安装与网络

不连接服务器的原生扩展检查：

```bash
python run_ctp.py --verify
```

本机必须能出站连接到配置中的交易/行情 TCP 前置；在 Windows 可先执行：

```powershell
Test-NetConnection 182.254.243.31 -Port 30001
Test-NetConnection 182.254.243.31 -Port 30011
```

Linux/macOS 如已安装 nc：

```bash
nc -vz -w 5 182.254.243.31 30001
nc -vz -w 5 182.254.243.31 30011
```

端口可达后，依次核对 TD 登录、MD 登录、订阅确认和实际 tick。只看到网络连接或订阅成功不等于已经收到行情；还需要有效合约、柜台开放时段与正确账号/SDK 模式。

本机 macOS arm64 已完成适配编译、真实登录、自动选约、订阅及 5 条快照回调；午间没有后续更新，盘中持续行情仍待验证，Windows 尚未验证。详见 [报告](experiments/002-ctp-demo/report.md)。本机可直接执行 `.venv/bin/python run_ctp.py`，默认持续运行；系统 Python 3.9 无法使用此入口。macOS 构建自动应用 [适配脚本](scripts/prepare_ctp_macos.py)，仅修改临时副本，实际厂商 SDK 为 6.7.7，适配范围为当前 Demo。

## 离线检查

```bash
python -m unittest discover -s experiments/002-ctp-demo -p 'test_*.py' -v
python scripts/wiki_lint.py
```

测试不连接交易服务器。完整开发证据见 [实验报告](experiments/002-ctp-demo/report.md)。

交易扩展入口与最新验证结果见 [单次价格触发下单](experiments/002-ctp-demo/TRADING.md)。13:48 已补验 m2701 盘中持续行情与 dry-run；行情入口 `run_ctp.py` 不会下单。
