# vnpy_ctp 最小连接与行情 Demo

使用 `vnpy_ctp` 的底层 **TdApi / MdApi**，顺序完成交易前置连接、客户端认证、交易账号登录、行情前置登录、合约订阅和逐条行情打印。主程序见 [demo.py](demo.py)。

```text
TD init → onFrontConnected → reqAuthenticate
        → onRspAuthenticate → reqUserLogin → onRspUserLogin
        → 默认查询期货行情快照，按成交量选择合约（手动 --symbols 则跳过）
MD init → onFrontConnected → reqUserLogin → onRspUserLogin
        → subscribeMarketData → onRspSubMarketData
        → onRtnDepthMarketData → 打印 JSON
```

不需要 MainEngine、EventEngine、CtpGateway、CTA 或 GUI。这个程序没有报单、撤单或自动确认结算的逻辑。

在本机运行推荐从项目根目录使用 [run_ctp.py](../../run_ctp.py)：先执行 `python run_ctp.py --setup`，填写脚本旁的本地配置，再执行 `python run_ctp.py`。Windows 可使用 `py -3`，Linux/macOS 可使用 `python3`。完整说明见 [LOCAL_RUN.md](../../LOCAL_RUN.md)。该入口使用项目自己的 `.venv`，不依赖下面云环境验证所用的路径。

## 当前已准备的环境

当前云环境已在 `/workspace/work/ctp-demo/venv` 从 S003 固定提交编译安装 `vnpy_ctp 6.7.11.5`。账号配置保存在脚本旁的 `config.local.json`，该文件权限为 600，已被 Git 忽略；本文不重复密码或授权码。

从项目根目录可运行：

```bash
/workspace/work/ctp-demo/venv/bin/python experiments/002-ctp-demo/demo.py
```

**当前云环境没有到 SIMNOW 的 TCP 通道，尚未完成真实登录或接收行情。** 以上命令需要先具备到配置中 TD/MD 地址的网络连通性。TCP 代理探测在连接环境代理时即被拒绝，不能据此判断 SIMNOW 服务器是否在线。

**默认持续输出收到的行情，没有条数或时长上限，按 Ctrl+C 退出。** 休市或暂时没有新 tick 时会继续等待；不会生成模拟行情充数。连接、认证、登录、订阅等发生错误时仍会说明原因后退出。

不传 `--symbols` 时，程序在 TD 登录后发送 `reqQryDepthMarketData`（ProductClass='1'），在柜台实际返回的期货快照范围内按累计成交量排序，每个品种保留成交量最大的一个月份，最多选取 5 个合约。相同成交量按持仓量与代码确定顺序，跳过零成交、无效数值、期权和组合形式的代码。启动时打印 `[SELECT]` 的代码、成交量、持仓量和交易日，然后订阅。

柜台可能不支持全量快照查询。若查询报错、超时或没有正成交量的期货快照，程序会警告并使用 2026 年 10 月的候选池：

| 代码 | 品种 |
| --- | --- |
| rb2701 | 螺纹钢 |
| ag2612 | 白银 |
| au2612 | 黄金 |
| i2701 | 铁矿石 |
| m2701 | 豆粕 |

候选池只是常见流动性品种的备用月份，未经实时活跃度核验，也不保证服务器当前支持。自动排名来自当前柜台返回的快照，不是经独立数据源核验的全市场排名；收盘/休市时快照也不表示仍有实时成交。快照不足 5 个合格品种时只订阅实际选出的数量，不补造排名。

可手动覆盖并保持持续运行：

```bash
/workspace/work/ctp-demo/venv/bin/python experiments/002-ctp-demo/demo.py --symbols rb2701 ag2612 au2612 i2701 m2701
```

使用原始合约代码，不要带 `.SHFE` 等后缀。备用月份过期或柜台不支持时用此参数替换。

## 在自己的机器安装

需要 Python 3.10+。推荐单独虚拟环境，避免修改已有 VeighNa 环境。`requirements.txt` 固定到已阅读的源码提交，首次安装涉及 C++ 编译；Linux 需要 GCC/G++，Windows 需要相应 MSVC 工具链，macOS 需要 Xcode 工具链。

Linux/macOS，在项目根目录：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps -r experiments/002-ctp-demo/requirements.txt
.venv/bin/python experiments/002-ctp-demo/demo.py
```

Windows PowerShell：

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install --no-deps -r experiments/002-ctp-demo/requirements.txt
.venv\Scripts\python.exe experiments/002-ctp-demo/demo.py
```

也可以复用已经安装相同版本 `vnpy_ctp` 的环境。当前环境没有找到该版本可用的 Linux wheel，因此实际验证使用的是源码编译。

若使用已下载的源码而不再次克隆，应先把 `raw/sources/vnpy_ctp` 完整复制到 `work/vnpy_ctp-build`（保留符号链接），再用 `python -m pip install --no-deps ./work/vnpy_ctp-build`。不要直接在不可改写的 raw 快照中构建。

