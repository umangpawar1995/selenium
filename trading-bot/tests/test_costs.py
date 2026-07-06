from trading_bot.config import DEFAULT_CONFIG
from trading_bot.costs.fees import taker_fee, maker_fee
from trading_bot.costs.funding import apply_funding, estimate_funding_rate, clamp
from trading_bot.costs.slippage import fill_price


def test_taker_fee_matches_binance_rate():
    assert taker_fee(10_000, DEFAULT_CONFIG.fees) == 10.0  # 0.1% of 10,000


def test_maker_fee_matches_binance_rate():
    assert maker_fee(10_000, DEFAULT_CONFIG.fees) == 10.0


def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-5, 0, 3) == 0
    assert clamp(2, 0, 3) == 2


def test_estimate_funding_rate_clamps_premium_before_adding_interest():
    cfg = DEFAULT_CONFIG.funding
    # huge premium gets clamped to +/-0.05% before the fixed interest is added
    rate = estimate_funding_rate(premium_index=10.0, cfg=cfg)
    assert rate == cfg.premium_clamp + cfg.interest_rate_per_interval


def test_estimate_funding_rate_caps_extreme_combined_rate():
    cfg = DEFAULT_CONFIG.funding
    # even with premium clamped, a config with a low cap must still bind
    from dataclasses import replace
    tight_cfg = replace(cfg, rate_cap=0.0003)
    rate = estimate_funding_rate(premium_index=10.0, cfg=tight_cfg)
    assert rate == tight_cfg.rate_cap


def test_apply_funding_long_pays_when_rate_positive():
    cfg = DEFAULT_CONFIG.funding
    charge = apply_funding(position_notional=10_000, is_long=True, cfg=cfg, live_rate=0.0001)
    assert charge.amount < 0  # long pays out
    assert charge.source == "exchange"
    assert abs(charge.amount) == 1.0  # 0.01% of 10,000


def test_apply_funding_short_receives_when_rate_positive():
    cfg = DEFAULT_CONFIG.funding
    charge = apply_funding(position_notional=10_000, is_long=False, cfg=cfg, live_rate=0.0001)
    assert charge.amount > 0  # short receives


def test_apply_funding_requires_a_rate_source():
    cfg = DEFAULT_CONFIG.funding
    try:
        apply_funding(position_notional=10_000, is_long=True, cfg=cfg)
        assert False, "should have raised"
    except ValueError:
        pass


def test_fill_price_crosses_real_book():
    cfg = DEFAULT_CONFIG.slippage
    buy = fill_price("buy", last_price=100, cfg=cfg, bid=99.9, ask=100.1)
    sell = fill_price("sell", last_price=100, cfg=cfg, bid=99.9, ask=100.1)
    assert buy.price == 100.1 and buy.source == "book"
    assert sell.price == 99.9 and sell.source == "book"


def test_fill_price_falls_back_to_documented_estimate_without_a_book():
    cfg = DEFAULT_CONFIG.slippage
    buy = fill_price("buy", last_price=100, cfg=cfg)
    sell = fill_price("sell", last_price=100, cfg=cfg)
    assert buy.source == "estimate" and buy.price > 100
    assert sell.source == "estimate" and sell.price < 100
