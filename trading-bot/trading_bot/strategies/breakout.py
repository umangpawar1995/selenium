import numpy as np
import pandas as pd

from trading_bot.strategies.base import Strategy


class DonchianBreakout(Strategy):
    """
    Donchian channel breakout: go long when price closes above the highest
    high of the last N bars (excluding the current bar), short when it
    closes below the lowest low of the last N bars. Standard definition,
    confirmed against Wikipedia's Donchian channel article.
    """

    name = "donchian_breakout"

    def __init__(self, window: int = 20):
        self.window = window

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        upper = ohlcv["high"].rolling(self.window).max().shift(1)
        lower = ohlcv["low"].rolling(self.window).min().shift(1)
        close = ohlcv["close"]

        position = pd.Series(0.0, index=ohlcv.index)
        state = 0.0
        for i in range(len(ohlcv)):
            if np.isnan(upper.iloc[i]) or np.isnan(lower.iloc[i]):
                position.iloc[i] = 0.0
                continue
            if close.iloc[i] > upper.iloc[i]:
                state = 1.0
            elif close.iloc[i] < lower.iloc[i]:
                state = -1.0
            position.iloc[i] = state
        return position
