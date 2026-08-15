# Stock Broker

AI-powered stock scanning and research assistant. Scans a universe of stocks daily, scores them on momentum/volume/relative-strength signals, and generates OpenAI-powered research theses — with paper trading and human-approved live trading planned for later phases.

> **Phase status:** Phase 1 (scanner + watchlist) and Phase 2 (AI thesis) are complete. Phase 3 (paper trading) is scaffolded. No live trading is active.

## Deployment

Deployed on Railway, auto-deploying from `master`:

- Web: https://stock-broker.up.railway.app
- API: https://stock-broker-api.up.railway.app

---

## Architecture

```
Market data (yfinance / IBKR)
        ↓
   Scanner Engine          — scores tickers on volume, momentum, RS, gap
        ↓
   Watchlist               — ranked list of flagged tickers
        ↓
   AI Thesis Agent         — OpenAI generates research thesis per ticker
   + Finnhub News          — recent headlines fed into the prompt
        ↓
   Paper Trading           — simulated trades, pending human approval
        ↓
   Human Approval Layer    — required before any real order
        ↓
   (Phase 4+) Live Trading via IBKR
```

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.11 · FastAPI · SQLAlchemy · Alembic |
| Database | PostgreSQL 16 |
| AI | OpenAI (`gpt-4o`) |
| Market data | yfinance (prototype) · IBKR Client Portal API |
| News | Finnhub company news API |
| Frontend | Next.js 15 · TypeScript · Tailwind · shadcn/ui |

## Monorepo layout

```
apps/
  api/          FastAPI backend
    src/broker/
      ai/           ThesisAgent (OpenAI)
      data/         yfinance, IBKR, Finnhub fetchers
      models/       SQLAlchemy ORM models
      ranking/      Signal scoring engine
      routers/      FastAPI route handlers
      scanner/      Scan orchestrator
    alembic/        DB migrations
  web/          Next.js frontend
```

## Quick start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 (or podman/docker)
- OpenAI API key
- Finnhub API key (free tier works)

### 2. Start Postgres

```bash
podman run -d --name signalalpha-pg \
  -e POSTGRES_DB=signalalpha \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 docker.io/postgres:16-alpine
```

### 3. Configure environment

```bash
cd apps/api
cp ../../.env.example .env
# Fill in:
#   OPENAI_API_KEY=sk-...
#   FINNHUB_API_KEY=...
#   DATABASE_URL=postgresql://postgres:password@localhost:5432/signalalpha
```

### 4. Run the API

```bash
cd apps/api
uv venv .venv && uv pip install -e ".[dev]"
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/uvicorn broker.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 5. Run the frontend

```bash
cd apps/web
npm install
npm run dev
# → http://localhost:3000
```

## IBKR Gateway (optional — required for live market data)

1. Download IBKR Client Portal Gateway from interactivebrokers.com
2. Run: `java -jar clientportal.gw/root/run.sh`
3. Log in at https://localhost:5000 (browser, 2FA required)
4. Keep running — the app pings `/v1/api/tickle` every 60 s to maintain the session

> IBKR requires manual 2FA login on every startup. This cannot be automated.

## Key guardrails

- No live trading code until Phase 4
- No buy/sell recommendations in any API response — the thesis describes, never directs
- Every OpenAI API call is logged to `agent_runs` table
- Thesis is cached by SHA-256 hash of ticker + date + signals; never regenerated for the same input
- Thesis only generated for tickers with `composite_score > 0.50` (configurable)

## API reference

Full interactive docs at `http://localhost:8000/docs` when the API is running.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/scanner/trigger` | Kick off a full scan |
| `GET` | `/api/v1/scanner/runs` | List scan runs |
| `GET` | `/api/v1/watchlist` | Today's ranked watchlist |
| `PUT` | `/api/v1/watchlist/{ticker}/status` | Update ticker status |
| `POST` | `/api/v1/thesis/generate` | Queue AI thesis generation |
| `GET` | `/api/v1/thesis/{ticker}` | Get latest thesis for a ticker |
| `GET` | `/api/v1/thesis/{ticker}/history` | Thesis history |
| `GET` | `/api/v1/paper-trades` | List paper trades |
| `POST` | `/api/v1/paper-trades` | Create paper trade |
| `POST` | `/api/v1/paper-trades/{id}/approve` | Approve a paper trade |

## Phase roadmap

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Scanner + watchlist |
| 2 | ✅ Done | AI thesis per ticker + Finnhub news |
| 3 | 🔧 In progress | Paper trading with human approval |
| 4 | Planned | Human-approved live trading via IBKR |
| 5 | Planned | Limited automation with strict guardrails |

---

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for a walkthrough of the UI.
