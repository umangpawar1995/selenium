"""
Real live/historical crypto prices from Binance's public market-data API.
No API key needed - these are public endpoints, confirmed against the
official docs on 2026-07-06:
  https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

from trading_bot.data_feed.base import PriceFeed, Quote

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"

_KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


class BinanceFeed(PriceFeed):
    def __init__(self, session: Optional[requests.Session] = None, timeout: float = 10.0):
        self.session = session or requests.Session()
        self.timeout = timeout

    def get_quote(self, symbol: str) -> Quote:
        resp = self.session.get(
            f"{SPOT_BASE}/api/v3/ticker/bookTicker",
            params={"symbol": symbol},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        bid, ask = float(data["bidPrice"]), float(data["askPrice"])
        mid = (bid + ask) / 2
        return Quote(
            symbol=symbol,
            price=mid,
            bid=bid,
            ask=ask,
            timestamp=datetime.now(timezone.utc),
            source="binance",
        )

    def get_history(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        rows = []
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        cursor = start_ms
        while cursor < end_ms:
            resp = self.session.get(
                f"{SPOT_BASE}/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            rows.extend(batch)
            cursor = batch[-1][0] + 1
            if len(batch) < 1000:
                break

        df = pd.DataFrame(rows, columns=_KLINE_COLUMNS)
        if df.empty:
            return df.set_index(pd.DatetimeIndex([], name="timestamp"))[
                ["open", "high", "low", "close", "volume"]
            ]
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        return df[["open", "high", "low", "close", "volume"]]

    def get_funding_rate_history(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Real, exchange-reported historical funding rates (not an estimate).
        https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
        """
        resp = self.session.get(
            f"{FUTURES_BASE}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
        df["fundingRate"] = df["fundingRate"].astype(float)
        return df.set_index("fundingTime")[["fundingRate", "markPrice"]]
