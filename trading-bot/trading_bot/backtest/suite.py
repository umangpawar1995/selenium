from typing import List

import pandas as pd

from trading_bot.backtest.backtester import BacktestResult, run_backtest
from trading_bot.config import BotConfig
from trading_bot.strategies.registry import STRATEGIES


def run_all_strategies(ohlcv: pd.DataFrame, cfg: BotConfig, periods_per_year: float) -> List[BacktestResult]:
    """Runs every registered strategy over the same real history so they can
    be compared side by side - add a strategy to the registry and it shows
    up here automatically."""
    return [run_backtest(ohlcv, factory(), cfg, periods_per_year) for factory in STRATEGIES.values()]
