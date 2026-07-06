import numpy as np
import pandas as pd

from trading_bot.backtest.backtester import run_backtest, passes_honest_bar
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.strategies.sma_crossover import SmaCrossover
from trading_bot.strategies.base import Strategy


def _synthetic_ohlcv(closes) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D", tz="UTC")
    closes = pd.Series(closes, index=idx)
    return pd.DataFrame({
        "open": closes, "high": closes * 1.001, "low": closes * 0.999,
        "close": closes, "volume": 1000.0,
    })


class AlwaysLong(Strategy):
    name = "always_long"

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(1.0, index=ohlcv.index)


class AlwaysFlat(Strategy):
    name = "always_flat"

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        return pd.Series(0.0, index=ohlcv.index)


def test_always_flat_never_pays_fees_and_equity_is_flat():
    df = _synthetic_ohlcv(np.linspace(100, 200, 50))
    result = run_backtest(df, AlwaysFlat(), DEFAULT_CONFIG, periods_per_year=365)
    assert result.trades == []
    assert result.equity_curve.iloc[-1] == DEFAULT_CONFIG.starting_balance


def test_always_long_in_uptrend_profits_net_of_real_costs():
    df = _synthetic_ohlcv(np.linspace(100, 300, 100))
    result = run_backtest(df, AlwaysLong(), DEFAULT_CONFIG, periods_per_year=365)
    assert result.equity_curve.iloc[-1] > DEFAULT_CONFIG.starting_balance
    assert len(result.trades) == 1  # opens once, held to the end
    assert result.trades[0].net_pnl > 0


def test_always_long_in_downtrend_shows_a_real_loss():
    df = _synthetic_ohlcv(np.linspace(200, 100, 100))
    result = run_backtest(df, AlwaysLong(), DEFAULT_CONFIG, periods_per_year=365)
    assert result.equity_curve.iloc[-1] < DEFAULT_CONFIG.starting_balance
    assert result.trades[0].net_pnl < 0
    assert not passes_honest_bar(result)  # a losing strategy must not pass


def test_sma_crossover_backtest_runs_and_produces_metrics():
    np.random.seed(7)
    walk = 100 + np.cumsum(np.random.normal(0, 1, 200))
    df = _synthetic_ohlcv(walk)
    result = run_backtest(df, SmaCrossover(fast=5, slow=20), DEFAULT_CONFIG, periods_per_year=365)
    assert result.metrics.num_trades >= 0
    assert isinstance(passes_honest_bar(result), bool)


def test_fees_make_pure_noise_trading_a_net_loser():
    # a strategy that flips every bar on pure noise should be ground down by
    # fees+spread - the honest bar must reject it.
    np.random.seed(3)
    walk = 100 + np.cumsum(np.random.normal(0, 0.5, 100))
    df = _synthetic_ohlcv(walk)

    class FlipEveryBar(Strategy):
        name = "flip_every_bar"

        def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
            return pd.Series([1.0 if i % 2 == 0 else -1.0 for i in range(len(ohlcv))], index=ohlcv.index)

    result = run_backtest(df, FlipEveryBar(), DEFAULT_CONFIG, periods_per_year=365)
    assert result.metrics.num_trades >= 90
    assert not passes_honest_bar(result)
