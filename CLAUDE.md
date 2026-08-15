# Stock Broker — CLAUDE.md

## Project

AI-powered stock scanning and research assistant. Phase 1+2 only: scanner + watchlist + AI thesis. No live trading.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy + Alembic + PostgreSQL (apps/api/)
- **Frontend:** Next.js 15 + TypeScript + Tailwind + shadcn/ui (apps/web/)
- **AI:** OpenAI (gpt-4o), integration in apps/api/src/broker/ai/thesis_agent.py
- **Broker data:** IBKR Client Portal Web API (requires Gateway running locally)

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
cp .env.local.example .env.local   # NEXT_PUBLIC_API_KEY must match the API's API_KEY
npm install
npm run dev
```

## IBKR Gateway (required for market data)

1. Download IBKR Client Portal Gateway from interactivebrokers.com
2. Run: `java -jar clientportal.gw/root/run.sh`
3. Log in at https://localhost:5000 (browser, requires 2FA)
4. Keep the process running; the app calls /v1/api/tickle every 60s to maintain session

**Important:** IBKR does not support fully automated OAuth. Manual 2FA login is always required on startup. Do not attempt to automate this step — flag it to the user.

## Key rules

- **No live trading code until Phase 4.** paper_trades.status is gated — pending_approval → open only after human approval. Order execution goes through `BrokerAdapter` (`broker/execution/base.py`); `orders/service.py::get_broker_adapter()` always returns `PaperAdapter` today. `execution/ibkr_adapter.py::IBKRAdapter` exists as a structural placeholder only — its `submit_order` always raises, never call `IBKRClient.place_order` directly from anywhere in the approval path.
- **No buy/sell recommendations** in any API response. Thesis describes, never directs.
- **Claude API calls are always logged** to agent_runs table. Never fire-and-forget.
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
- IBKR Gateway cannot run on Railway — it must run on a machine with browser access for 2FA

## Phase roadmap

1. Scanner + watchlist (current)
2. AI thesis per ticker (current)
3. Paper trading with human approval — includes both simulated `PaperAdapter` fills and manual TradingView execution (`execution_mode="manual_tradingview"`: human trades manually, self-reports the outcome via `/manual-execution/{id}`, see `docs/SIGNAL_ALPHA_DESIGN.md` §9)
4. Human-approved live trading via IBKR
5. Limited automation with strict guardrails
