from datetime import datetime, timezone

from trading_bot.portfolio import Portfolio


def test_winning_long_trade_credits_exact_pnl_net_of_costs():
    p = Portfolio(starting_balance=10_000)
    now = datetime.now(timezone.utc)
    p.open_position("BTCUSDT", "long", qty=0.1, fill_price=100.0, fee=1.0, timestamp=now)
    assert p.cash == 10_000 - 10.0 - 1.0  # notional + fee reserved
    p.add_funding("BTCUSDT", -0.05)  # paid funding while open (negative = cost)
    trade = p.close_position("BTCUSDT", fill_price=110.0, fee=1.1, timestamp=now)
    assert trade.gross_pnl == (110.0 - 100.0) * 0.1
    assert trade.net_pnl == trade.gross_pnl - 1.0 - 1.1 - 0.05
    assert "BTCUSDT" not in p.positions


def test_losing_trade_is_recorded_truthfully_not_rounded_away():
    p = Portfolio(starting_balance=10_000)
    now = datetime.now(timezone.utc)
    p.open_position("BTCUSDT", "long", qty=1.0, fill_price=100.0, fee=0.1, timestamp=now)
    trade = p.close_position("BTCUSDT", fill_price=90.0, fee=0.09, timestamp=now)
    assert trade.gross_pnl == -10.0
    assert trade.net_pnl < -10.0  # loss plus fees, never hidden or floored at 0
    assert p.cash < p.starting_balance


def test_short_trade_profits_when_price_falls():
    p = Portfolio(starting_balance=10_000)
    now = datetime.now(timezone.utc)
    p.open_position("BTCUSDT", "short", qty=1.0, fill_price=100.0, fee=0.1, timestamp=now)
    trade = p.close_position("BTCUSDT", fill_price=90.0, fee=0.09, timestamp=now)
    assert trade.gross_pnl == 10.0


def test_blowup_detection_and_reset_keeps_trade_history():
    p = Portfolio(starting_balance=1000)
    now = datetime.now(timezone.utc)
    p.open_position("X", "long", qty=1000, fill_price=1.0, fee=0.0, timestamp=now)  # all-in
    p.close_position("X", fill_price=0.05, fee=0.0, timestamp=now)  # brutal loss
    assert p.is_blown_up({}, blowup_fraction=0.20)
    trades_before = len(p.closed_trades)
    p.reset()
    assert p.cash == p.starting_balance
    assert p.bust_count == 1
    assert len(p.closed_trades) == trades_before  # history is never erased
