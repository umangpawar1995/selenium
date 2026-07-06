from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Metrics:
    total_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int


def sharpe_ratio(period_returns: pd.Series, periods_per_year: float) -> float:
    """Standard annualized Sharpe with 0% risk-free rate, an explicit,
    labeled simplification rather than an invented number."""
    std = period_returns.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(period_returns.mean() / std * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: pd.Series) -> float:
    running_peak = equity_curve.cummax()
    drawdown = (equity_curve - running_peak) / running_peak
    return float(drawdown.min())


def win_rate(trade_pnls: List[float]) -> float:
    if not trade_pnls:
        return 0.0
    wins = sum(1 for pnl in trade_pnls if pnl > 0)
    return wins / len(trade_pnls)


def profit_factor(trade_pnls: List[float]) -> float:
    gains = sum(pnl for pnl in trade_pnls if pnl > 0)
    losses = -sum(pnl for pnl in trade_pnls if pnl < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def compute_metrics(
    equity_curve: pd.Series, trade_pnls: List[float], periods_per_year: float
) -> Metrics:
    period_returns = equity_curve.pct_change().dropna()
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) if len(equity_curve) > 1 else 0.0
    return Metrics(
        total_return=total_return,
        sharpe=sharpe_ratio(period_returns, periods_per_year),
        max_drawdown=max_drawdown(equity_curve),
        win_rate=win_rate(trade_pnls),
        profit_factor=profit_factor(trade_pnls),
        num_trades=len(trade_pnls),
    )
