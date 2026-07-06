#!/usr/bin/env python3
"""
Launches the dashboard at http://127.0.0.1:5000 - pick an exchange, symbol,
and strategy in the browser and click Start. No per-run command-line flags
needed anymore; --symbol/--source/--strategy below only pre-fill an
automatic start if you still want to launch straight from the terminal.
"""

import argparse
import logging

from trading_bot.dashboard.app import create_app
from trading_bot.dashboard.controller import BotController

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--source", choices=["binance", "yahoo"])
    parser.add_argument("--strategy")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--perpetual", action="store_true", help="charge funding (crypto perp only)")
    args = parser.parse_args()

    controller = BotController()
    if args.symbol and args.source and args.strategy:
        controller.start(
            symbol=args.symbol, source=args.source, strategy_name=args.strategy,
            interval=args.interval, perpetual=args.perpetual,
        )

    app = create_app(controller)
    print("dashboard: http://127.0.0.1:5000")
    app.run(port=5000)


if __name__ == "__main__":
    main()
