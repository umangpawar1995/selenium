from trading_bot.broker import PaperBroker
from trading_bot.config import DEFAULT_CONFIG
from trading_bot.portfolio import Portfolio
from tests.fakes import ScriptedFeed, quote


def test_open_then_close_one_honest_cycle():
    feed = ScriptedFeed({
        "BTCUSDT": [
            quote("BTCUSDT", price=50_000, bid=49_995, ask=50_005),
            quote("BTCUSDT", price=49_000, bid=48_995, ask=49_005),  # a real loss
        ]
    })
    portfolio = Portfolio(starting_balance=10_000)
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)

    broker.open("BTCUSDT", "long", notional_target=1_000)
    assert "BTCUSDT" in portfolio.positions
    pos = portfolio.positions["BTCUSDT"]
    assert pos.entry_price == 50_005  # filled at the real ask, not the mid

    trade = broker.close("BTCUSDT")
    assert trade.exit_price == 48_995  # filled at the real bid
    assert trade.gross_pnl < 0  # the price dropped - this must show as a loss
    assert trade.net_pnl < trade.gross_pnl  # fees make it worse, never better
    assert portfolio.cash < portfolio.starting_balance
    assert "BTCUSDT" not in portfolio.positions


def test_funding_charge_reduces_cash_for_long_when_rate_positive():
    feed = ScriptedFeed({"BTCUSDT": [quote("BTCUSDT", price=50_000, bid=49_995, ask=50_005)]})
    portfolio = Portfolio(starting_balance=10_000)
    broker = PaperBroker(feed, portfolio, DEFAULT_CONFIG)
    broker.open("BTCUSDT", "long", notional_target=1_000)
    cash_before = portfolio.cash
    broker.charge_funding("BTCUSDT", live_rate=0.0001)
    assert portfolio.cash < cash_before
    assert portfolio.positions["BTCUSDT"].funding_paid < 0  # negative = paid out
