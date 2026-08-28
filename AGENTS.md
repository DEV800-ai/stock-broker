# Stock Broker — AGENTS.md

## Project

AI-powered stock scanning and research assistant. Scanner + watchlist + AI thesis + paper trading + human-directed manual TradingView execution. No live/automated trading — never planned; see Phase roadmap below.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy + Alembic + PostgreSQL (apps/api/)
- **Frontend:** Next.js 15 + TypeScript + Tailwind + shadcn/ui (apps/web/)
- **AI:** OpenAI (gpt-4o), integration in apps/api/src/broker/ai/thesis_agent.py
- **Market data:** yfinance (`broker/data/yfinance_data.py`). No broker API integration — see "Execution model" below.

## Running locally

### Postgres
```bash
podman run -d --name signalalpha-pg \
  -e POSTGRES_DB=signalalpha -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password \
  -p 5432:5432 docker.io/postgres:16-alpine
```

### API
```bash
cd apps/api
cp ../../.env.example .env   # fill in your keys
# API_KEY is required — generate one with: openssl rand -hex 32
uv venv .venv && uv pip install -e ".[dev]"
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/uvicorn broker.main:app --reload
```

### Frontend
```bash
cd apps/web
cp .env.local.example .env.local   # server-only API_KEY must match the API's API_KEY — never NEXT_PUBLIC_*
npm install
npm run dev
```

## Execution model — no live broker integration, ever

Signal Alpha never places, modifies, or cancels an order and never connects
to a broker API. There is no IBKR (or other broker) integration in this
codebase — it was removed after a deliberate pivot (see
`docs/SIGNAL_ALPHA_DESIGN.md` §9). Non-paper trades go through **manual
TradingView execution**: the human trades manually in TradingView (or
wherever they choose), then self-reports the outcome via
`POST /manual-execution/{id}` (`broker/manual_execution/service.py`).
Portfolio context (`broker/portfolio/service.py`) is derived entirely from
`PaperTrade` rows, not a live account connection.

## Key rules

- **No live/automated trading code, full stop.** paper_trades.status is gated — pending_approval → open only after human approval. Order execution goes through `BrokerAdapter` (`broker/execution/base.py`); `orders/service.py::get_broker_adapter()` always returns `PaperAdapter`, and that's the only adapter that will ever be wired there — non-paper trades never go through `BrokerAdapter` at all, they go through the manual-execution self-report flow above. Do not add a live broker adapter or call any broker's order-placement API from anywhere in this codebase.
- **No buy/sell recommendations** in any API response. Thesis describes, never directs.
- **Codex API calls are always logged** to agent_runs table. Never fire-and-forget.
- **Thesis caching:** check agent_runs.input_hash (SHA256 of ticker+date+signals) before generating. Never regenerate the same thesis.
- **Thesis only generated** for tickers with composite_score > settings.thesis_min_score (default 0.50).
- **All API routes except /health require auth** (`X-API-Key` header, checked in `broker/auth.py`). Never add a new router without the `dependencies=[Depends(require_actor)]` wiring in `main.py`, and never hardcode `approved_by`/audit `actor` — use the identity from `require_actor`.
- **Human-only actions use `require_human_actor`, not `require_actor`.** Order/paper-trade approval and reject, and the agent kill switch's `unkill`/`autonomy-mode` endpoints, must depend on `require_human_actor` (`broker/auth.py`) so they can be gated behind the optional second `X-Human-Key` secret (`settings.human_approval_key`) once one exists — never wire a new approval-style endpoint to plain `require_actor`. Tightening the kill switch (`POST /agent-control/kill`) stays on `require_actor` deliberately — anyone with API access should be able to trip it, only loosening it should need the human key.

## Database

PostgreSQL only (not DuckDB). The API and background scanner write concurrently — single-writer DBs won't work here.

Migrations live in apps/api/alembic/. Run with:
```bash
PYTHONPATH=src .venv/bin/alembic upgrade head
```

## Deployment (Railway)

- Requires persistent volume for PostgreSQL
- Set all env vars from .env.example in Railway dashboard

## Phase roadmap

1. Scanner + watchlist (current)
2. AI thesis per ticker (current)
3. Paper trading with human approval — includes both simulated `PaperAdapter` fills and manual TradingView execution (`execution_mode="manual_tradingview"`: human trades manually, self-reports the outcome via `/manual-execution/{id}`, see `docs/SIGNAL_ALPHA_DESIGN.md` §9)
4. ~~Human-approved live trading via IBKR~~ — dropped, superseded by manual TradingView execution (Phase 3)
5. Limited automation with strict guardrails
