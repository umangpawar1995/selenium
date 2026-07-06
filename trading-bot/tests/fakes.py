from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

from trading_bot.data_feed.base import PriceFeed, Quote


class ScriptedFeed(PriceFeed):
    """Deterministic feed for tests: replays a scripted sequence of quotes
    per symbol instead of hitting a real network - this is a test double,
    never used by the live bot itself."""

    def __init__(
        self,
        quotes: Dict[str, List[Quote]],
        histories: Optional[Dict[str, pd.DataFrame]] = None,
        funding_rates: Optional[Dict[str, float]] = None,
    ):
        self._quotes = {symbol: list(seq) for symbol, seq in quotes.items()}
        self._index = {symbol: 0 for symbol in quotes}
        self._histories = histories or {}
        self._funding_rates = funding_rates or {}

    def get_quote(self, symbol: str) -> Quote:
        i = self._index[symbol]
        seq = self._quotes[symbol]
        quote = seq[min(i, len(seq) - 1)]
        self._index[symbol] = i + 1
        return quote

    def get_history(self, symbol: str, interval: str, start, end) -> pd.DataFrame:
        if symbol not in self._histories:
            raise NotImplementedError(f"no scripted history for {symbol}")
        return self._histories[symbol]

    def get_funding_rate_history(self, symbol: str, limit: int = 1) -> pd.DataFrame:
        rate = self._funding_rates.get(symbol, 0.0001)
        return pd.DataFrame({"fundingRate": [rate], "markPrice": [0.0]})


def quote(symbol, price, bid=None, ask=None, source="test") -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        bid=bid,
        ask=ask,
        timestamp=datetime.now(timezone.utc),
        source=source,
    )
