"""
Real stock prices via yfinance, an open-source wrapper around Yahoo
Finance's public (unofficial, no-key-required) endpoints. Confirmed
2026-07-06: https://github.com/ranaroussi/yfinance

Yahoo's free quotes are delayed for many exchanges and frequently omit a
live bid/ask outside market hours - when that happens `Quote.bid`/`.ask`
come back as None rather than a guessed number, and the slippage model
falls back to its documented estimate instead of pretending it saw a book.
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from trading_bot.data_feed.base import PriceFeed, Quote


class YahooFeed(PriceFeed):
    def get_quote(self, symbol: str) -> Quote:
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        price = float(fast["last_price"])
        bid = _clean(fast.get("bid"))
        ask = _clean(fast.get("ask"))
        return Quote(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            timestamp=datetime.now(timezone.utc),
            source="yfinance",
        )

    def get_history(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval, auto_adjust=True)
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "timestamp"
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close", "volume"]]


def _clean(value) -> Optional[float]:
    if value is None or value <= 0:
        return None
    return float(value)
