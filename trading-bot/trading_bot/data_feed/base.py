from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    bid: Optional[float]
    ask: Optional[float]
    timestamp: datetime
    source: str  # exact API this came from, e.g. "binance", "yfinance"


class PriceFeed(ABC):
    """
    A price feed is the only place real market data enters the bot. Every
    quote and every bar must say where it came from (`source`) so a fake
    number can never quietly pass as real data.
    """

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        """Latest real price for `symbol`, with bid/ask when available."""

    @abstractmethod
    def get_history(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """
        Real historical OHLCV bars for `symbol` between start and end.
        Returned DataFrame is indexed by UTC timestamp with columns:
        open, high, low, close, volume.
        """
