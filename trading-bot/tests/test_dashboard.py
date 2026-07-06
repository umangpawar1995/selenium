from datetime import datetime, timezone

from trading_bot.bot.runner import PaperTradingRunner, SymbolAssignment
from trading_bot.broker import PaperBroker
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.dashboard.app import create_app
from trading_bot.portfolio import Portfolio
from trading_bot.strategies.sma_crossover import SmaCrossover
from tests.fakes import ScriptedFeed, quote
from tests.test_runner import _history


def _runner_with_one_trade():
    portfolio = Portfolio(starting_balance=10_000)
    feed = ScriptedFeed(
        quotes={"BTCUSDT": [quote("BTCUSDT", 100, 99.9, 100.1)] * 10},
        histories={"BTCUSDT": _history([100] * 30)},
    )
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    broker.open("BTCUSDT", "long", notional_target=500)
    broker.close("BTCUSDT")
    portfolio.record_equity(datetime.now(timezone.utc), {"BTCUSDT": 100})
    assignment = SymbolAssignment(symbol="BTCUSDT", strategy=SmaCrossover(), history_interval="1h")
    return PaperTradingRunner(broker, [assignment], DEFAULT_CONFIG)


def test_index_page_renders():
    runner = _runner_with_one_trade()
    client = create_app(runner).test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"paper trading bot" in resp.data


def test_state_api_reports_real_ledger_numbers():
    runner = _runner_with_one_trade()
    client = create_app(runner).test_client()
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["starting_balance"] == 10_000
    assert len(data["recent_trades"]) == 1
    assert data["recent_trades"][0]["symbol"] == "BTCUSDT"
    assert data["bust_count"] == 0
