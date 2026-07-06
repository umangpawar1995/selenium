import numpy as np
import pandas as pd

from trading_bot.strategies.base import Strategy


class SmaCrossover(Strategy):
    """Classic trend-following: long while the fast SMA is above the slow
    SMA, short while it's below. Textbook definition, no variant invented."""

    name = "sma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError("fast window must be shorter than slow window")
        self.fast = fast
        self.slow = slow

    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        fast_sma = ohlcv["close"].rolling(self.fast).mean()
        slow_sma = ohlcv["close"].rolling(self.slow).mean()
        position = np.where(fast_sma > slow_sma, 1, -1)
        position = pd.Series(position, index=ohlcv.index, dtype=float)
        position[slow_sma.isna()] = 0  # no signal until both averages exist
        return position
