# paper trading bot

A simulation trading bot: real live prices, fake money, honest mechanics.
Built from the fabrichhhhh "Your AI Trading Bot With Claude" guide.

**The one rule this bot lives by: never fake a fill, a price, or a profit.**
It has no secret edge. It will lose trades, and if a strategy has no real
edge it will sometimes blow up the whole paper balance - and it is built to
show you that truthfully.

## What's in here

```
trading_bot/
  config.py           every fee/funding/kelly constant, each with a source
  data_feed/          real prices: Binance (crypto) and yfinance (stocks)
  costs/              fee, funding-rate, and slippage models
  portfolio.py        the fake-money ledger (cash, positions, trade log)
  broker.py           opens/closes positions against real quotes + costs
  strategies/         SMA crossover, RSI reversion, Donchian breakout
  backtest/           runs a strategy over real history, honest pass/fail bar
  sizing/kelly.py      fractional-Kelly position sizing from real trade history
  bot/runner.py        the live paper-trading loop + reset-and-learn on blowup
  dashboard/           local Flask dashboard (equity curve, positions, trades)
run_backtest.py        CLI: fetch real history, backtest all 3 strategies
run_bot.py              CLI: run the live paper loop + dashboard
tests/                  unit tests for every piece above
```

## Setup

```
pip install -r requirements.txt
```

## Backtest first

```
python run_backtest.py --symbol BTCUSDT --source binance --interval 1h --days 60
python run_backtest.py --symbol AAPL --source yahoo --interval 1d --days 365
```

Prints each strategy's real historical performance net of fees and slippage,
and whether it clears the honest pass bar (`num_trades >= 10`, positive
return, `Sharpe > 0`, `max_drawdown > -50%`, `profit_factor > 1`). A
strategy that doesn't clear this is reported as failing - it does not get
special-cased to look better.

## Run the paper bot

```
python run_bot.py --symbol BTCUSDT --source binance --strategy sma --perpetual
```

Then open http://127.0.0.1:5000 for the live dashboard (equity curve, open
positions, trade log, and the "lessons" banked each time the account resets
after a blowup).

## What every number is actually based on

Sources checked 2026-07-06 (see docstrings in `config.py`,
`costs/funding.py`, `sizing/kelly.py` for the same citations inline):

- **Spot fee**: Binance base-tier spot fee is 0.1% maker/taker.
  https://www.binance.com/en/fee/spotMaker
- **Funding**: Binance USDS-M perpetuals settle every 8h at 00:00/08:00/16:00
  UTC; rate = clamp(premium index, ±0.05%) + ~0.01% interest per interval,
  capped at ±0.3%. The bot fetches the *real* historical funding rate from
  `GET /fapi/v1/fundingRate` whenever possible; the formula above is only a
  documented, clearly-labeled fallback (`source="estimate"`), never
  presented as if it were a fetched number.
  https://www.binance.com/en/support/faq/detail/360033525031
- **Slippage**: fills cross the real bid/ask (buy at the live ask, sell at
  the live bid). If a live book isn't available, a documented fallback
  spread estimate is used and labeled `source="estimate"`.
- **RSI**: Wilder's RSI = 100 - 100/(1+RS), RS = avg gain / avg loss.
  https://chartschool.stockcharts.com
- **Donchian breakout**: long above the highest high of the last N bars,
  short below the lowest low. https://en.wikipedia.org/wiki/Donchian_channel
- **Kelly criterion**: f\* = p - q/b (p = win rate, q = 1-p, b = payoff
  ratio). The bot runs half-Kelly (`fraction=0.5`) since full Kelly is
  aggressive and highly sensitive to estimation error - a common
  professional default. Before a strategy has 20 real closed trades to
  estimate a win rate/payoff from, it uses a small fixed "warmup" size
  (2% of equity) instead of inventing an edge from too little data.

## Known limitation of this build environment

This bot was built and tested inside a sandboxed cloud container whose
network policy blocks outbound calls to arbitrary hosts (Binance, Yahoo
Finance, etc. all returned `403` on every attempt here). That means the
**37 unit tests all run and pass in this sandbox using scripted/synthetic
fixture data** (see `tests/fakes.py`, clearly never used by the real bot),
but the actual live network calls in `BinanceFeed`, `YahooFeed`,
`run_backtest.py`, and `run_bot.py` could not be exercised end-to-end here.
Run `python run_backtest.py ...` on your own machine first - if the
endpoints or response shapes have drifted since 2026-07-06, that's where
it'll surface.

## Risk, plainly

This is a simulation. It has no edge beyond whatever a simple SMA/RSI/
Donchian strategy has, net of real trading costs - historically, not much.
Paper-trade it for as long as you want; only point it at a real account if
you've watched it operate honestly for a while and understand you could
lose real money the same way it loses fake money here.
