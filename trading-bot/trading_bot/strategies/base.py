from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """A strategy turns real historical prices into a position series -
    nothing here touches money or fees, that's the backtester's/broker's job."""

    name: str

    @abstractmethod
    def signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Given an OHLCV DataFrame (columns: open, high, low, close, volume),
        returns a Series aligned to the same index with values in
        {-1, 0, 1} meaning short / flat / long for each bar.
        """
