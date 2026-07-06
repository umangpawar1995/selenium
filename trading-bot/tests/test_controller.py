import pandas as pd

from trading_bot.config import DEFAULT_CONFIG
from trading_bot.dashboard.controller import BotController
from tests.fakes import ScriptedFeed, quote


def _history(prices, freq="D"):
    idx = pd.date_range("2026-01-01", periods=len(prices), freq=freq, tz="UTC")
    s = pd.Series(prices, index=idx)
    return pd.DataFrame({"open": s, "high": s * 1.001, "low": s * 0.999, "close": s, "volume": 1.0})


def _make_controller(histories, quotes):
    def feed_factory(source):
        return ScriptedFeed(quotes=quotes, histories=histories)

    return BotController(cfg=DEFAULT_CONFIG, feed_factory=feed_factory)


def test_not_running_until_started():
    controller = _make_controller({}, {})
    assert not controller.is_running()
    assert controller.current is None


def test_start_then_stop_switches_cleanly():
    histories = {"RELIANCE.NS": _history([100] * 30)}
    quotes = {"RELIANCE.NS": [quote("RELIANCE.NS", 100, 99.9, 100.1)] * 5}
    controller = _make_controller(histories, quotes)

    controller.start(symbol="RELIANCE.NS", source="yahoo", strategy_name="sma_crossover", interval="1d")
    assert controller.is_running()
    assert controller.current["symbol"] == "RELIANCE.NS"
    assert controller.current["strategy"] == "sma_crossover"

    controller.stop()
    assert not controller.is_running()
    assert controller.current is None


def test_start_rejects_unknown_strategy():
    controller = _make_controller({}, {})
    try:
        controller.start(symbol="X", source="yahoo", strategy_name="not_a_real_strategy")
        assert False, "should have raised"
    except ValueError:
        pass


def test_backtest_runs_every_registered_strategy():
    import numpy as np
    histories = {"BTCUSDT": _history(list(100 + np.cumsum(np.random.default_rng(1).normal(0, 1, 120))))}
    controller = _make_controller(histories, {})

    results = controller.backtest(symbol="BTCUSDT", source="binance", interval="1d", days=120)
    names = {r["strategy"] for r in results}
    assert names == {"sma_crossover", "rsi_reversion", "donchian_breakout"}
    for r in results:
        assert isinstance(r["passed"], bool)


def test_available_strategies_matches_registry():
    controller = _make_controller({}, {})
    assert controller.available_strategies() == ["donchian_breakout", "rsi_reversion", "sma_crossover"]
