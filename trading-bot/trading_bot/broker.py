from datetime import datetime
from typing import Optional

from trading_bot.config import BotConfig
from trading_bot.costs.fees import taker_fee
from trading_bot.costs.funding import apply_funding
from trading_bot.costs.slippage import fill_price
from trading_bot.data_feed.base import PriceFeed, Quote
from trading_bot.portfolio import Portfolio, Side, Trade


class PaperBroker:
    """
    The one honest engine: every open/close touches a real quote, pays the
    real fee, crosses the real (or clearly-labeled fallback) spread, and
    writes the exact result - profit or loss - to the ledger. Fake money in,
    real market mechanics applied, truthful numbers out.
    """

    def __init__(self, feed: PriceFeed, portfolio: Portfolio, cfg: BotConfig):
        self.feed = feed
        self.portfolio = portfolio
        self.cfg = cfg

    def open(self, symbol: str, side: Side, notional_target: float) -> None:
        quote = self.feed.get_quote(symbol)
        order_side = "buy" if side == "long" else "sell"
        fill = fill_price(order_side, quote.price, self.cfg.slippage, quote.bid, quote.ask)
        qty = notional_target / fill.price
        fee = taker_fee(qty * fill.price, self.cfg.fees)
        self.portfolio.open_position(
            symbol=symbol,
            side=side,
            qty=qty,
            fill_price=fill.price,
            fee=fee,
            timestamp=quote.timestamp,
        )

    def close(self, symbol: str) -> Trade:
        quote = self.feed.get_quote(symbol)
        pos = self.portfolio.positions[symbol]
        order_side = "sell" if pos.side == "long" else "buy"
        fill = fill_price(order_side, quote.price, self.cfg.slippage, quote.bid, quote.ask)
        fee = taker_fee(pos.qty * fill.price, self.cfg.fees)
        return self.portfolio.close_position(
            symbol=symbol, fill_price=fill.price, fee=fee, timestamp=quote.timestamp
        )

    def charge_funding(
        self, symbol: str, live_rate: Optional[float] = None, premium_index: Optional[float] = None
    ) -> None:
        """Applies one funding interval's charge to an open position."""
        pos = self.portfolio.positions[symbol]
        charge = apply_funding(
            position_notional=pos.qty * pos.entry_price,
            is_long=(pos.side == "long"),
            cfg=self.cfg.funding,
            live_rate=live_rate,
            premium_index=premium_index,
        )
        self.portfolio.add_funding(symbol, charge.amount)

    def mark_to_market(self, symbols: list) -> dict:
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.feed.get_quote(symbol).price
        return prices

    def check_blowup_and_reset(self, mark_prices: dict, now: datetime) -> bool:
        if self.portfolio.is_blown_up(mark_prices, self.cfg.blowup_fraction):
            self.portfolio.record_equity(now, mark_prices)
            self.portfolio.reset()
            return True
        return False
