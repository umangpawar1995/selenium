import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

from trading_bot.broker import PaperBroker
from trading_bot.config import BotConfig
from trading_bot.portfolio import Portfolio
from trading_bot.sizing.kelly import estimate_from_trades
from trading_bot.strategies.base import Strategy

log = logging.getLogger("trading_bot.runner")


@dataclass
class SymbolAssignment:
    symbol: str
    strategy: Strategy
    history_interval: str = "1h"
    history_lookback_bars: int = 200
    is_perpetual: bool = False  # only perpetual futures accrue funding


@dataclass
class Lesson:
    """One entry per reset-and-learn bust: what was open, and the honest
    stats banked from the run that just ended."""
    timestamp: datetime
    bust_count: int
    equity_at_reset: float
    trades_so_far: int
    win_rate_so_far: float


class PaperTradingRunner:
    def __init__(
        self,
        broker: PaperBroker,
        assignments: List[SymbolAssignment],
        cfg: BotConfig,
    ):
        self.broker = broker
        self.assignments = {a.symbol: a for a in assignments}
        self.cfg = cfg
        self.lessons: List[Lesson] = []
        self._last_funding_charge: Dict[str, datetime] = {}

    @property
    def portfolio(self) -> Portfolio:
        return self.broker.portfolio

    def _current_kelly_fraction(self) -> float:
        pnls = [t.net_pnl for t in self.portfolio.closed_trades]
        return estimate_from_trades(pnls, self.cfg.kelly).sized_fraction

    def _maybe_charge_funding(self, symbol: str, now: datetime) -> None:
        assignment = self.assignments[symbol]
        if not assignment.is_perpetual or symbol not in self.portfolio.positions:
            return
        last = self._last_funding_charge.get(symbol)
        interval = timedelta(hours=self.cfg.funding.interval_hours)
        if last is not None and now - last < interval:
            return
        try:
            history = self.broker.feed.get_funding_rate_history(symbol, limit=1)
            live_rate = float(history["fundingRate"].iloc[-1])
            self.broker.charge_funding(symbol, live_rate=live_rate)
        except Exception:
            log.warning("could not fetch live funding rate for %s; skipping this interval", symbol)
            return
        self._last_funding_charge[symbol] = now

    def tick(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)

        mark_prices = self.broker.mark_to_market(list(self.assignments))
        if self.broker.check_blowup_and_reset(mark_prices, now):
            pnls = [t.net_pnl for t in self.portfolio.closed_trades]
            wins = sum(1 for p in pnls if p > 0)
            self.lessons.append(Lesson(
                timestamp=now,
                bust_count=self.portfolio.bust_count,
                equity_at_reset=self.portfolio.starting_balance * self.cfg.blowup_fraction,
                trades_so_far=len(pnls),
                win_rate_so_far=(wins / len(pnls)) if pnls else 0.0,
            ))
            log.warning("blew up (bust #%d) - resetting and continuing", self.portfolio.bust_count)

        for symbol, assignment in self.assignments.items():
            self._maybe_charge_funding(symbol, now)

            end = now
            start = end - _bar_span(assignment.history_interval) * assignment.history_lookback_bars
            history = self.broker.feed.get_history(symbol, assignment.history_interval, start, end)
            if history.empty:
                continue
            signal = assignment.strategy.signal(history)
            target = signal.iloc[-1]

            has_position = symbol in self.portfolio.positions
            current_side = self.portfolio.positions[symbol].side if has_position else None
            target_side = "long" if target == 1.0 else ("short" if target == -1.0 else None)

            if has_position and target_side != current_side:
                self.broker.close(symbol)
                has_position = False

            if target_side is not None and not has_position:
                fraction = self._current_kelly_fraction()
                if fraction <= 0.0:
                    continue  # no verified edge yet - stay flat rather than guess a size
                notional = self.portfolio.cash * fraction
                if notional <= 0:
                    continue
                self.broker.open(symbol, target_side, notional)

        self.portfolio.record_equity(now, mark_prices)

    def run_forever(self, interval_seconds: float = 60.0) -> None:
        """Blocking loop for a real local run - not meant to run inside a
        sandboxed CI container. Ctrl+C to stop."""
        while True:
            self.tick()
            time.sleep(interval_seconds)


def _bar_span(interval: str) -> timedelta:
    unit = interval[-1]
    amount = int(interval[:-1])
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    raise ValueError(f"unsupported interval: {interval}")
