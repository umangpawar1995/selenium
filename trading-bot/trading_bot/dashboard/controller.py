"""
Owns whichever single paper-trading run is currently active, so the
dashboard can start/stop/switch symbol+strategy from the browser instead of
requiring a separate terminal command per combination.
"""

import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from trading_bot.backtest.backtester import passes_honest_bar
from trading_bot.backtest.suite import run_all_strategies
from trading_bot.bot.runner import PaperTradingRunner, SymbolAssignment
from trading_bot.broker import PaperBroker
from trading_bot.config import BotConfig, DEFAULT_CONFIG
from trading_bot.data_feed.base import PriceFeed
from trading_bot.data_feed.binance_feed import BinanceFeed
from trading_bot.data_feed.yahoo_feed import YahooFeed
from trading_bot.portfolio import Portfolio
from trading_bot.strategies.registry import STRATEGIES

PERIODS_PER_YEAR = {
    "1m": 365 * 24 * 60, "5m": 365 * 24 * 12, "15m": 365 * 24 * 4,
    "1h": 365 * 24, "4h": 365 * 6, "1d": 365,
}


def default_feed_factory(source: str) -> PriceFeed:
    return BinanceFeed() if source == "binance" else YahooFeed()


class BotController:
    def __init__(
        self,
        cfg: BotConfig = DEFAULT_CONFIG,
        feed_factory: Callable[[str], PriceFeed] = default_feed_factory,
    ):
        self.cfg = cfg
        self._feed_factory = feed_factory
        self._lock = threading.Lock()
        self.runner: Optional[PaperTradingRunner] = None
        self.current: Optional[dict] = None  # {symbol, source, strategy, interval, perpetual}
        self._stop_event: Optional[threading.Event] = None

    def available_strategies(self):
        return sorted(STRATEGIES.keys())

    def is_running(self) -> bool:
        return self.runner is not None

    def start(
        self,
        symbol: str,
        source: str,
        strategy_name: str,
        interval: str = "1h",
        perpetual: bool = False,
        tick_seconds: float = 60.0,
    ) -> None:
        if strategy_name not in STRATEGIES:
            raise ValueError(f"unknown strategy: {strategy_name}")
        if source not in ("binance", "yahoo"):
            raise ValueError(f"unknown source: {source}")

        with self._lock:
            self._stop_locked()

            feed = self._feed_factory(source)
            portfolio = Portfolio(starting_balance=self.cfg.starting_balance)
            broker = PaperBroker(feed, portfolio, self.cfg)
            assignment = SymbolAssignment(
                symbol=symbol,
                strategy=STRATEGIES[strategy_name](),
                history_interval=interval,
                is_perpetual=perpetual,
            )
            runner = PaperTradingRunner(broker, [assignment], self.cfg)

            stop_event = threading.Event()
            thread = threading.Thread(
                target=runner.run_forever, args=(tick_seconds, stop_event), daemon=True
            )
            self.runner = runner
            self._stop_event = stop_event
            self.current = {
                "symbol": symbol, "source": source, "strategy": strategy_name,
                "interval": interval, "perpetual": perpetual,
            }
            thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        self.runner = None
        self._stop_event = None
        self.current = None

    def backtest(self, symbol: str, source: str, interval: str, days: int) -> list:
        feed = self._feed_factory(source)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        ohlcv = feed.get_history(symbol, interval, start, end)
        if ohlcv.empty:
            raise ValueError(f"no history returned for {symbol} from {source}")

        periods_per_year = PERIODS_PER_YEAR.get(interval, 365)
        results = run_all_strategies(ohlcv, self.cfg, periods_per_year)
        return [
            {
                "strategy": r.strategy_name,
                "passed": passes_honest_bar(r),
                "trades": r.metrics.num_trades,
                "total_return": r.metrics.total_return,
                "sharpe": r.metrics.sharpe,
                "max_drawdown": r.metrics.max_drawdown,
                "win_rate": r.metrics.win_rate,
                "profit_factor": r.metrics.profit_factor,
            }
            for r in results
        ]
