import pandas as pd

from trading_bot.config import DEFAULT_CONFIG
from trading_bot.dashboard.app import create_app
from trading_bot.dashboard.controller import BotController
from tests.fakes import ScriptedFeed, quote


def _history(prices):
    idx = pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC")
    s = pd.Series(prices, index=idx)
    return pd.DataFrame({"open": s, "high": s * 1.001, "low": s * 0.999, "close": s, "volume": 1.0})


def _controller_with_a_run():
    histories = {"BTCUSDT": _history([100] * 30)}
    quotes = {"BTCUSDT": [quote("BTCUSDT", 100, 99.9, 100.1)] * 5}

    def feed_factory(source):
        return ScriptedFeed(quotes=quotes, histories=histories)

    controller = BotController(cfg=DEFAULT_CONFIG, feed_factory=feed_factory)
    controller.start(symbol="BTCUSDT", source="binance", strategy_name="sma_crossover", interval="1h")
    return controller


def test_index_page_renders_with_strategy_options():
    controller = BotController()
    client = create_app(controller).test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"paper trading bot" in resp.data
    assert b"sma_crossover" in resp.data


def test_state_api_reports_not_running_before_start():
    controller = BotController()
    client = create_app(controller).test_client()
    data = client.get("/api/state").get_json()
    assert data["running"] is False


def test_state_api_reports_real_ledger_numbers_once_running():
    controller = _controller_with_a_run()
    client = create_app(controller).test_client()
    data = client.get("/api/state").get_json()
    assert data["running"] is True
    assert data["current"]["symbol"] == "BTCUSDT"
    assert data["starting_balance"] == DEFAULT_CONFIG.starting_balance


def test_start_and_stop_endpoints():
    histories = {"AAPL": _history([100] * 30)}
    quotes = {"AAPL": [quote("AAPL", 100, 99.9, 100.1)] * 5}

    def feed_factory(source):
        return ScriptedFeed(quotes=quotes, histories=histories)

    controller = BotController(feed_factory=feed_factory)
    client = create_app(controller).test_client()

    resp = client.post("/api/start", json={"symbol": "AAPL", "source": "yahoo", "strategy": "sma_crossover"})
    assert resp.get_json()["ok"] is True
    assert controller.is_running()

    resp = client.post("/api/stop")
    assert resp.get_json()["ok"] is True
    assert not controller.is_running()


def test_start_endpoint_reports_error_for_bad_strategy():
    controller = BotController()
    client = create_app(controller).test_client()
    resp = client.post("/api/start", json={"symbol": "AAPL", "source": "yahoo", "strategy": "nope"})
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False