`--no-deps` 是有意使用的：Demo 根据已安装包的分发元数据直接加载 `vnctpmd` / `vnctptd` 扩展，避开包入口自动导入 Gateway 及 NumPy/TA-Lib 等依赖。这仍是同一套底层 API；若编写完整 VeighNa 应用，则应按官方方式安装完整依赖并使用 `from vnpy_ctp.api import MdApi, TdApi`。本 Demo 不改写、伪造或遮蔽 `vnpy_ctp` 包。

## 配置与参数

其他机器首次运行前，将 [config.example.json](config.example.json) 复制为 `config.local.json`，填入自己的 SIMNOW 账号、密码和授权码。UserID/BrokerID 必须保留为字符串，避免丢失前导零。

配置键对应用户提供的格式：`userid`、`password`、`brokerid`、`td_address`、`md_address`、`appid`、`auth_code`。附加 `production_mode` 是传给底层 CTP 创建 API 的布尔参数；本示例默认 false（测试模式），以所用柜台对合并版 CTP SDK 的要求为准，可在本地配置调整。

可用同名大写环境变量覆盖每个字符串字段，例如 `CTP_PASSWORD`、`CTP_AUTH_CODE`；不支持将密码直接放进命令行参数。密码和授权码会从程序日志中替换为 `***`，但本地配置与 SDK flow 文件仍需留在本机。

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `--config` | 脚本旁的 config.local.json | 本地配置文件 |
| `--symbols` | 自动选择 | 显式指定时跳过成交量查询，去重后订阅 |
| `--active-count` | 5 | 自动选择的不同品种数量（1–20）；备用池最多提供 5 个 |
| `--timeout` | 30 | TD 认证/登录、可选成交量查询、MD 登录/订阅各阶段超时；查询超时仅警告并继续 |
| `--duration` | 0 | 全部订阅确认后运行多久；0 表示持续运行 |
| `--max-ticks` | 0 | 打印 N 条行情后退出；0 表示不限 |
| `--flow-dir` | 脚本旁的 flow/ | 分为 td/ 和 md/，保存 CTP 本地流文件；建议使用 ASCII 路径 |

日常运行不要加 `--duration` 或 `--max-ticks`，它们只在显式设置时生效，供有界调试使用。例如临时测试可加 `--max-ticks 5`；这会打印 5 条后退出，**不是默认启动命令**。

按 Ctrl+C 退出。断线、认证失败、登录失败或订阅失败会退出并说明阶段，不会无限重试错误账号。可选的成交量查询失败只触发备用池，不导致退出。完整自动重连/续订阅属于后续扩展。

## 输出与成功判定

以下是**模拟格式示例，不是实际柜台回报**：

```text
[TD] 网络连接成功，发送客户端认证
[TD] 认证成功，发送账号登录
[TD] 登录成功，交易日=20261016
[MD] 网络连接成功，发送行情登录
[MD] 登录成功，发送合约订阅
[MD] 订阅成功: rb2701
[READY] 等待行情，按 Ctrl+C 退出；订阅成功不保证休市时有新行情
{"type":"tick","symbol":"rb2701","trading_day":"20261016","action_day":"20261015","time":"21:00:00","millisecond":500,"last_price":3500,"volume":100,"bid_price_1":3499,"bid_volume_1":3,"ask_price_1":3500,"ask_volume_1":5}
```

代码分别保留 TradingDay 与 ActionDay，不自行推导夜盘交易日。无效极大浮点价格、NaN 或缺失数值输出为 JSON `null`。网络连接、登录成功、订阅确认和收到行情是四个不同的检查点；未知/过期合约或休市可能导致有订阅响应却没有新 tick。

退出码：`0` 为按数量/时长正常结束且至少打印一条 tick；`1` 为配置、依赖、请求、回报、超时或资源释放错误；`2` 为到达运行时长但尚无 tick（也用于命令行参数错误）；`130` 为 Ctrl+C。

## 验证

不依赖 `vnpy_ctp`，也不访问网络的离线测试：

```bash
python3 -m unittest discover -s experiments/002-ctp-demo -p 'test_*.py' -v
```

28 个测试已通过，包括主链、拒绝认证、登录/订阅错误、返回非零、日期/无效报价、脱敏、超时、主线程清理与清理失败，以及默认参数不设退出限制、连续打印 8 条后继续运行、空闲等待、Ctrl+C 清理、成交量排序/品种去重、排名传递到订阅、查询失败/超时回退和晚到回报隔离。真实原生扩展也已编译、加载，并在仅本地回环的探测中完成 create/init/exit；这不等于 SIMNOW 登录已成功。

完整证据和限制见 [实验报告](report.md)；知识沉淀见 [Wiki 实践页](../../wiki/projects/ctp-minimal-demo.md)。
