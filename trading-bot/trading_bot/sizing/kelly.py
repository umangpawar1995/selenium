from dataclasses import dataclass
from typing import List, Optional

from trading_bot.config import KellyConfig


@dataclass(frozen=True)
class KellyEstimate:
    win_rate: float
    win_loss_ratio: float
    full_kelly: float
    sized_fraction: float  # full_kelly * cfg.fraction, clamped to [0, 1]
    basis: str  # "trade_history" or "warmup_fixed_size"


def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """
    f* = p - q/b, the classic Kelly formula (b = payoff ratio, p = win
    probability, q = 1-p). Confirmed against standard references.
    """
    if win_loss_ratio <= 0:
        return 0.0
    q = 1 - win_rate
    return win_rate - q / win_loss_ratio


def estimate_from_trades(trade_pnls: List[float], cfg: KellyConfig) -> KellyEstimate:
    """
    Sizes off the strategy's own realized trade history. If there aren't
    enough closed trades yet to estimate win rate/payoff honestly, no edge
    is invented from a tiny sample - it uses the fixed, small `warmup_fraction`
    instead (basis = "warmup_fixed_size") purely so the bot can accumulate a
    real trade history, until enough trades exist to size off actual Kelly math.
    """
    if len(trade_pnls) < cfg.min_trades_for_estimate:
        return KellyEstimate(
            win_rate=0.0,
            win_loss_ratio=0.0,
            full_kelly=0.0,
            sized_fraction=cfg.warmup_fraction,
            basis="warmup_fixed_size",
        )

    wins = [pnl for pnl in trade_pnls if pnl > 0]
    losses = [-pnl for pnl in trade_pnls if pnl < 0]
    win_rate = len(wins) / len(trade_pnls)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    full_kelly = kelly_fraction(win_rate, win_loss_ratio)
    # a negative f* means no edge - refuse to short-size a real bet from it
    sized = max(0.0, full_kelly) * cfg.fraction
    sized = min(sized, 1.0)  # never leverage beyond the paper account's own equity
    return KellyEstimate(
        win_rate=win_rate,
        win_loss_ratio=win_loss_ratio,
        full_kelly=full_kelly,
        sized_fraction=sized,
        basis="trade_history",
    )
