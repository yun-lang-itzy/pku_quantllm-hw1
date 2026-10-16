"""Offline protocol tests: no native dependency and no network connection."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread, get_ident
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import demo
import run_ctp


def settings():
    return demo.Settings('test-user', 'test-password', '9999',
                         'tcp://127.0.0.1:30001', 'tcp://127.0.0.1:30011',
                         'test-app', 'test-auth', False)


class FakeApi:
    instances = []

    def __init__(self):
        self.calls = []
        self.exit_thread = None
        self.__class__.instances.append(self)

    def createFtdcTraderApi(self, path, mode):
        self.calls.append(('create_td', path, mode))

    def createFtdcMdApi(self, path, mode):
        self.calls.append(('create_md', path, mode))

    def subscribePrivateTopic(self, mode):
        self.calls.append(('private', mode))

    def subscribePublicTopic(self, mode):
        self.calls.append(('public', mode))

    def registerFront(self, address):
        self.calls.append(('front', address))

    def init(self):
        self.calls.append(('init',))

    def reqAuthenticate(self, request, reqid):
        self.calls.append(('auth', request, reqid))
        return 0

    def reqUserLogin(self, request, reqid):
        self.calls.append(('login', request, reqid))
        return 0

    def subscribeMarketData(self, symbol):
        self.calls.append(('subscribe', symbol))
        return 0

    def exit(self):
        self.exit_thread = get_ident()
        self.calls.append(('exit',))

    def release(self):
        self.calls.append(('release',))


class AutoTd(FakeApi):
    instances = []

    def init(self):
        super().init()
        self.onFrontConnected()

    def reqAuthenticate(self, request, reqid):
        result = super().reqAuthenticate(request, reqid)
        self.onRspAuthenticate({}, {}, reqid, True)
        return result

    def reqUserLogin(self, request, reqid):
        result = super().reqUserLogin(request, reqid)
        self.onRspUserLogin({'TradingDay': '20261016'}, {}, reqid, True)
        return result


class AutoMd(FakeApi):
    instances = []

    def init(self):
        super().init()
        self.onFrontConnected()

    def reqUserLogin(self, request, reqid):
        result = super().reqUserLogin(request, reqid)
        self.onRspUserLogin({}, {}, reqid, True)
        return result

    def subscribeMarketData(self, symbol):
        result = super().subscribeMarketData(symbol)
        self.onRspSubMarketData({'InstrumentID': symbol}, {}, 1, True)
        self.onRtnDepthMarketData({'InstrumentID': symbol, 'LastPrice': 100.5})
        return result


class QuietMd(AutoMd):
    instances = []

    def subscribeMarketData(self, symbol):
        self.calls.append(('subscribe', symbol))
        self.onRspSubMarketData({'InstrumentID': symbol}, {}, 1, True)
        return 0


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.lines = []
        self.session = demo.Session(settings(), ['rb2701', 'au2612'], output=self.lines.append)
        self.td, self.md = demo.build_clients(self.session, FakeApi, FakeApi)

    def test_td_authentication_precedes_login_and_login_confirmation(self):
        self.td.onFrontConnected()
        self.assertEqual([call[0] for call in self.td.calls], ['auth'])
        self.assertFalse(self.session.td_ready.is_set())
        self.td.onRspAuthenticate({}, {}, 1, False)
        self.assertEqual(len(self.td.calls), 1)
        self.td.onRspAuthenticate({}, {}, 1, True)
        self.assertEqual([call[0] for call in self.td.calls], ['auth', 'login'])
        self.assertEqual([call[2] for call in self.td.calls], [1, 2])
        self.td.onRspUserLogin({}, {}, 2, True)
        self.assertTrue(self.session.td_ready.is_set())

    def test_authentication_failure_stops_without_login_or_close_in_callback(self):
        self.td.onRspAuthenticate({}, {'ErrorID': 63, 'ErrorMsg': 'denied'}, 1, True)
        self.assertTrue(self.session.failed)
        self.assertTrue(self.session.stop.is_set())
        self.assertEqual(self.td.calls, [])
        self.assertIsNone(self.td.exit_thread)

    def test_md_subscribes_only_after_login_and_requires_each_ack(self):
        self.md.onFrontConnected()
        self.assertEqual([x[0] for x in self.md.calls], ['login'])
        self.md.onRspUserLogin({}, {}, 1, True)
        self.assertEqual([x[1] for x in self.md.calls if x[0] == 'subscribe'], ['rb2701', 'au2612'])
        self.assertFalse(self.session.subscribed.is_set())
        self.md.onRspSubMarketData({'InstrumentID': 'rb2701'}, {}, 1, False)
        self.assertFalse(self.session.subscribed.is_set())
        self.md.onRspSubMarketData({'InstrumentID': 'au2612'}, {}, 1, True)
        self.assertTrue(self.session.subscribed.is_set())

    def test_login_and_subscription_errors_stop_session(self):
        for callback in (self.md.onRspUserLogin, self.md.onRspSubMarketData):
            with self.subTest(callback=callback.__name__):
                current = demo.Session(settings(), ['rb2701'], output=lambda text: None)
                _, md = demo.build_clients(current, FakeApi, FakeApi)
                getattr(md, callback.__name__)({}, {'ErrorID': 3, 'ErrorMsg': 'invalid'}, 1, True)
                self.assertTrue(current.failed)
                self.assertFalse(current.subscribed.is_set())

    def test_request_send_failure_does_not_wait_as_if_successful(self):
        self.session.request('send', lambda: -2)
        self.assertTrue(self.session.failed)
        self.assertIn('返回码=-2', self.lines[-1])

    def test_callback_logs_redact_password_and_auth_code(self):
        self.td.onRspError({'ErrorID': 1, 'ErrorMsg': 'test-password / test-auth'}, 1, True)
        text='\n'.join(self.lines)
        self.assertNotIn('test-password', text)
        self.assertNotIn('test-auth', text)
        self.assertNotIn('test-password', repr(settings()))
        self.assertNotIn('test-auth', repr(settings()))

    def test_tick_json_keeps_dates_and_normalizes_invalid_quotes(self):
        self.md.onRtnDepthMarketData({
            'InstrumentID': 'rb2701', 'TradingDay': '20261016', 'ActionDay': '20261015',
            'UpdateTime': '21:00:00', 'UpdateMillisec': 500, 'LastPrice': 100,
            'BidPrice1': sys.float_info.max, 'AskPrice1': float('nan'), 'Volume': 12,
        })
        tick=json.loads(self.lines[-1])
        self.assertEqual(tick['trading_day'], '20261016')
        self.assertEqual(tick['action_day'], '20261015')
        self.assertEqual(tick['last_price'], 100)
        self.assertIsNone(tick['bid_price_1'])
        self.assertIsNone(tick['ask_price_1'])
        self.assertEqual(self.session.tick_count, 1)

    def test_max_ticks_limits_output_and_ignores_unrequested_instruments(self):
        self.session.max_ticks=1
        self.md.onRtnDepthMarketData({'InstrumentID': 'not-requested'})
        self.assertEqual(self.session.tick_count, 0)
        for _ in range(2):
            self.md.onRtnDepthMarketData({'InstrumentID': 'rb2701', 'LastPrice': 101})
        self.assertEqual(self.session.tick_count, 1)
        self.assertTrue(self.session.stop.is_set())

    def test_disconnect_requests_main_thread_shutdown(self):
        self.md.onFrontDisconnected(0x1001)
        self.assertTrue(self.session.stop.is_set())
        self.assertTrue(self.session.failed)
        self.assertIsNone(self.md.exit_thread)

    def test_open_initializes_topics_and_separate_flow_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            demo.open_client(self.td, 'TD', settings(), Path(folder))
            demo.open_client(self.md, 'MD', settings(), Path(folder))
            self.assertTrue((Path(folder)/'td').is_dir())
            self.assertTrue((Path(folder)/'md').is_dir())
        self.assertEqual([x[0] for x in self.td.calls], ['create_td', 'private', 'public', 'front', 'init'])
        self.assertEqual(self.td.calls[1:3], [('private',2), ('public',2)])
        self.assertFalse(self.td.calls[0][2])

    def test_timeout_releases_started_td_without_starting_md(self):
        FakeApi.instances=[]
        with tempfile.TemporaryDirectory() as folder:
            code=demo.run(self.session, FakeApi, FakeApi, Path(folder), timeout=0.001)
        td,md=FakeApi.instances
        self.assertEqual(code, 1)
        self.assertEqual(td.exit_thread, get_ident())
        self.assertFalse(md.started)
        self.assertEqual(md.calls, [])

    def test_whole_happy_path_prints_tick_and_closes_both_on_main_thread(self):
        AutoTd.instances=[]
        AutoMd.instances=[]
        session=demo.Session(settings(), ['rb2701'], max_ticks=1, output=self.lines.append)
        with tempfile.TemporaryDirectory() as folder:
            code=demo.run(session, AutoMd, AutoTd, Path(folder))
        self.assertEqual(code, 0)
        self.assertEqual(session.tick_count, 1)
        self.assertEqual(AutoTd.instances[-1].exit_thread, get_ident())
        self.assertEqual(AutoMd.instances[-1].exit_thread, get_ident())

    def test_duration_without_ticks_is_distinguished_from_tick_success(self):
        class QuietMd(AutoMd):
            def subscribeMarketData(self,symbol):
                self.onRspSubMarketData({'InstrumentID':symbol}, {}, 1, True)
                return 0
        with tempfile.TemporaryDirectory() as folder:
            code=demo.run(demo.Session(settings(), ['rb2701'], output=self.lines.append),
                          QuietMd, AutoTd, Path(folder), duration=0.001)
        self.assertEqual(code, 2)

    def test_cleanup_failure_is_reported_and_does_not_skip_other_client(self):
        class BrokenExitMd(AutoMd):
            def exit(self):
                raise RuntimeError('test cleanup failure')
        AutoTd.instances=[]
        current=demo.Session(settings(), ['rb2701'], max_ticks=1, output=self.lines.append)
        with tempfile.TemporaryDirectory() as folder:
            code=demo.run(current, BrokenExitMd, AutoTd, Path(folder))
        self.assertEqual(code, 1)
        self.assertEqual(AutoTd.instances[-1].exit_thread, get_ident())
        self.assertTrue(any('释放失败' in line for line in self.lines))

    def test_json_keeps_leading_zero_id_and_environment_can_supply_password(self):
        values=settings().__dict__.copy()
        values['userid']='000123'
        values['password']=''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json'
            path.write_text(json.dumps(values))
            with patch.dict(os.environ, {'CTP_PASSWORD':'environment-secret'}):
                result=demo.Settings.load(path)
        self.assertEqual(result.userid, '000123')
        self.assertEqual(result.password, 'environment-secret')

    def test_configuration_rejects_numeric_ids_and_invalid_mode(self):
        for key,value in [('userid',123), ('production_mode','false')]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                values=settings().__dict__.copy()
                values[key]=value
                path=Path(folder)/'config.json'
                path.write_text(json.dumps(values))
                with self.assertRaises(ValueError):
                    demo.Settings.load(path)

    def test_main_rejects_exchange_suffix_before_loading_native_extensions(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            demo.main(['--symbols','rb2701.SHFE'])
        self.assertEqual(error.exception.code, 2)

    def test_default_cli_selects_automatically_without_tick_or_duration_limit(self):
        with (patch.object(demo.Settings, 'load', return_value=settings()),
              patch.object(demo, 'load_native_api', return_value=(FakeApi, FakeApi)),
              patch.object(demo, 'run', return_value=0) as run,
              contextlib.redirect_stdout(io.StringIO())):
            self.assertEqual(demo.main([]), 0)
        session = run.call_args.args[0]
        self.assertEqual(session.symbols, [])
        self.assertEqual(session.active_count, 5)
        self.assertEqual(session.max_ticks, 0)
        self.assertEqual(run.call_args.args[-1], 0)

    def test_active_selection_ranks_volume_and_retains_distinct_products(self):
        quotes = [
            {'InstrumentID': 'rb2705', 'Volume': 4000, 'OpenInterest': 50},
            {'InstrumentID': 'rb2701', 'Volume': 6000, 'OpenInterest': 100},
            {'InstrumentID': 'ag2612', 'Volume': 5000},
            {'InstrumentID': 'au2612', 'Volume': 3000},
            {'InstrumentID': 'i2701', 'Volume': 2000},
            {'InstrumentID': 'TA701', 'Volume': 1000},
            {'InstrumentID': 'm2701', 'Volume': 500},
            {'InstrumentID': 'rb2701C3500', 'Volume': 99999},
            {'InstrumentID': 'SP rb2701&rb2705', 'Volume': 99999},
            {'InstrumentID': 'cu2611', 'Volume': 0},
            {'InstrumentID': 'al2611', 'Volume': float('nan')},
        ]
        result = demo.active_contracts(quotes, 5)
        self.assertEqual([row['symbol'] for row in result], ['rb2701', 'ag2612', 'au2612', 'i2701', 'TA701'])

    def test_auto_selected_contracts_reach_md_subscriptions(self):
        class QuoteTd(AutoTd):
            def reqQryDepthMarketData(self, request, reqid):
                self.calls.append(('depth', request, reqid))
                self.onRspQryDepthMarketData({'InstrumentID': 'rb2701', 'Volume': 500}, {}, reqid, False)
                self.onRspQryDepthMarketData({'InstrumentID': 'ag2612', 'Volume': 1000}, {}, reqid, True)
                return 0
        AutoMd.instances = []
        current = demo.Session(settings(), [], output=self.lines.append, active_count=2)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(demo.run(current, AutoMd, QuoteTd, Path(folder), duration=0.001), 0)
        self.assertEqual(current.symbols, ['ag2612', 'rb2701'])
        subscriptions = [call[1] for call in AutoMd.instances[-1].calls if call[0] == 'subscribe']
        self.assertEqual(subscriptions, current.symbols)

    def test_optional_volume_query_error_uses_explicitly_labelled_fallback(self):
        class ErrorTd(AutoTd):
            def reqQryDepthMarketData(self, request, reqid):
                self.onRspError({'ErrorID': 7, 'ErrorMsg': 'query unavailable'}, reqid, True)
                return 0
        current = demo.Session(settings(), [], output=self.lines.append)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(demo.run(current, AutoMd, ErrorTd, Path(folder), duration=0.001), 0)
        self.assertFalse(current.failed)
        self.assertEqual(current.symbols, list(demo.FALLBACK_SYMBOLS))
        self.assertTrue(any('未经实时活跃度核验' in line for line in self.lines))

    def test_volume_query_timeout_uses_fallback_and_ignores_late_data(self):
        class SilentTd(FakeApi):
            def reqQryDepthMarketData(self, request, reqid):
                return 0
        current = demo.Session(settings(), [], output=self.lines.append)
        td, _ = demo.build_clients(current, FakeApi, SilentTd)
        self.assertTrue(demo.choose_contracts(current, td, timeout=0.001))
        selected = list(current.symbols)
        td.onRspQryDepthMarketData({'InstrumentID': 'cu2611', 'Volume': 9999}, {}, current.depth_reqid, True)
        self.assertEqual(current.symbols, selected)
        self.assertEqual(current.depth_quotes, {})
        self.assertFalse(current.failed)

    def test_default_stream_stays_running_after_more_than_five_ticks(self):
        current = demo.Session(settings(), ['rb2701'], output=self.lines.append)
        codes = []
        QuietMd.instances = []
        with tempfile.TemporaryDirectory() as folder:
            worker = Thread(target=lambda: codes.append(demo.run(current, QuietMd, AutoTd, Path(folder))))
            worker.start()
            try:
                self.assertTrue(current.subscribed.wait(1))
                md = QuietMd.instances[-1]
                for _ in range(8):
                    md.onRtnDepthMarketData({'InstrumentID': 'rb2701', 'LastPrice': 101})
                self.assertFalse(current.stop.wait(0.02))
                self.assertEqual(current.tick_count, 8)
                self.assertTrue(worker.is_alive())
            finally:
                current.stop.set()
                worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(codes, [0])

    def test_default_stream_waits_for_ticks_without_closing_when_idle(self):
        current = demo.Session(settings(), ['rb2701'], output=self.lines.append)
        with tempfile.TemporaryDirectory() as folder:
            worker = Thread(target=demo.run, args=(current, QuietMd, AutoTd, Path(folder)))
            worker.start()
            try:
                self.assertTrue(current.subscribed.wait(1))
                self.assertFalse(current.stop.wait(0.02))
                self.assertTrue(worker.is_alive())
                self.assertEqual(current.tick_count, 0)
            finally:
                current.stop.set()
                worker.join(1)
        self.assertFalse(worker.is_alive())

    def test_keyboard_interrupt_closes_clients_and_returns_130(self):
        class InterruptingStop:
            def wait(self, timeout):
                raise KeyboardInterrupt
            def is_set(self):
                return False
            def set(self):
                pass
        current = demo.Session(settings(), ['rb2701'], output=self.lines.append)
        current.stop = InterruptingStop()
        AutoTd.instances = []
        QuietMd.instances = []
        with tempfile.TemporaryDirectory() as folder:
            code = demo.run(current, QuietMd, AutoTd, Path(folder))
        self.assertEqual(code, 130)
        self.assertEqual(AutoTd.instances[-1].exit_thread, get_ident())
        self.assertEqual(QuietMd.instances[-1].exit_thread, get_ident())

    def test_local_setup_preserves_existing_account_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            config = target / 'config.local.json'
            config.write_bytes(b'{"password":"private-local-value"}')
            before = config.read_bytes()
            with patch.object(run_ctp, 'DEMO_DIR', target):
                self.assertFalse(run_ctp.prepare_config())
            self.assertEqual(config.read_bytes(), before)

    def test_local_setup_creates_private_template_once(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            template = target / 'config.example.json'
            template.write_text('{"password":""}')
            with patch.object(run_ctp, 'DEMO_DIR', target):
                self.assertTrue(run_ctp.prepare_config())
                self.assertFalse(run_ctp.prepare_config())
            config = target / 'config.local.json'
            self.assertEqual(config.read_bytes(), template.read_bytes())
            if os.name != 'nt':
                self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_local_launcher_forwards_arguments_without_adding_exit_limits(self):
        with (patch.object(run_ctp, 'python_path', return_value=Path(sys.executable)),
              patch.object(run_ctp, 'prepare_config', return_value=False),
              patch.object(run_ctp.subprocess, 'run') as launch):
            launch.return_value.returncode = 0
            self.assertEqual(run_ctp.main(['--symbols', 'rb2701', 'ag2612']), 0)
        command = launch.call_args.args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[-3:], ['--symbols', 'rb2701', 'ag2612'])
        self.assertNotIn('--max-ticks', command)
        self.assertNotIn('--duration', command)


if __name__ == '__main__':
    unittest.main()
