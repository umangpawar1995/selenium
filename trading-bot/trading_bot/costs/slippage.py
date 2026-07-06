from dataclasses import dataclass
from typing import Optional

from trading_bot.config import SlippageConfig


@dataclass(frozen=True)
class Fill:
    price: float
    source: str  # "book" (crossed a real bid/ask) or "estimate" (documented fallback)


def fill_price(
    side: str,
    last_price: float,
    cfg: SlippageConfig,
    bid: Optional[float] = None,
    ask: Optional[float] = None,
) -> Fill:
    """
    A market buy fills at the real ask, a market sell fills at the real bid -
    that is the honest cost of crossing the spread, not a made-up number.

    If a live order book isn't available (e.g. a delayed stock quote with no
    bid/ask), falls back to a documented spread estimate applied to the last
    traded price, and is labeled source="estimate" so it is never confused
    with a real quoted fill.
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")

    if bid is not None and ask is not None:
        price = ask if side == "buy" else bid
        return Fill(price=price, source="book")

    half_spread = last_price * cfg.fallback_spread_pct_of_price / 2
    price = last_price + half_spread if side == "buy" else last_price - half_spread
    return Fill(price=price, source="estimate")
