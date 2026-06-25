# Signal Alpha — CLAUDE.md

## Project

AI-powered stock scanning and research assistant. Phase 1+2 only: scanner + watchlist + AI thesis. No live trading.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy + Alembic + PostgreSQL (apps/api/)
- **Frontend:** Next.js 15 + TypeScript + Tailwind + shadcn/ui (apps/web/)
- **AI:** Anthropic Claude (claude-sonnet-4-6), provider abstracted in apps/api/src/broker/ai/provider.py
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
uv venv .venv && uv pip install -e ".[dev]"
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/uvicorn broker.main:app --reload
```

### Frontend
```bash
cd apps/web
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

- **No live trading code until Phase 4.** paper_trades.status is gated — pending_approval → open only after human approval.
- **No buy/sell recommendations** in any API response. Thesis describes, never directs.
- **Claude API calls are always logged** to agent_runs table. Never fire-and-forget.
- **Thesis caching:** check agent_runs.input_hash (SHA256 of ticker+date+signals) before generating. Never regenerate the same thesis.
- **Thesis only generated** for tickers with composite_score > settings.thesis_min_score (default 0.50).

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
3. Paper trading with human approval
4. Human-approved live trading via IBKR
5. Limited automation with strict guardrails
