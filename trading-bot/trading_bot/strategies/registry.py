"""
The single place that lists every strategy the bot knows about. The
dashboard's dropdown and the backtest CLI both read from this dict - to add
a new strategy, write the class (see strategies/base.py for the interface)
and add one line here. Nothing else needs to change.
"""

from typing import Callable, Dict

from trading_bot.strategies.base import Strategy
from trading_bot.strategies.breakout import DonchianBreakout
from trading_bot.strategies.rsi_reversion import RsiReversion
from trading_bot.strategies.sma_crossover import SmaCrossover

STRATEGIES: Dict[str, Callable[[], Strategy]] = {
    "sma_crossover": lambda: SmaCrossover(),
    "rsi_reversion": lambda: RsiReversion(),
    "donchian_breakout": lambda: DonchianBreakout(),
}
