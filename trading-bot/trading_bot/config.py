"""
Every number in here is either a documented exchange rule or an explicit,
labeled assumption. Nothing is invented and passed off as a fact.

Sources checked 2026-07-06:
  - Binance spot fee (base tier, no BNB discount): 0.1% maker / 0.1% taker.
    https://www.binance.com/en/fee/spotMaker
  - Binance USDS-M futures funding: settles every 8h at 00:00/08:00/16:00 UTC.
    Funding rate = clamp(premium index, -0.05%, +0.05%) + interest rate
    (0.01% per 8h interval for most pairs), capped at +/-0.3% per interval.
    https://www.binance.com/en/support/faq/detail/360033525031
    https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
  - Kelly criterion: f* = p - q/b  (b = win/loss payoff ratio, p = win rate,
    q = 1-p). Half-Kelly (fraction=0.5) is the common professional default
    because it captures most of the growth rate with much less drawdown.
    https://www.litefinance.org/blog/for-beginners/best-technical-indicators/kelly-criterion-trading/
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeeConfig:
    # Binance spot, standard (VIP0) tier, no BNB discount applied.
    spot_taker_fee: float = 0.001   # 0.1%
    spot_maker_fee: float = 0.001   # 0.1%


@dataclass(frozen=True)
class FundingConfig:
    interval_hours: int = 8
    # Fixed interest-rate component Binance adds on top of the premium index.
    interest_rate_per_interval: float = 0.0001   # 0.01% per 8h (~0.03%/day)
    # Binance dampens the premium index into this band before adding interest.
    premium_clamp: float = 0.0005                # +/- 0.05%
    # Hard ceiling/floor on the combined rate for a single interval.
    rate_cap: float = 0.003                      # +/- 0.3%


@dataclass(frozen=True)
class SlippageConfig:
    # Fills are simulated by crossing the *real* top-of-book spread:
    # buys fill at the live ask, sells fill at the live bid. When a live
    # order book isn't available (e.g. delayed stock quotes), this fraction
    # of the last known spread is used as a documented fallback estimate,
    # never a fabricated fill price.
    fallback_spread_pct_of_price: float = 0.0005  # 0.05%, conservative estimate


@dataclass(frozen=True)
class KellyConfig:
    # Half-Kelly: professionals commonly run 0.25-0.5x full Kelly to trade
    # off growth rate against drawdown risk from estimation error.
    fraction: float = 0.5
    min_trades_for_estimate: int = 20  # don't size off a tiny, noisy sample
    # Fixed, deliberately small bet used only during warm-up (before enough
    # trades exist to estimate a real edge) so the bot can bootstrap a trade
    # history at all. It is not a Kelly output and is never confused with one.
    warmup_fraction: float = 0.02


@dataclass(frozen=True)
class BotConfig:
    # This is fake paper money. It is never sent to a broker.
    starting_balance: float = 10_000.00
    currency: str = "USD"
    # Reset-and-learn: if the paper account's equity falls below this
    # fraction of the starting balance, the run is logged as a bust,
    # lessons are appended to the ledger, and the balance resets so the
    # bot keeps learning instead of sitting dead at zero.
    blowup_fraction: float = 0.20

    fees: FeeConfig = field(default_factory=FeeConfig)
    funding: FundingConfig = field(default_factory=FundingConfig)
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    kelly: KellyConfig = field(default_factory=KellyConfig)


DEFAULT_CONFIG = BotConfig()
