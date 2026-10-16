#!/usr/bin/env python3
"""Single-shot SIMNOW buy-open demo; dry-run unless --send-order is explicit."""
from __future__ import annotations

import argparse
from datetime import datetime
import math
from pathlib import Path
import re
from threading import Event
from time import monotonic, sleep
from zoneinfo import ZoneInfo

import demo

HERE = Path(__file__).resolve().parent
SHANGHAI = ZoneInfo('Asia/Shanghai')
TERMINAL = {'0', '2', '4', '5'}  # filled, partial/not queued, not queued, cancelled


def positive(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and 0 < value < 1e100


class TradingSession(demo.Session):
    def __init__(self, settings, symbol, threshold, send=False, output=None):
        super().__init__(settings, [symbol], output=output)
        if not re.fullmatch(r'[A-Za-z]+\d{3,4}', symbol) or not positive(threshold):
            raise ValueError('需要有效期货合约和有限正数阈值')
        if (settings.production_mode or settings.brokerid != '9999'
                or settings.td_address != 'tcp://182.254.243.31:30001'
                or settings.md_address != 'tcp://182.254.243.31:30011'):
            raise ValueError('此教学入口仅允许当前 SIMNOW 仿真配置')
        self.threshold, self.send = threshold, send
        self.settled, self.instrument_ready = Event(), Event()
        self.instrument = None
        self.login = {}
        self.quote = None
        self.quote_received = 0.0
        self.triggered = False
        self.order_ref = ''
        self.sent_at = None
        self.cancel_at = None
        self.terminal = False
        self.order_sysid = ''
        self.trades = set()
        self.pending_trades = []
        self.stale_logged = False

    def tick(self, data):
        super().tick(data)
        with self.lock:
            if data.get('InstrumentID') == self.symbols[0]:
                self.quote = dict(data)
                self.quote_received = monotonic()

    def valid_quote(self, now):
        q = self.quote
        if not q or now - self.quote_received > 5:
            return False
        try:
            stamp = datetime.strptime(q['ActionDay'] + q['UpdateTime'], '%Y%m%d%H:%M:%S').replace(tzinfo=SHANGHAI)
            age = (datetime.now(SHANGHAI) - stamp).total_seconds()
        except (KeyError, TypeError, ValueError):
            return False
        if not -2 <= age <= 5 or q.get('TradingDay') != self.login.get('TradingDay'):
            if not self.stale_logged:
                self.log('[SKIP] 行情时间过旧或交易日不匹配，等待新行情')
                self.stale_logged = True
            return False
        price = q.get('AskPrice1')
        lower, upper = q.get('LowerLimitPrice'), q.get('UpperLimitPrice')
        if not all(positive(x) for x in (price, q.get('LastPrice'), lower, upper, q.get('AskVolume1'))):
            return False
        tick = self.instrument['PriceTick']
        return lower <= price <= upper and math.isclose(price / tick, round(price / tick), abs_tol=1e-6, rel_tol=0)

    def step(self, td, now=None):
        now = monotonic() if now is None else now
        with self.lock:
            if (not self.stop.is_set() and not self.triggered and self.settled.is_set()
                    and self.instrument_ready.is_set() and self.subscribed.is_set()
                    and self.valid_quote(now) and self.quote['LastPrice'] > self.threshold):
                self.triggered = True  # Latch BEFORE calling the API, including failures.
                self.order_ref = str(int(self.login.get('MaxOrderRef') or '0') + 1)
                if len(self.order_ref) > 12:
                    self.fail('报单编号', '超出 CTP OrderRef 长度')
                    return
                req = dict(InstrumentID=self.symbols[0], ExchangeID=self.instrument['ExchangeID'],
                           LimitPrice=self.quote['AskPrice1'], VolumeTotalOriginal=1,
                           OrderPriceType='2', Direction='0', CombOffsetFlag='0',
                           CombHedgeFlag='1', ContingentCondition='1', ForceCloseReason='0',
                           TimeCondition='3', VolumeCondition='1', MinVolume=1,
                           IsAutoSuspend=0, OrderRef=self.order_ref,
                           BrokerID=self.settings.brokerid, InvestorID=self.settings.userid,
                           UserID=self.settings.userid)
                self.log(f'[INTENT] 最新价 {self.quote["LastPrice"]} > {self.threshold}；'
                         f'{self.symbols[0]} 买入开仓 1 手，限价={req["LimitPrice"]}')
                if not self.send:
                    self.log('[DRY-RUN] 仅打印意图，未调用 reqOrderInsert；本次不再触发')
                    return
                self.sent_at = now
                td.reqid += 1
                result = td.reqOrderInsert(req, td.reqid)
                self.log(f'[INSERT] ref={self.order_ref} 请求返回={result}；返回 0 不代表成交')
                if result:
                    self.terminal = True  # Locally rejected; no automatic retry.
                    self.fail('报单发送', result)
            if self.sent_at is not None and not self.terminal:
                if self.cancel_at is None and now - self.sent_at >= 10:
                    self.cancel(td, now)
                elif self.cancel_at is not None and now - self.cancel_at >= 15:
                    self.fail('撤单确认超时', '委托状态未知，请在柜台核对；不自动重报')

    def cancel(self, td, now=None):
        with self.lock:
            if self.sent_at is None or self.terminal or self.cancel_at is not None:
                return
            self.cancel_at = monotonic() if now is None else now
            td.reqid += 1
            req = dict(InstrumentID=self.symbols[0], ExchangeID=self.instrument['ExchangeID'],
                       OrderRef=self.order_ref, FrontID=self.login['FrontID'],
                       SessionID=self.login['SessionID'], ActionFlag='0',
                       BrokerID=self.settings.brokerid, InvestorID=self.settings.userid)
            result = td.reqOrderAction(req, td.reqid)
            self.log(f'[CANCEL] 申请撤单，返回={result}；以委托回报确认结果')
            if result:
                self.fail('撤单发送', f'{result}；委托可能仍有效，请在柜台核对')

    def owns_order(self, data):
        return (self.sent_at is not None and data.get('InstrumentID') == self.symbols[0]
                and data.get('OrderRef') == self.order_ref
                and data.get('FrontID') == self.login.get('FrontID')
                and data.get('SessionID') == self.login.get('SessionID'))

    def order(self, data):
        with self.lock:
            if not self.owns_order(data):
                return
            self.order_sysid = data.get('OrderSysID', '').strip() or self.order_sysid
            status = data.get('OrderStatus')
            self.log(f'[ORDER] ref={self.order_ref} status={status} '
                     f'成交={data.get("VolumeTraded")} 剩余={data.get("VolumeTotal")} '
                     f'{data.get("StatusMsg", "")}')
            if status in TERMINAL or data.get('OrderSubmitStatus') == '4':
                self.terminal = True
            if data.get('OrderSubmitStatus') == '4':
                self.fail('报单拒绝', data.get('StatusMsg', '柜台拒单'))
            pending, self.pending_trades = self.pending_trades, []
            for trade in pending:
                self.trade(trade)

    def trade(self, data):
        with self.lock:
            if (self.sent_at is None or data.get('InstrumentID') != self.symbols[0]
                    or data.get('OrderRef') != self.order_ref
                    or data.get('ExchangeID') != self.instrument['ExchangeID']):
                return
            if not self.order_sysid:
                self.pending_trades.append(dict(data))
                return
            if data.get('OrderSysID', '').strip() != self.order_sysid:
                return
            key = (data.get('TradingDay'), data.get('ExchangeID'), data.get('TradeID'))
            if key not in self.trades:
                self.trades.add(key)
                if data.get('Volume', 0) >= 1:
                    self.terminal = True
                self.log(f'[TRADE] {self.symbols[0]} 买入开仓 '
                         f'价格={data.get("Price")} 手数={data.get("Volume")}；不会自动平仓')


def build_clients(session, md_type, td_type):
    base_td, md = demo.build_clients(session, md_type, td_type)

    class TradeTd(type(base_td)):
        def onRspUserLogin(self, data, error, reqid, last):
            if not error.get('ErrorID') and last:
                session.login = dict(data)
            super().onRspUserLogin(data, error, reqid, last)

        def onRspSettlementInfoConfirm(self, data, error, reqid, last):
            if session.check_response('结算确认', error) and last:
                session.log('[TD] 结算确认成功')
                session.settled.set()

        def onRspQryInstrument(self, data, error, reqid, last):
            if not session.check_response('合约查询', error):
                return
            if data.get('InstrumentID') == session.symbols[0]:
                session.instrument = dict(data)
            if last:
                info = session.instrument
                if (not info or info.get('ProductClass') != '1' or not info.get('IsTrading')
                        or not info.get('ExchangeID') or not positive(info.get('PriceTick'))
                        or not info.get('MinLimitOrderVolume', 0) <= 1 <= info.get('MaxLimitOrderVolume', 0)):
                    session.fail('合约校验', '未找到可交易且允许 1 手限价单的期货合约')
                else:
                    session.log(f'[TD] 合约确认 {session.symbols[0]} '
                                f'{info["ExchangeID"]} 最小变动价位={info["PriceTick"]}')
                    session.instrument_ready.set()

        def onRtnOrder(self, data):
            session.order(data)

        def onRtnTrade(self, data):
            session.trade(data)

        def onRspOrderInsert(self, data, error, reqid, last):
            if data.get('OrderRef') == session.order_ref and error.get('ErrorID'):
                session.terminal = True
                session.fail('报单拒绝', f'{error.get("ErrorID")} {error.get("ErrorMsg")}')

        def onErrRtnOrderInsert(self, data, error):
            self.onRspOrderInsert(data, error, 0, True)

        def onRspOrderAction(self, data, error, reqid, last):
            if error.get('ErrorID'):
                session.fail('撤单拒绝', f'{error.get("ErrorID")} {error.get("ErrorMsg")}；需核对委托')

        def onErrRtnOrderAction(self, data, error):
            self.onRspOrderAction(data, error, 0, True)

    td = TradeTd()
    td.reqid, td.created, td.started = 0, False, False
    return td, md


def run(session, md_type, td_type, duration=0):
    td, md = build_clients(session, md_type, td_type)
    result = 1
    try:
        demo.open_client(td, 'TD', session.settings, HERE / 'flow/trade')
        if not demo.wait_ready(session, session.td_ready, 'TD 登录', 30):
            return 1
        td.reqid += 1
        session.request('结算确认', td.reqSettlementInfoConfirm,
                        dict(BrokerID=session.settings.brokerid, InvestorID=session.settings.userid), td.reqid)
        if not demo.wait_ready(session, session.settled, '结算确认', 30):
            return 1
        td.reqid += 1
        session.request('合约查询', td.reqQryInstrument, dict(InstrumentID=session.symbols[0]), td.reqid)
        if not demo.wait_ready(session, session.instrument_ready, '合约查询', 30):
            return 1
        demo.open_client(md, 'MD', session.settings, HERE / 'flow/trade')
        if not demo.wait_ready(session, session.subscribed, '行情订阅', 30):
            return 1
        session.log('[READY] 等待最新价超过阈值；Ctrl+C 退出')
        start = monotonic()
        while not session.stop.wait(0.05):
            session.step(td)
            if duration and monotonic() - start >= duration:
                break
        result = 1 if session.failed else 0
    except KeyboardInterrupt:
        session.log('[STOP] 用户停止')
        result = 130
    except Exception as exc:
        session.fail('运行异常', f'{type(exc).__name__}: {exc}')
    finally:
        # Stop new signals first, but keep callbacks alive for cancellation ack.
        try:
            session.cancel(td)
            end = monotonic() + 15
            while session.sent_at is not None and not session.terminal and monotonic() < end:
                sleep(0.05)
            if session.sent_at is not None and not session.terminal:
                session.log('[UNRESOLVED] 未确认撤单/成交终态，请在柜台核对；退出不会自动撤销委托')
                result = 1
        except (Exception, KeyboardInterrupt) as exc:
            session.log(f'[UNRESOLVED] 清理中断 {type(exc).__name__}；请在柜台核对委托')
            result = 1
        session.stop.set()
        for client in (md, td):
            try:
                if client.started:
                    client.exit()
                elif client.created:
                    client.release()
            except Exception as exc:
                session.log(f'[ERROR] API 释放失败：{type(exc).__name__}')
                result = 1
        session.log(f'[EXIT] 行情={session.tick_count}；触发={session.triggered}；实际报单尝试={session.sent_at is not None}')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--threshold', type=float, required=True)
    parser.add_argument('--send-order', action='store_true', help='显式允许 SIMNOW 仿真报单；默认只打印意图')
    parser.add_argument('--duration', type=float, default=0, help='0 持续运行；退出时尝试撤销本次未完成委托')
    parser.add_argument('--config', type=Path, default=HERE / 'config.local.json')
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration 必须是有限非负数')
    try:
        session = TradingSession(demo.Settings.load(args.config), args.symbol, args.threshold, args.send_order)
        md_type, td_type = demo.load_native_api()
    except (ValueError, OSError, ImportError) as exc:
        parser.error(f'配置或环境不可用：{type(exc).__name__}')
    session.log(f'[MODE] {"SIMNOW 实际报单" if args.send_order else "DRY-RUN 不发送委托"}；'
                f'{args.symbol} 最新价 > {args.threshold}；买入开仓 1 手，10 秒未完成申请撤单')
    return run(session, md_type, td_type, args.duration)


if __name__ == '__main__':
    raise SystemExit(main())
