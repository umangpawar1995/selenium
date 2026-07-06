"""
A minimal, dependency-free local dashboard. It only ever reads the
portfolio/runner state that the honest engine already computed - it does
not compute or format any number itself, so it can't quietly present a
number the ledger didn't produce.

The controller lets you pick a symbol/exchange/strategy from the browser
and start/stop paper trading, instead of running a separate command per
combination.
"""

from flask import Flask, jsonify, render_template, request

from trading_bot.dashboard.controller import BotController


def create_app(controller: BotController) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", strategies=controller.available_strategies())

    @app.get("/api/state")
    def state():
        if not controller.is_running():
            return jsonify({"running": False, "current": None})

        runner = controller.runner
        portfolio = runner.portfolio
        mark_prices = runner.broker.mark_to_market(list(runner.assignments))
        equity = portfolio.equity(mark_prices)

        return jsonify({
            "running": True,
            "current": controller.current,
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

    @app.get("/api/strategies")
    def strategies():
        return jsonify({"strategies": controller.available_strategies()})

    @app.post("/api/backtest")
    def backtest():
        body = request.get_json(force=True)
        try:
            results = controller.backtest(
                symbol=body["symbol"],
                source=body["source"],
                interval=body.get("interval", "1d"),
                days=int(body.get("days", 365)),
            )
            return jsonify({"ok": True, "results": results})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/start")
    def start():
        body = request.get_json(force=True)
        try:
            controller.start(
                symbol=body["symbol"],
                source=body["source"],
                strategy_name=body["strategy"],
                interval=body.get("interval", "1h"),
                perpetual=bool(body.get("perpetual", False)),
            )
            return jsonify({"ok": True, "current": controller.current})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/stop")
    def stop():
        controller.stop()
        return jsonify({"ok": True})

    return app
