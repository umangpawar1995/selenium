from datetime import datetime, timedelta, timezone

import pandas as pd

from trading_bot.bot.runner import PaperTradingRunner, SymbolAssignment
from trading_bot.broker import PaperBroker
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.portfolio import Portfolio
from trading_bot.strategies.base import Strategy
from tests.fakes import ScriptedFeed, quote


def _history(prices):
    idx = pd.date_range("2026-01-01", periods=len(prices), freq="h", tz="UTC")
    s = pd.Series(prices, index=idx)
    return pd.DataFrame({"open": s, "high": s * 1.001, "low": s * 0.999, "close": s, "volume": 1.0})


class AlwaysLong(Strategy):
    name = "always_long"

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(1.0, index=ohlcv.index)


class AlwaysFlat(Strategy):
    name = "always_flat"

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(0.0, index=ohlcv.index)


def _make_runner(strategy, quotes, histories):
    portfolio = Portfolio(starting_balance=10_000)
    feed = ScriptedFeed(quotes=quotes, histories=histories)
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    assignment = SymbolAssignment(symbol="BTCUSDT", strategy=strategy, history_interval="1h")
    return PaperTradingRunner(broker, [assignment], DEFAULT_CONFIG)


def test_first_tick_opens_with_warmup_size_not_full_kelly():
    quotes = {"BTCUSDT": [quote("BTCUSDT", 100, 99.9, 100.1)]}
    histories = {"BTCUSDT": _history([100] * 30)}
    runner = _make_runner(AlwaysLong(), quotes, histories)

    runner.tick(now=datetime.now(timezone.utc))

    assert "BTCUSDT" in runner.portfolio.positions
    notional = runner.portfolio.positions["BTCUSDT"].notional
    # warmup fraction is 2% of the 10,000 starting cash - a small bet, not
    # an all-in guess, since there's no trade history yet to size Kelly from.
    assert notional < 10_000 * 0.05


def test_flat_signal_never_opens_a_position():
    quotes = {"BTCUSDT": [quote("BTCUSDT", 100, 99.9, 100.1)] * 3}
    histories = {"BTCUSDT": _history([100] * 30)}
    runner = _make_runner(AlwaysFlat(), quotes, histories)
    runner.tick(now=datetime.now(timezone.utc))
    assert "BTCUSDT" not in runner.portfolio.positions


def test_perpetual_position_gets_charged_real_funding():
    portfolio = Portfolio(starting_balance=10_000)
    feed = ScriptedFeed(
        quotes={"BTCUSDT": [quote("BTCUSDT", 100, 99.9, 100.1)] * 5},
        histories={"BTCUSDT": _history([100] * 30)},
        funding_rates={"BTCUSDT": 0.0001},
    )
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    broker.open("BTCUSDT", "long", notional_target=1000)

    assignment = SymbolAssignment(
        symbol="BTCUSDT", strategy=AlwaysLong(), history_interval="1h", is_perpetual=True
    )
    runner = PaperTradingRunner(broker, [assignment], DEFAULT_CONFIG)

    cash_before = portfolio.cash
    runner.tick(now=datetime.now(timezone.utc))
    assert portfolio.positions["BTCUSDT"].funding_paid < 0  # a real charge was applied
    assert portfolio.cash < cash_before

    # funding shouldn't be charged twice within the same 8h interval
    funding_after_first_tick = portfolio.positions["BTCUSDT"].funding_paid
    runner.tick(now=datetime.now(timezone.utc) + timedelta(minutes=1))
    assert portfolio.positions["BTCUSDT"].funding_paid == funding_after_first_tick


def test_blowup_resets_and_banks_a_lesson():
    portfolio = Portfolio(starting_balance=1000)
    feed = ScriptedFeed(
        quotes={"BTCUSDT": [quote("BTCUSDT", 1.0, 0.999, 1.001)]},
        histories={"BTCUSDT": _history([1.0] * 30)},
    )
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    portfolio.open_position("BTCUSDT", "long", qty=1000, fill_price=1.0, fee=0.0,
                             timestamp=datetime.now(timezone.utc))

    assignment = SymbolAssignment(symbol="BTCUSDT", strategy=AlwaysFlat(), history_interval="1h")
    runner = PaperTradingRunner(broker, [assignment], DEFAULT_CONFIG)

    # force the mark price crash the blowup check will see
    feed._quotes["BTCUSDT"] = [quote("BTCUSDT", 0.01, 0.009, 0.011)]
    feed._index["BTCUSDT"] = 0

    runner.tick(now=datetime.now(timezone.utc))

    assert portfolio.bust_count == 1
    assert portfolio.cash == portfolio.starting_balance
    assert len(runner.lessons) == 1
    assert runner.lessons[0].bust_count == 1
