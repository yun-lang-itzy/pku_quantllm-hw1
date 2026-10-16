"""Offline trading tests; fake APIs never connect or send an external order."""
from datetime import datetime, timedelta
from pathlib import Path
import sys
from time import monotonic
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo
import trade_demo as trade
from test_demo import FakeApi, AutoTd, AutoMd


def settings():
    return demo.Settings('test', 'password', '9999', 'tcp://182.254.243.31:30001',
                         'tcp://182.254.243.31:30011', 'test', 'auth')


def quote(**changes):
    now = datetime.now(trade.SHANGHAI)
    result = dict(InstrumentID='m2701', LastPrice=101, AskPrice1=102, AskVolume1=10,
                  LowerLimitPrice=80, UpperLimitPrice=120,
                  TradingDay=now.strftime('%Y%m%d'), ActionDay=now.strftime('%Y%m%d'),
                  UpdateTime=now.strftime('%H:%M:%S'))
    result.update(changes)
    return result


INFO = dict(InstrumentID='m2701', ExchangeID='DCE', PriceTick=1, IsTrading=1,
            ProductClass='1', MinLimitOrderVolume=1, MaxLimitOrderVolume=100)


class Td(FakeApi):
    reqid = 0
    insert_result = 0
    cancel_result = 0

    def reqOrderInsert(self, req, reqid):
        self.calls.append(('insert', req, reqid))
        return self.insert_result

    def reqOrderAction(self, req, reqid):
        self.calls.append(('cancel', req, reqid))
        return self.cancel_result


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.s = trade.TradingSession(settings(), 'm2701', 100, True, self.logs.append)
        self.s.login = dict(FrontID=1, SessionID=2, MaxOrderRef='40', TradingDay=quote()['TradingDay'])
        self.s.instrument = INFO.copy()
        for event in (self.s.settled, self.s.instrument_ready, self.s.subscribed):
            event.set()
        self.td = Td()
        self.s.tick(quote())

    def calls(self, kind):
        return [call for call in self.td.calls if call[0] == kind]

    def order(self, **changes):
        data = dict(InstrumentID='m2701', OrderRef='41', FrontID=1, SessionID=2,
                    OrderSysID='abc', OrderStatus='3', VolumeTraded=0, VolumeTotal=1)
        data.update(changes)
        return data

    def test_strict_threshold_and_single_order(self):
        self.s.tick(quote(LastPrice=100))
        self.s.step(self.td)
        self.assertFalse(self.calls('insert'))
        for _ in range(50):
            self.s.tick(quote())
            self.s.step(self.td)
        self.assertEqual(len(self.calls('insert')), 1)
        req = self.calls('insert')[0][1]
        self.assertEqual((req['Direction'], req['CombOffsetFlag'], req['VolumeTotalOriginal'], req['LimitPrice']), ('0', '0', 1, 102))
        self.assertEqual(req['OrderRef'], '41')

    def test_dry_run_never_inserts_or_cancels(self):
        self.s.send = False
        self.s.step(self.td)
        self.s.step(self.td, monotonic() + 100)
        self.s.cancel(self.td)
        self.assertTrue(self.s.triggered)
        self.assertFalse(self.td.calls)
        self.assertTrue(any('[DRY-RUN]' in x for x in self.logs))

    def test_readiness_required(self):
        for event in (self.s.settled, self.s.instrument_ready, self.s.subscribed):
            event.clear()
            self.s.step(self.td)
            self.assertFalse(self.s.triggered)
            event.set()

    def test_invalid_quotes_never_trigger(self):
        for changes in [dict(AskPrice1=float('nan')), dict(AskPrice1=1.79e308),
                        dict(LastPrice=float('inf')), dict(AskVolume1=0),
                        dict(AskPrice1=121), dict(AskPrice1=102.5), dict(LowerLimitPrice=0),
                        dict(ActionDay='19990101'), dict(TradingDay='19990101'), dict(UpdateTime='bad')]:
            with self.subTest(changes=changes):
                self.s.tick(quote(**changes))
                self.s.step(self.td)
                self.assertFalse(self.s.triggered)

    def test_received_quote_expires(self):
        self.s.quote_received -= 6
        self.s.step(self.td)
        self.assertFalse(self.s.triggered)

    def test_cancel_once_after_ten_seconds(self):
        self.s.step(self.td)
        sent = self.s.sent_at
        self.s.step(self.td, sent + 9.9)
        self.assertFalse(self.calls('cancel'))
        self.s.step(self.td, sent + 10)
        self.s.step(self.td, sent + 11)
        self.assertEqual(len(self.calls('cancel')), 1)
        req = self.calls('cancel')[0][1]
        self.assertEqual((req['FrontID'], req['SessionID'], req['OrderRef']), (1, 2, '41'))
        self.assertFalse(self.s.terminal)  # request return != cancelled
        self.s.order(self.order(OrderStatus='5'))
        self.assertTrue(self.s.terminal)

    def test_terminal_never_regresses(self):
        self.s.step(self.td)
        self.s.order(self.order(OrderStatus='0'))
        self.s.order(self.order(OrderStatus='3'))
        self.s.step(self.td, self.s.sent_at + 20)
        self.assertTrue(self.s.terminal)
        self.assertFalse(self.calls('cancel'))

    def test_unrelated_order_ignored(self):
        self.s.step(self.td)
        self.s.order(self.order(SessionID=99, OrderStatus='0'))
        self.assertFalse(self.s.terminal)
        self.assertFalse(self.s.order_sysid)

    def test_trade_before_order_and_duplicate(self):
        self.s.step(self.td)
        data = dict(InstrumentID='m2701', OrderRef='41', OrderSysID='abc',
                    ExchangeID='DCE', TradingDay=quote()['TradingDay'], TradeID='t1', Price=102, Volume=1)
        self.s.trade(data)
        self.assertFalse(self.s.trades)
        self.s.order(self.order())
        self.s.trade(data)
        self.assertEqual(len(self.s.trades), 1)
        self.assertEqual(sum('[TRADE]' in x for x in self.logs), 1)
        self.assertTrue(self.s.terminal)

    def test_local_rejection_no_retry(self):
        self.td.insert_result = -1
        self.s.step(self.td)
        self.s.step(self.td)
        self.assertTrue(self.s.failed)
        self.assertEqual(len(self.calls('insert')), 1)
        self.assertFalse(self.calls('cancel'))

    def test_async_rejection(self):
        td, _ = trade.build_clients(self.s, FakeApi, Td)
        self.s.step(td)
        td.onErrRtnOrderInsert({'OrderRef':'41'}, {'ErrorID':31, 'ErrorMsg':'test rejection'})
        self.assertTrue(self.s.terminal)
        self.assertTrue(self.s.failed)

    def test_cancel_timeout_is_failure(self):
        self.s.step(self.td)
        self.s.step(self.td, self.s.sent_at + 10)
        self.s.step(self.td, self.s.sent_at + 25)
        self.assertTrue(self.s.failed)
        self.assertFalse(self.s.terminal)

    def test_cancel_reject_does_not_imply_terminal(self):
        self.td.cancel_result = -1
        self.s.step(self.td)
        self.s.cancel(self.td)
        self.assertTrue(self.s.failed)
        self.assertFalse(self.s.terminal)

    def test_contract_not_found(self):
        self.s.instrument = None
        td, _ = trade.build_clients(self.s, FakeApi, Td)
        td.onRspQryInstrument({}, {}, 1, True)
        self.assertTrue(self.s.failed)

    def test_exit_cancel_without_waiting_ten_seconds(self):
        self.s.step(self.td)
        self.s.cancel(self.td)
        self.assertEqual(len(self.calls('cancel')), 1)
        self.s.order(self.order(OrderStatus='5'))
        self.s.cancel(self.td)
        self.assertEqual(len(self.calls('cancel')), 1)

    def test_exchange_rejection_status(self):
        self.s.step(self.td)
        self.s.order(self.order(OrderSubmitStatus='4', StatusMsg='exchange rejection'))
        self.assertTrue(self.s.failed)
        self.assertTrue(self.s.terminal)

    def test_simnow_only_and_bad_threshold(self):
        for threshold in (float('nan'), float('inf'), 0, -1):
            with self.assertRaises(ValueError):
                trade.TradingSession(settings(), 'm2701', threshold)
        with self.assertRaises(ValueError):
            from dataclasses import replace
            trade.TradingSession(replace(settings(), brokerid='1234'), 'm2701', 100)


