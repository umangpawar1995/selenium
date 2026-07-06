from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal

Side = Literal["long", "short"]


@dataclass
class Position:
    symbol: str
    side: Side
    qty: float
    entry_price: float
    entry_time: datetime
    entry_fee: float
    funding_paid: float = 0.0  # accrues while the position stays open

    @property
    def notional(self) -> float:
        return self.qty * self.entry_price


@dataclass
class Trade:
    symbol: str
    side: Side
    qty: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    entry_fee: float
    exit_fee: float
    funding_paid: float
    gross_pnl: float
    net_pnl: float  # gross_pnl - entry_fee - exit_fee - funding_paid, exactly, win or lose


class Portfolio:
    """
    The fake-money ledger. Cash only ever moves by real fees, real funding,
    and the real (possibly negative) PnL of a closed trade - there is no
    code path that rounds a loss away or skips recording one.
    """

    def __init__(self, starting_balance: float):
        self.starting_balance = starting_balance
        self.cash = starting_balance
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self.equity_history: List[tuple] = []  # (timestamp, equity)
        self.bust_count = 0

    def equity(self, mark_prices: Dict[str, float]) -> float:
        total = self.cash
        for symbol, pos in self.positions.items():
            price = mark_prices.get(symbol, pos.entry_price)
            direction = 1 if pos.side == "long" else -1
            total += pos.qty * pos.entry_price + direction * pos.qty * (price - pos.entry_price)
        return total

    def record_equity(self, timestamp: datetime, mark_prices: Dict[str, float]) -> float:
        eq = self.equity(mark_prices)
        self.equity_history.append((timestamp, eq))
        return eq

    def open_position(
        self,
        symbol: str,
        side: Side,
        qty: float,
        fill_price: float,
        fee: float,
        timestamp: datetime,
    ) -> Position:
        """Reserves the full notional as margin (no leverage) plus the fee.
        Long and short both tie up the same notional; only the direction of
        the eventual PnL differs. That keeps the ledger's cash math identical
        for both sides instead of simulating short-borrow mechanics."""
        if symbol in self.positions:
            raise ValueError(f"{symbol} already has an open position")
        notional = qty * fill_price
        self.cash -= notional + fee
        pos = Position(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=fill_price,
            entry_time=timestamp,
            entry_fee=fee,
        )
        self.positions[symbol] = pos
        return pos

    def add_funding(self, symbol: str, amount: float) -> None:
        pos = self.positions[symbol]
        pos.funding_paid += amount
        self.cash += amount  # amount is signed: negative = paid out, positive = received

    def close_position(
        self, symbol: str, fill_price: float, fee: float, timestamp: datetime
    ) -> Trade:
        pos = self.positions.pop(symbol)
        direction = 1 if pos.side == "long" else -1
        gross_pnl = direction * pos.qty * (fill_price - pos.entry_price)
        margin_return = pos.qty * pos.entry_price  # the notional reserved at open_position
        self.cash += margin_return + gross_pnl - fee
        # funding_paid is already signed (negative = cost, positive = received),
        # so it's added, not subtracted, to avoid flipping its sign twice.
        net_pnl = gross_pnl - pos.entry_fee - fee + pos.funding_paid
        trade = Trade(
            symbol=symbol,
            side=pos.side,
            qty=pos.qty,
            entry_price=pos.entry_price,
            exit_price=fill_price,
            entry_time=pos.entry_time,
            exit_time=timestamp,
            entry_fee=pos.entry_fee,
            exit_fee=fee,
            funding_paid=pos.funding_paid,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
        )
        self.closed_trades.append(trade)
        return trade

    def is_blown_up(self, mark_prices: Dict[str, float], blowup_fraction: float) -> bool:
        return self.equity(mark_prices) <= self.starting_balance * blowup_fraction

    def reset(self) -> None:
        """Reset-and-learn: wipe the ledger back to the starting balance but
        keep closed_trades so past lessons aren't erased."""
        self.bust_count += 1
        self.cash = self.starting_balance
        self.positions.clear()
