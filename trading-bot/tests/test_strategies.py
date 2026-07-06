import numpy as np
import pandas as pd

from trading_bot.strategies.sma_crossover import SmaCrossover
from trading_bot.strategies.rsi_reversion import wilder_rsi, RsiReversion
from trading_bot.strategies.breakout import DonchianBreakout


def _synthetic_ohlcv(closes) -> pd.DataFrame:
    """Deterministic synthetic bars for unit-testing signal logic only -
    never used to claim a backtest ran on real market history."""
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D", tz="UTC")
    closes = pd.Series(closes, index=idx)
    return pd.DataFrame({
        "open": closes, "high": closes * 1.001, "low": closes * 0.999,
        "close": closes, "volume": 1000.0,
    })


def test_sma_crossover_goes_long_in_uptrend():
    closes = list(np.linspace(100, 200, 80))
    df = _synthetic_ohlcv(closes)
    strat = SmaCrossover(fast=5, slow=20)
    signal = strat.signal(df)
    assert signal.iloc[-1] == 1.0
    assert signal.iloc[:19].eq(0.0).all()  # no signal before the 20-bar slow SMA fills


def test_sma_crossover_goes_short_in_downtrend():
    closes = list(np.linspace(200, 100, 80))
    df = _synthetic_ohlcv(closes)
    strat = SmaCrossover(fast=5, slow=20)
    signal = strat.signal(df)
    assert signal.iloc[-1] == -1.0


def test_wilder_rsi_is_100_for_pure_uptrend():
    closes = list(range(1, 40))  # strictly increasing -> no losses at all
    df = _synthetic_ohlcv(closes)
    rsi = wilder_rsi(df["close"], period=14)
    assert rsi.iloc[-1] == 100.0


def test_rsi_reversion_goes_long_after_a_sharp_drop():
    closes = [100.0] * 20 + list(np.linspace(100, 60, 10))  # sharp drop -> oversold
    df = _synthetic_ohlcv(closes)
    strat = RsiReversion(period=14)
    signal = strat.signal(df)
    assert signal.iloc[-1] == 1.0


def test_donchian_breakout_goes_long_on_new_high():
    closes = [100.0] * 25 + [150.0]  # sudden breakout above the 20-bar range
    df = _synthetic_ohlcv(closes)
    strat = DonchianBreakout(window=20)
    signal = strat.signal(df)
    assert signal.iloc[-1] == 1.0
    assert signal.iloc[:20].eq(0.0).all()
