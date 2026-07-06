"""
A minimal, dependency-free local dashboard. It only ever reads the
portfolio/runner state that the honest engine already computed - it does
not compute or format any number itself, so it can't quietly present a
number the ledger didn't produce.
"""

from flask import Flask, jsonify, render_template

from trading_bot.bot.runner import PaperTradingRunner


def create_app(runner: PaperTradingRunner) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def state():
        portfolio = runner.portfolio
        mark_prices = runner.broker.mark_to_market(list(runner.assignments))
        equity = portfolio.equity(mark_prices)

        return jsonify({
            "starting_balance": portfolio.starting_balance,
            "cash": portfolio.cash,
            "equity": equity,
            "bust_count": portfolio.bust_count,
            "equity_history": [
                {"t": ts.isoformat(), "equity": eq} for ts, eq in portfolio.equity_history[-500:]
            ],
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": p.side,
                    "qty": p.qty,
                    "entry_price": p.entry_price,
                    "mark_price": mark_prices.get(p.symbol),
                    "funding_paid": p.funding_paid,
                }
                for p in portfolio.positions.values()
            ],
            "recent_trades": [
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "net_pnl": t.net_pnl,
                    "exit_time": t.exit_time.isoformat(),
                }
                for t in portfolio.closed_trades[-50:]
            ],
            "lessons": [
                {
                    "timestamp": lesson.timestamp.isoformat(),
                    "bust_count": lesson.bust_count,
                    "trades_so_far": lesson.trades_so_far,
                    "win_rate_so_far": lesson.win_rate_so_far,
                }
                for lesson in runner.lessons[-20:]
            ],
        })

    return app
