#!/usr/bin/env python3
"""
Runs the paper-trading bot on real live prices with fake money, and serves
the dashboard at http://127.0.0.1:5000

Usage:
  python run_bot.py --symbol BTCUSDT --source binance --strategy sma --perpetual
  python run_bot.py --symbol AAPL --source yahoo --strategy rsi
"""

import argparse
import logging
import threading

from trading_bot.bot.runner import PaperTradingRunner, SymbolAssignment
from trading_bot.broker import PaperBroker
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.dashboard.app import create_app
from trading_bot.data_feed.binance_feed import BinanceFeed
from trading_bot.data_feed.yahoo_feed import YahooFeed
from trading_bot.portfolio import Portfolio
from trading_bot.strategies.breakout import DonchianBreakout
from trading_bot.strategies.rsi_reversion import RsiReversion
from trading_bot.strategies.sma_crossover import SmaCrossover

STRATEGIES = {"sma": SmaCrossover, "rsi": RsiReversion, "breakout": DonchianBreakout}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--source", choices=["binance", "yahoo"], required=True)
    parser.add_argument("--strategy", choices=list(STRATEGIES), required=True)
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--tick-seconds", type=float, default=60.0)
    parser.add_argument("--perpetual", action="store_true", help="charge funding (crypto perp only)")
    args = parser.parse_args()

    feed = BinanceFeed() if args.source == "binance" else YahooFeed()
    portfolio = Portfolio(starting_balance=DEFAULT_CONFIG.starting_balance)
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    assignment = SymbolAssignment(
        symbol=args.symbol,
        strategy=STRATEGIES[args.strategy](),
        history_interval=args.interval,
        is_perpetual=args.perpetual,
    )
    runner = PaperTradingRunner(broker, [assignment], DEFAULT_CONFIG)

    threading.Thread(target=runner.run_forever, args=(args.tick_seconds,), daemon=True).start()

    app = create_app(runner)
    print("dashboard: http://127.0.0.1:5000")
    app.run(port=5000)


if __name__ == "__main__":
    main()
