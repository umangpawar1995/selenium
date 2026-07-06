#!/usr/bin/env python3
"""
Fetches real historical prices and runs every strategy through the
backtester, keeping only the ones that honestly clear `passes_honest_bar`.

Usage:
  python run_backtest.py --symbol BTCUSDT --source binance --interval 1h --days 60
  python run_backtest.py --symbol AAPL --source yahoo --interval 1d --days 365
"""

import argparse
from datetime import datetime, timedelta, timezone

from trading_bot.backtest.backtester import passes_honest_bar, run_backtest
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.data_feed.binance_feed import BinanceFeed
from trading_bot.data_feed.yahoo_feed import YahooFeed
from trading_bot.strategies.breakout import DonchianBreakout
from trading_bot.strategies.rsi_reversion import RsiReversion
from trading_bot.strategies.sma_crossover import SmaCrossover

PERIODS_PER_YEAR = {
    "1m": 365 * 24 * 60, "5m": 365 * 24 * 12, "15m": 365 * 24 * 4,
    "1h": 365 * 24, "4h": 365 * 6, "1d": 365,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--source", choices=["binance", "yahoo"], required=True)
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()

    feed = BinanceFeed() if args.source == "binance" else YahooFeed()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    print(f"fetching real {args.interval} history for {args.symbol} from {args.source}...")
    ohlcv = feed.get_history(args.symbol, args.interval, start, end)
    print(f"got {len(ohlcv)} real bars, {ohlcv.index.min()} to {ohlcv.index.max()}")

    periods_per_year = PERIODS_PER_YEAR.get(args.interval, 365)
    strategies = [SmaCrossover(), RsiReversion(), DonchianBreakout()]

    for strategy in strategies:
        result = run_backtest(ohlcv, strategy, DEFAULT_CONFIG, periods_per_year)
        m = result.metrics
        verdict = "PASS" if passes_honest_bar(result) else "fail"
        print(
            f"\n[{verdict}] {strategy.name}\n"
            f"  trades={m.num_trades} total_return={m.total_return:.2%} "
            f"sharpe={m.sharpe:.2f} max_drawdown={m.max_drawdown:.2%} "
            f"win_rate={m.win_rate:.2%} profit_factor={m.profit_factor:.2f}"
        )


if __name__ == "__main__":
    main()
