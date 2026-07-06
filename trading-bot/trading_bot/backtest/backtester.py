from dataclasses import dataclass
from typing import List

import pandas as pd

from trading_bot.backtest.metrics import Metrics, compute_metrics
from trading_bot.config import BotConfig
from trading_bot.costs.fees import taker_fee
from trading_bot.costs.slippage import fill_price
from trading_bot.strategies.base import Strategy


@dataclass
class BacktestTrade:
    side: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    net_pnl: float


@dataclass
class BacktestResult:
    strategy_name: str
    equity_curve: pd.Series
    trades: List[BacktestTrade]
    metrics: Metrics


def run_backtest(
    ohlcv: pd.DataFrame,
    strategy: Strategy,
    cfg: BotConfig,
    periods_per_year: float,
) -> BacktestResult:
    """
    Runs `strategy` over real historical OHLCV bars, re-investing the full
    paper balance into each new position. Every entry/exit pays the real
    documented taker fee and crosses a spread - since free historical order
    books aren't available, the documented fallback slippage estimate is
    used consistently here (never a live book, so never labeled as one).
    """
    signal = strategy.signal(ohlcv)
    equity = cfg.starting_balance
    equity_curve = []
    trades: List[BacktestTrade] = []

    state = 0.0
    entry_price = None
    entry_time = None
    qty = 0.0

    closes = ohlcv["close"]
    for t, price in closes.items():
        target = signal.loc[t]

        if target != state and state != 0.0:
            # close existing position
            side = "sell" if state == 1.0 else "buy"
            fill = fill_price(side, price, cfg.slippage)
            exit_fee = taker_fee(qty * fill.price, cfg.fees)
            gross = state * qty * (fill.price - entry_price)
            equity += gross - exit_fee
            trades.append(
                BacktestTrade(
                    side="long" if state == 1.0 else "short",
                    entry_time=entry_time,
                    exit_time=t,
                    entry_price=entry_price,
                    exit_price=fill.price,
                    net_pnl=gross - exit_fee,
                )
            )
            state = 0.0
            qty = 0.0

        if target != 0.0 and state == 0.0:
            side = "buy" if target == 1.0 else "sell"
            fill = fill_price(side, price, cfg.slippage)
            entry_fee = taker_fee(equity, cfg.fees)
            qty = (equity - entry_fee) / fill.price
            equity -= entry_fee
            entry_price = fill.price
            entry_time = t
            state = target

        mark = equity if state == 0.0 else equity + state * qty * (price - entry_price)
        equity_curve.append(mark)

    # close out any position still open at the end of the data window
    if state != 0.0:
        last_time = closes.index[-1]
        last_price = closes.iloc[-1]
        side = "sell" if state == 1.0 else "buy"
        fill = fill_price(side, last_price, cfg.slippage)
        exit_fee = taker_fee(qty * fill.price, cfg.fees)
        gross = state * qty * (fill.price - entry_price)
        equity += gross - exit_fee
        trades.append(
            BacktestTrade(
                side="long" if state == 1.0 else "short",
                entry_time=entry_time,
                exit_time=last_time,
                entry_price=entry_price,
                exit_price=fill.price,
                net_pnl=gross - exit_fee,
            )
        )
        equity_curve[-1] = equity

    equity_series = pd.Series(equity_curve, index=ohlcv.index)
    metrics = compute_metrics(equity_series, [t.net_pnl for t in trades], periods_per_year)
    return BacktestResult(
        strategy_name=strategy.name, equity_curve=equity_series, trades=trades, metrics=metrics
    )


def passes_honest_bar(result: BacktestResult, min_trades: int = 10) -> bool:
    """
    A strategy only "passes" if it clears every one of these, net of real
    costs - anything less and it gets reported as failing, not massaged.
    """
    m = result.metrics
    return (
        m.num_trades >= min_trades
        and m.total_return > 0
        and m.sharpe > 0
        and m.max_drawdown > -0.5
        and m.profit_factor > 1.0
    )
