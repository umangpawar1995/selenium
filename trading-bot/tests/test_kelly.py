from trading_bot.config import DEFAULT_CONFIG
from trading_bot.sizing.kelly import kelly_fraction, estimate_from_trades


def test_kelly_fraction_formula():
    # 60% win rate, 1:1 payoff -> f* = 0.6 - 0.4/1 = 0.2
    assert abs(kelly_fraction(0.6, 1.0) - 0.2) < 1e-9


def test_kelly_fraction_zero_payoff_ratio_is_zero():
    assert kelly_fraction(0.9, 0.0) == 0.0


def test_estimate_from_trades_uses_fixed_warmup_size_for_tiny_samples():
    cfg = DEFAULT_CONFIG.kelly
    pnls = [10, -5, 10, -5]  # far fewer than min_trades_for_estimate
    est = estimate_from_trades(pnls, cfg)
    assert est.basis == "warmup_fixed_size"
    assert est.sized_fraction == cfg.warmup_fraction


def test_estimate_from_trades_sizes_from_real_history():
    cfg = DEFAULT_CONFIG.kelly
    pnls = ([10.0] * 15 + [-5.0] * 10)  # 25 trades, 60% win rate, 2:1 payoff
    est = estimate_from_trades(pnls, cfg)
    assert est.basis == "trade_history"
    assert est.win_rate == 0.6
    assert abs(est.win_loss_ratio - 2.0) < 1e-9
    expected_full_kelly = 0.6 - 0.4 / 2.0  # 0.4
    assert abs(est.full_kelly - expected_full_kelly) < 1e-9
    assert abs(est.sized_fraction - expected_full_kelly * cfg.fraction) < 1e-9


def test_estimate_from_trades_never_sizes_a_negative_edge():
    cfg = DEFAULT_CONFIG.kelly
    pnls = [10.0] * 5 + [-20.0] * 20  # bad strategy: mostly losses, small wins
    est = estimate_from_trades(pnls, cfg)
    assert est.full_kelly < 0
    assert est.sized_fraction == 0.0
