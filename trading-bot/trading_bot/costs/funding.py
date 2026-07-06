from dataclasses import dataclass
from typing import Optional

from trading_bot.config import FundingConfig


@dataclass(frozen=True)
class FundingCharge:
    rate: float
    amount: float
    source: str  # "exchange" (real fetched rate) or "estimate" (documented fallback formula)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_funding_rate(premium_index: float, cfg: FundingConfig) -> float:
    """
    Reconstructs the Binance funding-rate formula for when a live funding
    rate can't be fetched: clamp(premium_index, +/-0.05%) + fixed interest,
    capped at +/-0.3% per 8h interval. This is a documented approximation,
    it is labeled as such by the caller (source="estimate"), never presented
    as a fetched, exchange-reported number.
    """
    clamped_premium = clamp(premium_index, -cfg.premium_clamp, cfg.premium_clamp)
    rate = clamped_premium + cfg.interest_rate_per_interval
    return clamp(rate, -cfg.rate_cap, cfg.rate_cap)


def apply_funding(
    position_notional: float,
    is_long: bool,
    cfg: FundingConfig,
    live_rate: Optional[float] = None,
    premium_index: Optional[float] = None,
) -> FundingCharge:
    """
    Charges (or pays) funding on an open perpetual-style position.
    Longs pay shorts when the rate is positive, and vice versa - that is
    real Binance mechanics, not a simplification.

    Pass `live_rate` when you fetched the real rate from the exchange
    (GET /fapi/v1/fundingRate). Only fall back to `premium_index` +
    the documented formula when no live rate is available.
    """
    if live_rate is not None:
        rate, source = live_rate, "exchange"
    elif premium_index is not None:
        rate, source = estimate_funding_rate(premium_index, cfg), "estimate"
    else:
        raise ValueError("apply_funding needs either live_rate or premium_index")

    sign = 1 if is_long else -1
    amount = -sign * rate * abs(position_notional)
    return FundingCharge(rate=rate, amount=amount, source=source)
