# Signal Alpha — Product & Technical Design Document

**Status:** Draft for review
**Scope:** MVP (Phases 1–3 of the roadmap in `CLAUDE.md`)
**Audience:** Engineering, product, and anyone evaluating whether to fund Phase 3/4 work

---

## 1. Executive Summary

Signal Alpha is an **agentic trading control plane** — not a broker, not an auto-trader. It sits between market/news data, AI research agents, a deterministic risk engine, paper trading, and (eventually) broker execution via Interactive Brokers.

The product thesis: AI is good at reading, summarizing, and pattern-matching across noisy data (price action, news, filings). AI is bad at being trusted with irreversible financial decisions unsupervised. Signal Alpha's job is to let AI do the first job at scale while structurally preventing it from doing the second — via a risk policy engine that AI cannot bypass, a human approval gate that is mandatory in MVP, and an audit log that makes every decision explainable after the fact.

This is deliberately positioned against "AI auto-trading" products (e.g. Robinhood's agentic trading direction). Signal Alpha borrows the good ideas — scoped agent permissions, order previews, portfolio-aware AI, auditability — but treats human approval as the load-bearing safety mechanism, not a feature flag to be removed later.

The current codebase (`apps/api`) already implements a meaningful slice of this: a scanner with composite scoring, an AI thesis agent with caching via `input_hash`, a paper trading loop with approval gating (`pending_approval → open → closed`), and an `agent_runs` audit table. This document extends that foundation into the full MVP: news/filing intelligence, a real risk policy engine, portfolio context, order preview, and the IBKR execution path.

---

## 2. Product Concept

> **Signal Alpha is the scanner, research, risk, approval, and audit layer for trading agents.**

It is not:
> An AI that freely buys and sells stocks.

Every AI output in the product is a **proposal**, never an **action**. Actions require either (a) a human clicking approve, or (b) in future phases, a deterministic rule that was itself human-approved in advance. The AI never has a code path to broker execution that doesn't pass through the risk engine and the approval layer.

### 2.1 User Personas

**Primary: The Active Individual Investor ("Dana")**
Manages their own IBKR account, follows 20–50 tickers, spends 30–60 min/day on research. Wants leverage on the "reading everything" problem — news, filings, price action — without giving up control of the buy button. Technically comfortable but not a developer. Cares about *why*, not just *what*.

**Secondary: The Systematic Tinkerer ("Marcus")**
Wants to backtest and paper-trade signal ideas before trusting them with money. Will eventually want Rules-Based Auto mode. Cares about win rate, Sharpe, hit rate by signal type — the paper trading analytics matter more to this persona than the thesis prose.

**Tertiary (post-MVP): Small RIA / prop-adjacent user**
Needs multi-account support and stronger compliance/audit guarantees. Explicitly out of scope for MVP but the audit-log-as-first-class-feature design should not preclude it later.

### 2.2 Core Workflows

1. **Morning brief**: scanner runs overnight → composite scores → thesis agent generates theses for tickers above `thesis_min_score` → user opens Daily Market Brief.
2. **Research a ticker**: user reads bull/bear case, news digest, portfolio-impact note → decides Watch / Paper / Propose.
3. **Paper trade**: system (or user) opens a paper trade tied to a thesis → tracked to exit → thesis-validity and outcome scored.
4. **Propose live trade**: order preview generated → risk engine evaluates → if not blocked, enters Trade Approval Queue → human approves/rejects → approved order sent to IBKR → fill tracked → post-trade monitoring resumes against the original thesis.
5. **Weekly review**: paper trading performance report; scanner signal quality by type; thesis accuracy vs. realized outcome.

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │              Next.js Dashboard               │
                         │  (Daily Brief, Stock Detail, Approval Queue, │
                         │   Portfolio Digest, Paper Perf, Audit Log)   │
                         └───────────────────────┬───────────────────────┘
                                                  │ REST (+ WS for live updates)
                         ┌───────────────────────▼───────────────────────┐
                         │                 FastAPI (apps/api)             │
                         │  ┌───────────┐ ┌───────────┐ ┌──────────────┐  │
                         │  │  Routers   │ │  Agent     │ │  Risk Policy │  │
                         │  │ (REST API) │ │  Gateway   │ │   Engine     │  │
                         │  └───────────┘ └───────────┘ └──────────────┘  │
                         └──┬──────────────┬───────────────┬──────────────┘
                            │              │               │
           ┌────────────────┘   ┌──────────┘    ┌──────────┘
           ▼                    ▼               ▼
   ┌───────────────┐   ┌────────────────┐   ┌───────────────────┐
   │  Scanner       │   │  AI Agents      │   │  Broker Adapter    │
   │  (scheduled)   │   │  (thesis,       │   │  Interface          │
   │                │   │  portfolio,     │   │  ┌───────────────┐  │
   │  News/Filing   │   │  news classify) │   │  │ IBKR Adapter   │  │
   │  Ingestion     │   │                 │   │  └───────────────┘  │
   │  (scheduled)   │   │  Claude API     │   │  (future: others)   │
   └───────┬────────┘   └────────┬────────┘   └──────────┬─────────┘
           │                     │                        │
           └──────────┬──────────┴───────────┬────────────┘
                       ▼                      ▼
              ┌─────────────────┐   ┌──────────────────┐
              │   PostgreSQL     │   │   Redis           │
              │  (system of      │   │ (queues, cache,   │
              │   record)        │   │  session state)   │
              └─────────────────┘   └──────────────────┘
                       ▲
                       │
              ┌────────┴─────────┐
              │ Celery/Temporal   │
              │ workers: scan,    │
              │ ingest news,      │
              │ generate thesis,  │
              │ tickle IBKR,      │
              │ monitor paper     │
              │ trades, digests   │
              └───────────────────┘
```

### 3.2 Component Diagram (text form)

```
apps/api/src/broker/
├── main.py                    # FastAPI app
├── config.py                  # Settings (env-driven)
├── db.py                      # SQLAlchemy session/engine
│
├── models/                    # ORM models = system of record
│   ├── universe.py            # tradable ticker universe
│   ├── scan.py                # scan_runs, scan_results
│   ├── news.py                # news_items (NEW: event classification)
│   ├── thesis.py              # stock_theses, agent_runs (audit)
│   ├── watchlist.py
│   ├── paper_trade.py         # paper_trades
│   ├── portfolio.py           # (NEW) broker_accounts, positions_snapshot
│   ├── risk.py                # (NEW) risk_policies, risk_evaluations
│   └── order.py               # (NEW) order_previews, live_orders
│
├── scanner/
│   └── runner.py              # composite scoring job
│
├── news/                      # (NEW) news & filing intelligence
│   ├── sources/                # finnhub.py, edgar.py, gdelt.py, ...
│   ├── classifier.py           # event-type + sentiment classification
│   └── ingest.py                # scheduled ingestion job
│
├── ai/
│   ├── provider.py             # LLM provider abstraction (exists)
│   ├── thesis_agent.py         # exists — extend with news/portfolio context
│   ├── portfolio_agent.py      # (NEW) portfolio digest agent
│   └── schemas.py              # (NEW) strict JSON-schema output contracts
│
├── risk/                      # (NEW) deterministic risk policy engine
│   ├── engine.py                # rule evaluation, pure functions
│   ├── rules.py                 # rule definitions (position size, sector cap, ...)
│   └── kill_switch.py
│
├── broker/                    # (NEW) broker adapter layer
│   ├── base.py                  # BrokerAdapter ABC
│   ├── ibkr_adapter.py          # implements BrokerAdapter using data/ibkr.py client
│   └── paper_adapter.py         # simulated fills, no external calls
│
├── gateway/                   # (NEW) agent tool gateway (MCP-style)
│   ├── tools.py                  # tool registry with scoped permissions
│   └── audit.py                  # every tool call → audit_log row
│
├── data/
│   ├── ibkr.py                 # exists — low-level IBKR client
│   ├── finnhub.py, yfinance_data.py
│   └── universe_seed.py
│
└── routers/                   # REST surface (existing pattern extends)
    ├── health.py, scanner.py, watchlist.py, thesis.py, paper_trades.py
    ├── portfolio.py            # (NEW)
    ├── orders.py               # (NEW) preview + approval queue
    ├── risk.py                 # (NEW) policy CRUD, kill switch
    └── audit.py                # (NEW)
```

### 3.3 Data Flow: Scan → Approved Order

```
1. Scheduled scan job (Celery beat, e.g. every 15 min during market hours)
      → scanner/runner.py computes composite_score per ticker
      → writes scan_runs / scan_results

2. News ingestion job (continuous / polling)
      → news/sources/*.py pull from Finnhub, EDGAR, GDELT, etc.
      → news/classifier.py assigns event_type, sentiment, impact, confidence
      → writes news_items, linked to ticker

3. Thesis trigger
      → for scan_results.composite_score > settings.thesis_min_score
      → check agent_runs.input_hash (ticker+date+signals) — skip if cached
      → ai/thesis_agent.py assembles context: scan signals + news_items + peers
      → calls Claude via ai/provider.py with a strict JSON schema
      → writes stock_theses + agent_runs (full input/output logged)

4. User reviews Daily Market Brief / Stock Detail page
      → selects: Watch | Paper Trade | Propose for Approval

5a. Paper trade path
      → routers/paper_trades.py creates paper_trades row (status=pending_appron... 
        or auto-opens per user setting)
      → scanner's daily job marks target/stop hits, closes trades, computes pnl

5b. Live trade path (Preview Required mode — the only live mode in MVP)
      → ai/thesis_agent.py or user manually requests propose_trade via gateway
      → gateway/tools.py: propose_trade → preview_order
      → order preview assembled: ticker, action, size, order_type, reason,
        bull/bear case, portfolio_impact (calls ai/portfolio_agent.py), risk_status
      → risk/engine.py evaluates preview against active risk_policies
           → outputs: approved | blocked | needs_manual_review | needs_smaller_size | paper_only
      → if not blocked: order_previews row created, appears in Trade Approval Queue
      → human clicks Approve (with optional size override) or Reject
      → on approval: broker/ibkr_adapter.py places order via IBKR Client Portal API
      → order status polled/streamed → live_orders row updated with fills
      → post-trade: paper_trades-style monitoring reattaches to the thesis,
        tracks whether thesis assumptions still hold (price, news, catalyst dates)

6. Every step above writes to agent_runs / audit_log — nothing is fire-and-forget.
```

---

## 4. Backend Services

Kept as a modular monolith (single FastAPI app + Celery workers) for MVP — a services split is premature at this scale and adds deployment/ops burden the team doesn't need yet (Railway single-Postgres deployment per `CLAUDE.md`).

| Service | Responsibility | Trigger |
|---|---|---|
| API (FastAPI) | REST endpoints, request-scoped risk checks, approval actions | HTTP |
| Scanner worker | Composite scoring | Celery beat, every 15 min market hours |
| News ingestion worker | Pull + classify news/filings | Celery beat, every 5–15 min (source-dependent rate limits) |
| Thesis worker | Generate/cache theses for qualifying tickers | Triggered after scan completes, or on-demand |
| Portfolio sync worker | Pull IBKR positions/cash snapshot | Every 5 min market hours, or on trade approval |
| IBKR session keeper | `/tickle` every 60s (already exists) | Celery beat |
| Paper trade monitor | Mark target/stop hits, close trades, compute pnl | Every 5–15 min |
| Order status poller | Poll IBKR order status until terminal | On order placement, short-interval until filled/cancelled |
| Digest generator | Weekly performance review, daily brief precompute | Nightly / weekly cron |

Celery is sufficient for MVP (simpler than Temporal, team already has Redis). Revisit Temporal only if workflow branching/retry complexity around order lifecycle grows (e.g. multi-leg approval chains) — not justified pre-MVP.

---

## 5. Data Architecture

Extends the existing schema (`scan_runs`, `scan_results`, `stock_theses`, `agent_runs`, `paper_trades`, watchlist/universe tables) rather than replacing it.

### 5.1 New tables

```sql
-- News & filing intelligence
CREATE TABLE news_items (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(12) NOT NULL,
    source          VARCHAR(50) NOT NULL,          -- finnhub|edgar|gdelt|...
    source_id       VARCHAR(200),                   -- dedup key from source
    headline        TEXT NOT NULL,
    url             TEXT,
    published_at    TIMESTAMP NOT NULL,
    event_type      VARCHAR(50),                    -- earnings_beat, guidance_cut, ...
    sentiment       VARCHAR(20),                     -- positive|negative|neutral
    expected_impact VARCHAR(20),                     -- high|medium|low
    confidence      DOUBLE PRECISION,
    risk_flag       BOOLEAN DEFAULT FALSE,
    raw_json        JSONB,
    created_at      TIMESTAMP DEFAULT now()
);
CREATE UNIQUE INDEX ON news_items (source, source_id);
CREATE INDEX ON news_items (ticker, published_at);

-- Broker accounts & portfolio snapshots (read-only mirror of IBKR state)
CREATE TABLE broker_accounts (
    id              SERIAL PRIMARY KEY,
    broker          VARCHAR(20) NOT NULL,            -- ibkr
    account_id      VARCHAR(50) NOT NULL UNIQUE,
    account_type    VARCHAR(20) NOT NULL,             -- paper|live
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE portfolio_snapshots (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER REFERENCES broker_accounts(id),
    snapshot_at     TIMESTAMP NOT NULL,
    cash            DOUBLE PRECISION,
    net_liq         DOUBLE PRECISION,
    positions_json  JSONB NOT NULL,                   -- [{ticker, qty, avg_cost, mkt_value, unrealized_pnl, sector}]
    sector_exposure_json JSONB,                        -- {sector: pct_of_nlv}
    created_at      TIMESTAMP DEFAULT now()
);

-- Risk policy engine
CREATE TABLE risk_policies (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    rule_type       VARCHAR(50) NOT NULL,             -- max_position_size, max_sector_exposure, ...
    params_json     JSONB NOT NULL,                    -- {max_pct: 0.05} etc.
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE risk_evaluations (
    id              SERIAL PRIMARY KEY,
    order_preview_id INTEGER REFERENCES order_previews(id),
    verdict         VARCHAR(30) NOT NULL,             -- approved|blocked|needs_manual_review|needs_smaller_size|paper_only
    rule_results_json JSONB NOT NULL,                  -- per-rule pass/fail + reason
    created_at      TIMESTAMP DEFAULT now()
);

-- Order preview & live orders
CREATE TABLE order_previews (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(12) NOT NULL,
    thesis_id       INTEGER REFERENCES stock_theses(id),
    action          VARCHAR(10) NOT NULL,             -- BUY|SELL
    amount_usd      DOUBLE PRECISION,
    shares          INTEGER,
    order_type      VARCHAR(20) NOT NULL,              -- LIMIT|MARKET(disallowed by default)
    limit_price     DOUBLE PRECISION,
    time_in_force   VARCHAR(10) DEFAULT 'DAY',
    reason          TEXT NOT NULL,
    bull_case       TEXT,
    bear_case       TEXT,
    portfolio_impact TEXT,
    risk_status     VARCHAR(30),                        -- mirrors risk_evaluations.verdict
    approval_required BOOLEAN DEFAULT TRUE,
    status          VARCHAR(20) DEFAULT 'pending',       -- pending|approved|rejected|expired
    approved_by     VARCHAR(100),
    approved_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE live_orders (
    id              SERIAL PRIMARY KEY,
    order_preview_id INTEGER REFERENCES order_previews(id) NOT NULL,
    broker_order_id VARCHAR(100),
    account_id      INTEGER REFERENCES broker_accounts(id),
    status          VARCHAR(30) NOT NULL,                -- submitted|filled|partial|cancelled|rejected
    filled_qty      INTEGER DEFAULT 0,
    avg_fill_price  DOUBLE PRECISION,
    broker_response_json JSONB,
    submitted_at    TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT now()
);

-- Kill switch (single-row config, or per-account)
CREATE TABLE agent_control (
    id              SERIAL PRIMARY KEY,
    scope           VARCHAR(50) NOT NULL DEFAULT 'global', -- global|account:<id>
    autonomy_mode   VARCHAR(30) NOT NULL DEFAULT 'preview_required', -- research_only|paper_only|preview_required
    is_killed       BOOLEAN DEFAULT FALSE,
    killed_reason   TEXT,
    killed_at       TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT now()
);

-- Thesis validity tracking (post-trade / post-thesis monitoring)
CREATE TABLE thesis_checks (
    id              SERIAL PRIMARY KEY,
    thesis_id       INTEGER REFERENCES stock_theses(id) NOT NULL,
    checked_at      TIMESTAMP DEFAULT now(),
    still_valid     BOOLEAN,
    change_summary  TEXT,
    triggered_by    VARCHAR(50)                           -- scheduled|news_event|price_move
);
```

`agent_runs` already covers the "every AI call logged with input_hash + tokens" requirement — extend it, don't replace it. Add a generic `audit_log` table for non-AI actions (approvals, kill switch toggles, risk overrides) so the Audit Log dashboard view has one place to query:

```sql
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    actor           VARCHAR(100) NOT NULL,               -- user email or 'system'
    action          VARCHAR(50) NOT NULL,                 -- approve_order, reject_order, kill_switch_on, ...
    entity_type     VARCHAR(50),                           -- order_preview, paper_trade, risk_policy
    entity_id       INTEGER,
    details_json    JSONB,
    created_at      TIMESTAMP DEFAULT now()
);
```

### 5.2 Why not a separate audit DB / event store

For MVP, Postgres tables with append-only semantics (no UPDATE/DELETE on `agent_runs`/`audit_log` in application code) are sufficient. A true event-sourced ledger is over-engineering at this stage — revisit only if regulatory/compliance requirements demand tamper-evidence beyond DB-level access control.

---

## 6. Suggested APIs (REST surface)

Existing routers stay as-is. New/extended endpoints:

```
GET  /portfolio/summary                 → latest snapshot + risk digest
GET  /portfolio/digest                  → AI-generated portfolio digest (cached, regenerated on snapshot change)

POST /orders/preview                    → { ticker, action, amount|shares, order_type, limit_price, thesis_id? }
                                           returns OrderPreview + risk_status
GET  /orders/queue                      → pending order_previews needing approval
POST /orders/{id}/approve               → requires human auth; triggers broker placement
POST /orders/{id}/reject
GET  /orders/{id}                       → status incl. live_orders fill info

GET  /risk/policies
POST /risk/policies                     → create/update a rule (admin-only)
POST /risk/kill-switch                  → { on: bool, reason }
GET  /risk/kill-switch

GET  /news?ticker=&since=&event_type=
GET  /theses/{ticker}/checks            → thesis_checks history (did thesis stay valid)

GET  /audit?entity_type=&since=&actor=
GET  /performance/weekly                → paper trading metrics (win rate, Sharpe, hit rate by signal)
```

All mutating endpoints (`approve`, `reject`, `kill-switch`, `risk/policies` POST) require authenticated human session — never callable by the agent gateway directly (see §8).

---

## 7. Agent / Tool Interface Design (Agent Gateway)

MCP-style internal gateway. Every tool has an explicit permission scope, JSON-schema input/output, and is logged unconditionally — logging is not optional per-tool, it's enforced by the gateway dispatcher itself so no tool can be added that skips it.

```python
# gateway/tools.py (shape, not final code)

class ToolScope(str, Enum):
    READ_MARKET = "read_market"
    READ_PORTFOLIO = "read_portfolio"
    READ_NEWS = "read_news"
    PROPOSE = "propose"          # can create previews, cannot execute
    PAPER_EXECUTE = "paper_execute"
    LIVE_EXECUTE = "live_execute"  # gated: only reachable after human approval, never by agent directly
    ADMIN = "admin"

@dataclass
class ToolSpec:
    name: str
    scope: ToolScope
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    handler: Callable
    requires_risk_check: bool = False

TOOLS = {
    "read_market_data":   ToolSpec(scope=ToolScope.READ_MARKET, ...),
    "read_portfolio":     ToolSpec(scope=ToolScope.READ_PORTFOLIO, ...),
    "read_positions":     ToolSpec(scope=ToolScope.READ_PORTFOLIO, ...),
    "read_news":          ToolSpec(scope=ToolScope.READ_NEWS, ...),
    "scan_market":        ToolSpec(scope=ToolScope.READ_MARKET, ...),
    "generate_thesis":    ToolSpec(scope=ToolScope.PROPOSE, ...),
    "propose_trade":      ToolSpec(scope=ToolScope.PROPOSE, requires_risk_check=True, ...),
    "preview_order":      ToolSpec(scope=ToolScope.PROPOSE, requires_risk_check=True, ...),
    "place_paper_order":  ToolSpec(scope=ToolScope.PAPER_EXECUTE, ...),
    "request_live_approval": ToolSpec(scope=ToolScope.PROPOSE, ...),  # just queues it — never executes
    "place_live_order":   ToolSpec(scope=ToolScope.LIVE_EXECUTE, ...),  # NOT invocable by AI agent role in MVP
    "cancel_order":       ToolSpec(scope=ToolScope.LIVE_EXECUTE, ...),
    "get_audit_log":      ToolSpec(scope=ToolScope.READ_PORTFOLIO, ...),
    "disable_agent":      ToolSpec(scope=ToolScope.ADMIN, ...),
}
```

**Key design decision:** the AI agent's credential/role is only ever granted `READ_*` and `PROPOSE` scopes. `place_live_order` exists as a tool for architectural symmetry (so the approval-queue backend and a future rules-based-auto mode share one code path) but the AI's own tool-calling session has no scope that reaches it — approval is what elevates an `order_preview` into something `place_live_order` will act on, and that elevation only happens via the human-auth-gated REST endpoint, not via agent tool call. This is enforced at the gateway dispatcher level (scope check before handler invocation), not just by convention — don't rely on the AI "choosing" not to call it.

Every dispatch:
```python
def dispatch(tool_name: str, input: dict, caller_scopes: set[ToolScope]) -> dict:
    spec = TOOLS[tool_name]
    if spec.scope not in caller_scopes:
        raise PermissionError(...)
    validated_input = spec.input_schema.model_validate(input)
    if spec.requires_risk_check:
        risk_result = risk_engine.evaluate(validated_input)
    result = spec.handler(validated_input)
    audit_log.write(tool=tool_name, input=validated_input, output=result, risk=risk_result)
    return spec.output_schema.model_validate(result).model_dump()
```

---

## 8. Risk Policy Model

Deterministic, rule-based, no LLM in the loop. Rules are data (`risk_policies` table), the engine is pure code — this is the one part of the system that must be boring and fully unit-tested, since it's the actual safety boundary.

```python
# risk/rules.py (shape)

class RuleResult(BaseModel):
    rule: str
    passed: bool
    reason: str

def check_max_position_size(preview, portfolio, policy) -> RuleResult: ...
def check_max_sector_exposure(preview, portfolio, policy) -> RuleResult: ...
def check_max_daily_loss(preview, account_pnl_today, policy) -> RuleResult: ...
def check_no_margin(preview, portfolio) -> RuleResult: ...          # hard-coded, not configurable in MVP
def check_no_options(preview) -> RuleResult: ...                     # hard-coded
def check_no_shorting(preview) -> RuleResult: ...                    # hard-coded
def check_earnings_proximity(preview, calendar, policy) -> RuleResult: ...
def check_liquidity(preview, scan_result, policy) -> RuleResult: ...
def check_has_thesis(preview) -> RuleResult: ...
def check_cooldown(preview, recent_rejections_and_losses) -> RuleResult: ...
def check_kill_switch(agent_control) -> RuleResult: ...

RULES: list[Callable] = [check_kill_switch, check_no_margin, check_no_options,
                          check_no_shorting, check_has_thesis, check_liquidity,
                          check_max_position_size, check_max_sector_exposure,
                          check_max_daily_loss, check_earnings_proximity, check_cooldown]

def evaluate(preview, context) -> RiskEvaluation:
    results = [rule(preview, context) for rule in RULES]
    if any(r.rule == "kill_switch" and not r.passed for r in results):
        return RiskEvaluation(verdict="blocked", results=results)
    if any(not r.passed for r in [check_no_margin, check_no_options, check_no_shorting]):
        return RiskEvaluation(verdict="blocked", results=results)   # hard blocks, non-negotiable
    if not check_has_thesis(preview).passed:
        return RiskEvaluation(verdict="blocked", results=results)
    if any(not r.passed for r in [max_position_size_result, max_sector_exposure_result]):
        return RiskEvaluation(verdict="needs_smaller_size", results=results)
    if earnings_proximity_flagged or liquidity_marginal:
        return RiskEvaluation(verdict="needs_manual_review", results=results)
    return RiskEvaluation(verdict="approved", results=results)   # "approved" still requires human click in MVP —
                                                                   # this verdict means "eligible to enter the queue"
```

Important nuance: **"approved" by the risk engine ≠ order sent to broker.** In MVP (Preview Required mode), risk-engine "approved" only means the order preview is allowed to appear in the Trade Approval Queue. A human must still click Approve. This double-gate is intentional — the risk engine prevents obviously bad orders from ever reaching a human, and the human is the final authority on everything that remains. Only in the future Rules-Based Auto mode would "approved" by the risk engine be sufficient on its own, and that's explicitly out of MVP scope.

---

## 9. Execution Model — Manual TradingView, No Live Broker Integration

**Superseded from an earlier draft:** this section originally specified an
IBKR `BrokerAdapter` interface (`get_positions`, `place_order`,
`cancel_order`, etc.) with a Client Portal Gateway connection, intended to
extend to live execution in a later phase. That plan is dropped. Signal
Alpha never places, modifies, or cancels an order, and never connects to a
broker API — all IBKR code (`data/ibkr.py`, `execution/ibkr_adapter.py`,
`portfolio/ibkr_provider.py`) has been removed from the codebase. The
reasoning: IBKR's OAuth Web API is not currently approved for retail/
individual accounts (researched, not assumed), which would have forced the
local Client Portal Gateway's manual-2FA-on-every-startup dependency to
persist indefinitely — the single largest source of operational complexity
on the original roadmap. Dropping it removes that dependency entirely and
also simplifies the compliance posture (§12): Signal Alpha never holds a
broker relationship or touches order placement.

**The actual model:** `execution/base.py::BrokerAdapter` (ABC,
`submit_order(...)`) still exists but is effectively vestigial —
`execution/paper_adapter.py::PaperAdapter` is its only implementation, used
only for `execution_mode="paper"` simulated trades. Every other trade goes
through **manual TradingView execution**: `OrderPreview.execution_mode =
"manual_tradingview"`. Approving one of these previews (`POST
/orders/{id}/approve`) does **not** call a `BrokerAdapter` — it just marks
the preview `approved` and hands the human a chart deep-link
(`GET/POST /orders/{id}/open-tradingview`) plus a copy-to-clipboard
order-detail block (TradingView has no public URL-parameter mechanism to
prefill its order ticket from a third-party site — confirmed by research,
not a gap to build around). The human trades manually in TradingView (or
elsewhere — TradingView is just the user's chosen venue, nothing about this
design depends on it specifically), then self-reports what actually
happened via `POST /manual-execution/{id}` (`broker/manual_execution/service.py`),
which records the outcome (`executed` / `executed_with_changes` /
`rejected` / `watch_only` / `paper_tracked` / `cancelled`) and, for the two
"position" outcomes, creates a `PaperTrade` row with
`source="manual_tradingview"` so it flows through the same approval/close
lifecycle as simulated paper trades but stays reportable separately
(`reports/paper_trading_health.py` breaks out win rate / pnl / status by
`source`).

**Portfolio context is derived entirely from `PaperTrade` rows** (both
`source="paper"` and `source="manual_tradingview"`), not from any live
broker connection — see `orders/service.py::build_portfolio_state()` and
`portfolio/service.py::get_portfolio_view()`. There is no
`broker_accounts`/`portfolio_snapshots` table and none is planned; the
`PaperTrade` table (with self-reported real fills for the manual-execution
rows) is the single source of truth for "what's currently held."

---

## 10. MVP Milestone Plan

Building on what already exists (scanner, thesis agent, paper trading loop, IBKR client, health check):

**Milestone A — News & Filing Intelligence** (foundation for better theses)
- `news_items` table, ingestion job for Finnhub news + SEC EDGAR filings (start with these two; GDELT/Benzinga later)
- Event-type + sentiment classifier (rule-based first pass + LLM fallback for ambiguous cases — don't call an LLM per headline at scan volume)
- Wire into `thesis_agent.py` as additional context

**Milestone B — Portfolio Context** — DONE, derived from `PaperTrade`, not IBKR
- No new tables — positions/exposure derived from existing `PaperTrade` rows
  (`orders/service.py::build_portfolio_state()`, extended by
  `portfolio/service.py::get_portfolio_view()` with per-position current
  price/unrealized P&L via `data/pricing.py::_latest_price`)
- `GET /portfolio` endpoint + frontend Portfolio page
- No live broker sync worker or `portfolio_agent.py` digest — out of scope;
  revisit only if a real need for a narrative digest (vs. raw numbers)
  emerges

**Milestone C — Risk Policy Engine**
- `risk_policies`, `risk_evaluations` tables
- `risk/engine.py` + rule set from §8, fully unit-tested (this is the part that needs the highest test coverage in the whole system)
- Kill switch (`agent_control` table + `/risk/kill-switch` endpoint)

**Milestone D — Order Preview + Approval Queue**
- `order_previews`, `live_orders` tables
- `POST /orders/preview`, approval queue endpoints
- Dashboard: Trade Approval Queue view
- Still writes to `paper_adapter` only — no live IBKR order placement yet, to validate the full pipeline safely

**Milestone E — Live Execution (IBKR)** — SUPERSEDED, dropped
- Replaced by manual TradingView execution (part of Milestone D's scope —
  `manual_execution/service.py`, already built). No live broker order API is
  planned; see §9.

**Milestone F — Audit Log & Dashboard polish**
- `audit_log` table, `/audit` endpoint, Agent Activity Log view
- `thesis_checks` table + scheduled thesis-validity re-checks
- Weekly performance review generation

Recommended order: A → C (can start in parallel with B) → B → D → F → E. Risk engine and audit log should exist *before* order preview/approval is exposed, not bolted on after.

---

## 11. Build vs. Buy

| Area | Recommendation | Why |
|---|---|---|
| Market/price data | Buy (Finnhub, already integrated) for real-time; yfinance only for prototyping | Free tiers rate-limit hard; scanner needs reliability |
| News | Start with Finnhub (already have key) + SEC EDGAR (free, official) | Covers earnings/analyst/filing events without new vendor cost |
| GDELT | Skip for MVP | High noise-to-signal for single-name equity research; revisit for macro/sector signals later |
| Article full-text parsing (newspaper4k/Fundus) | Skip for MVP | Legal/ToS risk scraping publisher sites; headline + source summary is enough for thesis context |
| Broker execution | Build (IBKR Client Portal API) | No good buy option for a broker-agnostic control plane; this is the core IP |
| LLM | Buy (Anthropic API, already integrated via `ai/provider.py`) | Not a differentiator to build in-house |
| Workflow orchestration | Build on Celery (already have Redis) | Temporal is buy-adjacent overhead not justified at this scale |
| Auth | Buy (Clerk/Auth0) if multi-user is needed pre-MVP; otherwise simple session auth is fine for single-operator use | Don't build auth |

---

## 12. Security & Compliance Considerations

- **This is not a broker-dealer or RIA product in MVP** — it never takes custody, never executes without a human click, and the AI never gives directive buy/sell language (per existing `CLAUDE.md` rule: "Thesis describes, never directs"). Keep this framing consistent in all UI copy — "consider," "may warrant," never "buy this."
- **Secrets**: IBKR session cookies, Anthropic API key, DB credentials — standard env-var/Railway-secret handling, never logged. `agent_runs.raw_response`/`input_json` must be scrubbed of secrets before storage (should never contain any, but validate).
- **IBKR auth is inherently manual** (2FA, browser login) — already documented in `CLAUDE.md`. Do not attempt to automate around this; it's a deliberate broker-side control, not a bug.
- **Least privilege for the agent role**: as in §7, the AI's tool-calling credentials structurally cannot reach `place_live_order`. This should be enforced by scope-checking in the gateway dispatcher, not by prompt instructions alone — prompts are not a security boundary.
- **Kill switch must be reachable independent of the main app** — e.g. a direct DB flag or a separate minimal endpoint — so it still works if the scheduler/worker layer is misbehaving.
- **Rate limiting on approval endpoints** and required re-auth for `place_live_order`-triggering actions (don't let a stale session silently approve trades).
- **Data retention**: audit log and `agent_runs` should be append-only and retained indefinitely for MVP (cheap at this volume) — useful both for debugging and for any future compliance conversation.

---

## 13. Failure Modes & Mitigations

| Failure | Mitigation |
|---|---|
| LLM hallucinates a bullish thesis on bad/stale news | News items carry `confidence`/`expected_impact`; thesis agent prompt requires citing specific `news_items`; low-confidence news shouldn't singlehandedly drive a high-confidence thesis — enforce in prompt + spot-check in thesis_checks |
| Risk engine bug approves something it shouldn't | Risk engine is pure/deterministic and the most heavily unit-tested module; kill switch as backstop; MVP live mode is Preview Required only, so a human is still the last line of defense even if the engine misjudges |
| IBKR Gateway session drops mid-day | `/tickle` every 60s (exists) + `is_authenticated()` health check (exists) surfaced prominently in dashboard; block new order previews from reaching "approved" state if gateway auth is stale |
| Duplicate thesis generation burns LLM spend | Already mitigated via `agent_runs.input_hash` caching — keep this invariant as new context (news) is added to the hash |
| News source outage silently starves theses of context | Ingestion job failures logged + surfaced on dashboard; thesis agent should note in output when news context is stale/missing rather than silently omitting it |
| Partial fills / broker order stuck in ambiguous state | Order status poller with terminal-state timeout → surfaces as "needs manual review" in dashboard rather than assuming success |
| Kill switch flips but in-flight order already submitted | Kill switch blocks new `order_previews` from being created/approved; in-flight broker orders still need explicit cancel — document this limitation, add `cancel_order` prominently in UI when kill switch is engaged |
| Cooldown/risk rules gamed by rapid resubmission | `check_cooldown` keys off recent rejections/losses per ticker, not per order-preview-id, so resubmitting a rejected idea under a new preview still triggers it |

---

## 14. What Should NOT Be Built in MVP

- Options, margin, shorting — hard-blocked in the risk engine, not just "unsupported in UI"
- Rules-Based Auto or Full Automation modes
- Multi-broker support (design the adapter interface for it, don't build a second adapter)
- Multi-account / multi-user RIA features
- Full-text article scraping (legal risk, low marginal value over headlines+summaries)
- GDELT / macro-signal ingestion
- Websocket streaming market data (polling snapshots is sufficient at MVP scan cadence)
- A custom event-sourced audit ledger (Postgres tables are enough)
- Backtesting engine beyond what paper trading naturally provides
- Mobile app

---

## 15. Open Questions

1. **Position sizing input**: does the user specify dollar amount, share count, or % of portfolio when requesting a preview? (Recommend: dollar amount, converted to shares at preview time using latest snapshot price.)
2. **Who can edit risk policies?** Single-operator use probably means "the account owner," but the schema should support an `updated_by` audit trail regardless.
2. **Order preview staleness**: how long is a preview valid before requiring re-evaluation (price may have moved)? Recommend a short TTL (e.g. 5 min) after which re-preview is required before approval is allowed.
3. **Thesis re-check cadence**: daily, or event-triggered by new news_items on the ticker? Recommend event-triggered with a daily fallback sweep.
4. **How aggressive should the news classifier be about LLM usage** given volume? Recommend rule/keyword-based first-pass classification, LLM only for ambiguous or high-scoring tickers, to control cost.

---

## 16. Suggested Next Implementation Steps

1. Add `news_items` model + Alembic migration; wire Finnhub news ingestion (client already exists at `data/finnhub.py`) and SEC EDGAR filings into it.
2. Write `risk/engine.py` and `risk/rules.py` with unit tests covering every rule in isolation and in combination — this should be the best-tested module in the codebase before anything depends on it.
3. Add `broker/base.py` `BrokerAdapter` ABC and refactor `data/ibkr.py` usage behind `broker/ibkr_adapter.py` + a `broker/paper_adapter.py`, so paper and (future) live share one interface.
4. Add `order_previews`/`live_orders`/`agent_control` tables + `POST /orders/preview` endpoint, feeding the risk engine — before any UI, verify end-to-end via API/tests that a preview correctly resolves to each of the five verdicts.
5. Build the Trade Approval Queue dashboard view against the paper adapter only, to validate the full UX before touching live IBKR order placement.
