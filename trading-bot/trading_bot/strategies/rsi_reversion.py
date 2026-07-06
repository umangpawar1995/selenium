import numpy as np
import pandas as pd

from trading_bot.strategies.base import Strategy


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Standard Wilder RSI: RS = avg_gain / avg_loss (Wilder smoothing),
    RSI = 100 - 100 / (1 + RS). Confirmed against StockCharts/Macroption.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)  # avg_loss == 0 means pure gains -> RSI 100


class RsiReversion(Strategy):
    """Mean reversion: go long when RSI dips under `oversold`, go short when
    it climbs over `overbought`, flat back out around the midline (50)."""

    name = "rsi_reversion"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        rsi = wilder_rsi(ohlcv["close"], self.period)
        position = pd.Series(0.0, index=ohlcv.index)
        state = 0.0
        for i, value in enumerate(rsi):
            if np.isnan(value):
                position.iloc[i] = 0.0
                continue
            if value < self.oversold:
                state = 1.0
            elif value > self.overbought:
                state = -1.0
            elif (state == 1.0 and value >= 50) or (state == -1.0 and value <= 50):
                state = 0.0
            position.iloc[i] = state
        return position
