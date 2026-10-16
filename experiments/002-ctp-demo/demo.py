#!/usr/bin/env python3
"""Read-only SIMNOW demo using vnpy_ctp's native Python MdApi and TdApi."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
from threading import Event, RLock
from time import monotonic
from typing import Callable
from urllib.parse import urlsplit


# October 2026 fallback candidates, not a live volume ranking. Prefer the
# cabinet's current futures depth snapshots to avoid stale delivery months.
FALLBACK_SYMBOLS = ('rb2701', 'ag2612', 'au2612', 'i2701', 'm2701')


def active_contracts(quotes: list[dict], count: int) -> list[dict]:
    """Rank positive-volume futures snapshots, retaining one month per product."""
    products: dict[str, dict] = {}
    for quote in quotes:
        symbol = quote.get('InstrumentID', '')
        match = re.fullmatch(r'([A-Za-z]+)\d{3,4}', symbol) if isinstance(symbol, str) else None
        volume = quote.get('Volume', 0)
        interest = quote.get('OpenInterest', 0)
        if not match or not isinstance(volume, (int, float)) or not math.isfinite(volume) or volume <= 0:
            continue
        if not isinstance(interest, (int, float)) or not math.isfinite(interest):
            interest = 0
        entry = {'symbol': symbol, 'volume': volume, 'open_interest': interest,
                 'trading_day': quote.get('TradingDay')}
        product = match[1].lower()
        previous = products.get(product)
        if previous is None or (volume, interest, symbol) > (previous['volume'], previous['open_interest'], previous['symbol']):
            products[product] = entry
    return sorted(products.values(), key=lambda entry: (-entry['volume'], -entry['open_interest'], entry['symbol']))[:count]


@dataclass(frozen=True)
class Settings:
    userid: str
    password: str = field(repr=False)
    brokerid: str
    td_address: str
    md_address: str
    appid: str
    auth_code: str = field(repr=False)
    production_mode: bool = False

    @classmethod
    def load(cls, path: Path) -> 'Settings':
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('配置必须是 JSON 对象')
        values = {}
        # Byte limits are the native char-array sizes minus the terminating NUL.
        limits = {'userid': 15, 'password': 40, 'brokerid': 10, 'appid': 32, 'auth_code': 16}
        for key in ('userid', 'password', 'brokerid', 'td_address', 'md_address', 'appid', 'auth_code'):
            value = os.environ.get(f'CTP_{key.upper()}', data.get(key, ''))
            if not isinstance(value, str) or not value or '\x00' in value:
                raise ValueError(f'配置字段 {key} 必须是非空字符串')
            if key in limits and (not value.isascii() or len(value) > limits[key]):
                raise ValueError(f'配置字段 {key} 必须为 ASCII，长度不超过 {limits[key]}')
            values[key] = value
        for key in ('td_address', 'md_address'):
            address = urlsplit(values[key])
            if (address.scheme != 'tcp' or not address.hostname or not address.port
                    or address.username or address.password or address.path
                    or address.query or address.fragment):
                raise ValueError(f'{key} 必须为 tcp://主机:端口')
        mode = data.get('production_mode', False)
        if not isinstance(mode, bool):
            raise ValueError('production_mode 必须为 JSON 布尔值')
        return cls(**values, production_mode=mode)


def load_native_api() -> tuple[type, type]:
    """Load the installed extensions without importing the optional Gateway stack.

    Importing vnpy_ctp.api normally first executes vnpy_ctp.__init__, which imports
    CtpGateway, vnpy.trader.utility and its NumPy/TA-Lib dependencies. Only the two
    native extensions are needed here. They are loaded from distribution metadata,
    never from the immutable source snapshot or an unverified download URL.
    """
    distribution = importlib.metadata.distribution('vnpy_ctp')
    folder = Path(distribution.locate_file('vnpy_ctp/api'))
    classes = []
    for name, class_name in (('vnctpmd', 'MdApi'), ('vnctptd', 'TdApi')):
        candidates = [folder / (name + suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES]
        extension = next((path for path in candidates if path.is_file()), None)
        if extension is None:
            raise ImportError(f'没有找到 {name} 原生扩展，请按 README 编译或安装 vnpy_ctp')
        spec = importlib.util.spec_from_file_location(name, extension)
        if spec is None or spec.loader is None:
            raise ImportError(f'无法加载 {name} 原生扩展')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        classes.append(getattr(module, class_name))
    return classes[0], classes[1]


class Session:
    def __init__(self, settings: Settings, symbols: list[str], max_ticks: int = 0,
                 output: Callable[[str], None] | None = None, active_count: int = 5) -> None:
        self.settings = settings
        self.symbols = symbols
        self.max_ticks = max_ticks
        self.output = output or (lambda text: print(text, flush=True))
        self.stop = Event()
        self.td_ready = Event()
        self.subscribed = Event()
        self.failed = False
        self.tick_count = 0
        self.accepted: set[str] = set()
        self.lock = RLock()
        self.active_count = active_count
        self.depth_quotes: dict[str, dict] = {}
        self.depth_ready = Event()
        self.depth_reqid: int | None = None
        self.depth_closed = False

    def log(self, text: str) -> None:
        with self.lock:
            for secret in (self.settings.password, self.settings.auth_code):
                text = text.replace(secret, '***')
            self.output(text)

    def fail(self, stage: str, reason: object) -> None:
        with self.lock:
            if self.stop.is_set():
                return
            self.failed = True
            self.log(f'[ERROR] {stage}: {reason}')
            self.stop.set()

    def check_response(self, stage: str, error: dict | None) -> bool:
        error = error or {}
        if error.get('ErrorID', 0):
            self.fail(stage, f"code={error['ErrorID']} {error.get('ErrorMsg', '')}")
            return False
        return not self.stop.is_set()

    def request(self, stage: str, function: Callable, *args: object) -> None:
        if self.stop.is_set():
            return
        try:
            result = function(*args)
            if result != 0:
                self.fail(stage, f'请求未成功发送，返回码={result}')
        except Exception as exc:
            self.fail(stage, f'{type(exc).__name__}: {exc}')

    def tick(self, data: dict) -> None:
        with self.lock:
            if self.stop.is_set() or data.get('InstrumentID') not in self.symbols:
                return
            def number(key: str) -> float | int | None:
                value = data.get(key)
                if not isinstance(value, (float, int)) or not math.isfinite(value) or abs(value) >= sys.float_info.max:
                    return None
                return value
            payload = {
                'type': 'tick', 'symbol': data.get('InstrumentID'),
                'trading_day': data.get('TradingDay'), 'action_day': data.get('ActionDay'),
                'time': data.get('UpdateTime'), 'millisecond': data.get('UpdateMillisec'),
                'last_price': number('LastPrice'), 'volume': number('Volume'),
                'bid_price_1': number('BidPrice1'), 'bid_volume_1': number('BidVolume1'),
                'ask_price_1': number('AskPrice1'), 'ask_volume_1': number('AskVolume1'),
            }
            self.log(json.dumps(payload, ensure_ascii=False, allow_nan=False))
            self.tick_count += 1
            if self.max_ticks and self.tick_count >= self.max_ticks:
                self.stop.set()


def build_clients(session: Session, md_type: type, td_type: type) -> tuple[object, object]:
    """Subclass the actual APIs; fake bases can be supplied for offline tests."""
    settings = session.settings

    class DemoTd(td_type):
        def onFrontConnected(self) -> None:
            session.log('[TD] 网络连接成功，发送客户端认证')
            self.reqid += 1
            session.request('TD 认证请求', self.reqAuthenticate, {
                'UserID': settings.userid, 'BrokerID': settings.brokerid,
                'AppID': settings.appid, 'AuthCode': settings.auth_code,
            }, self.reqid)

        def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
            if session.check_response('TD 认证', error) and last:
                session.log('[TD] 认证成功，发送账号登录')
                self.reqid += 1
                session.request('TD 登录请求', self.reqUserLogin, {
                    'UserID': settings.userid, 'BrokerID': settings.brokerid,
                    'Password': settings.password,
                }, self.reqid)

        def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
            if session.check_response('TD 登录', error) and last:
                session.log(f"[TD] 登录成功，交易日={data.get('TradingDay', '')}")
                session.td_ready.set()

        def onRspQryDepthMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
            with session.lock:
                if session.depth_closed or reqid != session.depth_reqid or session.stop.is_set():
                    return
                if error and error.get('ErrorID', 0):
                    session.log(f"[WARN] 成交量查询失败: code={error['ErrorID']} {error.get('ErrorMsg', '')}")
                    session.depth_ready.set()
                    return
                symbol = data.get('InstrumentID')
                if isinstance(symbol, str) and symbol:
                    session.depth_quotes[symbol] = dict(data)
                if last:
                    session.depth_ready.set()

        def onRspError(self, error: dict, reqid: int, last: bool) -> None:
            if reqid == session.depth_reqid:
                self.onRspQryDepthMarketData({}, error, reqid, True)
                return
            session.check_response('TD 异步错误', error)

        def onFrontDisconnected(self, reason: int) -> None:
            session.fail('TD 连接断开', reason)

    class DemoMd(md_type):
        def onFrontConnected(self) -> None:
            session.log('[MD] 网络连接成功，发送行情登录')
            self.reqid += 1
            session.request('MD 登录请求', self.reqUserLogin, {
                'UserID': settings.userid, 'BrokerID': settings.brokerid,
                'Password': settings.password,
            }, self.reqid)

        def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
            if session.check_response('MD 登录', error) and last:
                session.log('[MD] 登录成功，发送合约订阅')
                for symbol in session.symbols:
                    session.request(f'MD 订阅 {symbol}', self.subscribeMarketData, symbol)

        def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
            if not session.check_response('MD 订阅响应', error):
                return
            symbol = data.get('InstrumentID')
            if symbol in session.symbols:
                with session.lock:
                    session.accepted.add(symbol)
                    session.log(f'[MD] 订阅成功: {symbol}')
                    if session.accepted == set(session.symbols):
                        session.subscribed.set()

        def onRtnDepthMarketData(self, data: dict) -> None:
            session.tick(data)

        def onRspError(self, error: dict, reqid: int, last: bool) -> None:
            session.check_response('MD 异步错误', error)

        def onFrontDisconnected(self, reason: int) -> None:
            session.fail('MD 连接断开', reason)

    td, md = DemoTd(), DemoMd()
    for client in (td, md):
        client.reqid = 0
        client.created = False
        client.started = False
    return td, md


def open_client(client: object, kind: str, settings: Settings, flow_dir: Path) -> None:
    folder = (flow_dir / kind.lower()).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    path = str(folder) + os.sep
    if kind == 'TD':
        client.createFtdcTraderApi(path, settings.production_mode)
    else:
        client.createFtdcMdApi(path, settings.production_mode)
    client.created = True
    if kind == 'TD':
        client.subscribePrivateTopic(2)  # THOST_TERT_QUICK: only events after login
        client.subscribePublicTopic(2)
    address = settings.td_address if kind == 'TD' else settings.md_address
    client.registerFront(address)
    client.init()
    client.started = True


def wait_ready(session: Session, event: Event, stage: str, timeout: float, fatal: bool = True) -> bool:
    deadline = monotonic() + timeout
    while not event.is_set():
        if session.stop.wait(min(0.1, max(0, deadline - monotonic()))):
            return False
        if monotonic() >= deadline and not event.is_set():
            if fatal:
                session.fail(stage, '超时，请检查网络、柜台开放时段、配置或合约代码')
            else:
                session.log(f'[WARN] {stage}超时，使用已返回快照或候选合约继续订阅')
            return False
    return not session.failed


def choose_contracts(session: Session, td: object, timeout: float) -> bool:
    session.log(f'[SELECT] 查询柜台成交量，选取最多 {session.active_count} 个不同品种的期货合约')
    td.reqid += 1
    session.depth_reqid = td.reqid
    try:
        # THOST_FTDC_PC_Futures == '1'. Empty InstrumentID queries futures snapshots.
        result = td.reqQryDepthMarketData({'ProductClass': '1'}, td.reqid)
        if result == 0:
            wait_ready(session, session.depth_ready, '成交量查询', timeout, fatal=False)
        else:
            session.log(f'[WARN] 成交量查询未发送，返回码={result}')
    except Exception as exc:
        session.log(f'[WARN] 成交量查询不可用: {type(exc).__name__}: {exc}')
    with session.lock:
        session.depth_closed = True
        if session.stop.is_set():
            return False
        selected = active_contracts(list(session.depth_quotes.values()), session.active_count)
        if selected:
            session.symbols = [entry['symbol'] for entry in selected]
            for entry in selected:
                session.log('[SELECT] ' + json.dumps(entry, ensure_ascii=False))
        else:
            session.symbols = list(FALLBACK_SYMBOLS[:session.active_count])
            session.log('[WARN] 无可用的正成交量快照，使用 2026-10 候选池；未经实时活跃度核验，必要时用 --symbols 替换')
        session.log('[SUBSCRIBE] ' + ' '.join(session.symbols))
    return True


def serve(session: Session, td: object, md: object, flow_dir: Path,
          timeout: float, duration: float) -> int:
    open_client(td, 'TD', session.settings, flow_dir)
    if not wait_ready(session, session.td_ready, 'TD 认证/登录', timeout):
        return 1
    if not session.symbols and not choose_contracts(session, td, timeout):
        return 1
    open_client(md, 'MD', session.settings, flow_dir)
    if not wait_ready(session, session.subscribed, 'MD 登录/订阅', timeout):
        return 1 if session.failed or not session.tick_count else 0
    session.log('[READY] 等待行情，按 Ctrl+C 退出；订阅成功不保证休市时有新行情')
    deadline = monotonic() + duration if duration else None
    while not session.stop.wait(0.1):
        if deadline is not None and monotonic() >= deadline:
            break
    if session.failed:
        return 1
    if not session.tick_count:
        session.log('[INFO] 尚未收到行情，请检查交易时段与合约是否有效')
        return 2
    return 0


def run(session: Session, md_type: type, td_type: type, flow_dir: Path,
        timeout: float = 30, duration: float = 0) -> int:
    td, md = build_clients(session, md_type, td_type)
    result = 1
    try:
        result = serve(session, td, md, flow_dir, timeout, duration)
    except KeyboardInterrupt:
        session.log('[INFO] 用户停止')
        result = 130
    except Exception as exc:
        session.fail('运行异常', f'{type(exc).__name__}: {exc}')
    finally:
        # Native exit() joins the callback worker. Always close on the main thread,
        # never inside onRsp*/onRtn* (joining oneself would deadlock).
        session.stop.set()
        for kind, client in (('MD', md), ('TD', td)):
            try:
                if client.started:
                    client.exit()
                elif client.created:
                    client.release()
            except Exception as exc:
                session.log(f'[ERROR] {kind} 释放失败: {type(exc).__name__}: {exc}')
                result = 1
        session.log(f'[EXIT] 已打印行情: {session.tick_count} 条')
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument('--config', type=Path, default=here / 'config.local.json')
    parser.add_argument('--symbols', nargs='+', help='手动指定原始合约代码；默认按柜台成交量自动选取')
    parser.add_argument('--active-count', type=int, default=5, help='自动选择的不同品种合约数量，默认 5，最多 20')
    parser.add_argument('--flow-dir', type=Path, default=here / 'flow')
    parser.add_argument('--timeout', type=float, default=30, help='每个连接登录阶段的超时秒数')
    parser.add_argument('--duration', type=float, default=0, help='订阅就绪后运行秒数，0 表示持续运行')
    parser.add_argument('--max-ticks', type=int, default=0, help='打印 N 条行情后退出，0 表示不限')
    args = parser.parse_args(argv)
    if (not math.isfinite(args.timeout) or args.timeout <= 0
            or not math.isfinite(args.duration) or args.duration < 0 or args.max_ticks < 0):
        parser.error('timeout 必须为有限正数；duration 和 max-ticks 必须非负')
    if not 1 <= args.active_count <= 20:
        parser.error('active-count 必须在 1 到 20 之间')
    symbols = list(dict.fromkeys(args.symbols or []))
    if not all(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', symbol) for symbol in symbols):
        parser.error('symbols 只能包含原始合约代码，不带交易所后缀或空格')
    try:
        settings = Settings.load(args.config)
    except (OSError, ValueError) as exc:
        print(f'[ERROR] 无法读取有效配置: {type(exc).__name__}；请检查配置字段和本地文件', file=sys.stderr)
        return 1
    session = Session(settings, symbols, args.max_ticks, active_count=args.active_count)
    session.log(f'[RUN] {"自动选取合约" if not symbols else "手动合约: " + " ".join(symbols)}；'
                f'{"持续运行，按 Ctrl+C 退出" if not args.duration and not args.max_ticks else "按显式时长/条数限制运行"}')
    try:
        md_type, td_type = load_native_api()
    except (ImportError, OSError, RuntimeError) as exc:
        session.log(f'[ERROR] 原生扩展不可用: {type(exc).__name__}: {exc}；请按 README 安装')
        return 1
    return run(session, md_type, td_type, args.flow_dir, args.timeout, args.duration)


if __name__ == '__main__':
    raise SystemExit(main())
