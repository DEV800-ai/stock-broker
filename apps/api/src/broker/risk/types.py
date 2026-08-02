"""Pure data types for the risk policy engine.

These are plain dataclasses, not ORM models — the engine is decoupled from the
DB so it can be unit-tested without a database and reused once order_previews
exists (a later milestone) by mapping that row onto TradeProposal.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class TradeProposal:
    ticker: str
    action: str  # BUY|SELL
    order_type: str  # LIMIT|MARKET
    shares: int
    limit_price: float | None
    estimated_value: float  # shares * limit_price (or best estimate)
    sector: str | None = None
    thesis_id: int | None = None
    uses_margin: bool = False
    is_short: bool = False
    is_option: bool = False


@dataclass
class PortfolioState:
    net_liquidation: float
    cash: float
    # ticker -> current market value of that position
    position_values: dict[str, float] = field(default_factory=dict)
    # sector -> current market value held in that sector
    sector_values: dict[str, float] = field(default_factory=dict)
    realized_pnl_today: float = 0.0
    realized_pnl_week: float = 0.0


@dataclass
class RiskPolicyParams:
    max_position_pct: float = 0.05
    max_sector_pct: float = 0.25
    max_daily_loss_pct: float = 0.03
    max_weekly_loss_pct: float = 0.08
    min_avg_daily_volume: float = 500_000
    earnings_blackout_days: int = 2
    allow_trade_before_earnings: bool = False
    cooldown_rejections_threshold: int = 2
    cooldown_losses_threshold: int = 2


@dataclass
class RiskContext:
    proposal: TradeProposal
    portfolio: PortfolioState
    policy: RiskPolicyParams
    has_thesis: bool
    autonomy_mode: str = "preview_required"  # research_only|paper_only|preview_required
    is_killed: bool = False
    kill_reason: str | None = None
    earnings_date: date | None = None
    today: date | None = None
    avg_daily_volume: float | None = None
    recent_rejections: int = 0
    recent_losses: int = 0


@dataclass
class RuleResult:
    rule: str
    passed: bool
    reason: str
    # what this failure implies for the verdict if it fails
    severity: str = "block"  # block|paper_only|needs_smaller_size|needs_manual_review


@dataclass
class RiskEvaluation:
    verdict: str  # approved|blocked|needs_manual_review|needs_smaller_size|paper_only
    results: list[RuleResult]

    @property
    def failed(self) -> list[RuleResult]:
        return [r for r in self.results if not r.passed]
