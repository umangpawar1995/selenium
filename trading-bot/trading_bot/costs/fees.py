from trading_bot.config import FeeConfig


def taker_fee(notional: float, cfg: FeeConfig) -> float:
    """Fee charged for a market (taker) fill, in the same currency as notional."""
    return abs(notional) * cfg.spot_taker_fee


def maker_fee(notional: float, cfg: FeeConfig) -> float:
    """Fee charged for a resting (maker) fill, in the same currency as notional."""
    return abs(notional) * cfg.spot_maker_fee