class FullTd(AutoTd):
    def reqUserLogin(self, req, reqid):
        self.onRspUserLogin(dict(FrontID=1, SessionID=2, MaxOrderRef='40', TradingDay=quote()['TradingDay']), {}, reqid, True)
        return 0

    def reqSettlementInfoConfirm(self, req, reqid):
        self.onRspSettlementInfoConfirm({}, {}, reqid, True)
        return 0

    def reqQryInstrument(self, req, reqid):
        self.onRspQryInstrument(INFO, {}, reqid, True)
        return 0


class FullMd(AutoMd):
    def subscribeMarketData(self, symbol):
        self.onRspSubMarketData({'InstrumentID':symbol}, {}, 1, True)
        self.onRtnDepthMarketData(quote())
        return 0


class LifecycleTests(unittest.TestCase):
    def test_full_dry_run_and_cleanup(self):
        logs = []
        s = trade.TradingSession(settings(), 'm2701', 100, output=logs.append)
        self.assertEqual(trade.run(s, FullMd, FullTd, duration=0.1), 0)
        self.assertTrue(s.triggered)
        self.assertIsNone(s.sent_at)
        self.assertTrue(any('[DRY-RUN]' in x for x in logs))

    def test_keyboard_interrupt_before_order(self):
        s = trade.TradingSession(settings(), 'm2701', 100, output=lambda _: None)
        with patch.object(s, 'step', side_effect=KeyboardInterrupt):
            self.assertEqual(trade.run(s, FullMd, FullTd), 130)
        self.assertIsNone(s.sent_at)


if __name__ == '__main__':
    unittest.main()
