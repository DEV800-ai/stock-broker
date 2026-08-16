# Stock Broker — Frontend

Next.js 15 frontend for the Stock Broker AI research assistant.

## Dev server

```bash
npm install
npm run dev
# → http://localhost:3000
```

Browser requests go through this app's own `/api/backend/*` proxy
(`src/app/api/backend/[...path]/route.ts`), which forwards to the FastAPI backend and attaches
`X-API-Key` server-side — the key is never sent to the browser. Configure the backend location
and secret via server-only env vars (see `.env.local.example`):

```bash
cp .env.local.example .env.local
# API_URL=http://localhost:8000
# API_KEY=<must match the API's API_KEY>
```

## Pages

| Route | Description |
|---|---|
| `/dashboard` | System health + recent scan runs |
| `/ideas` | Top Ideas — scan, ranked results, TradingView chart, thesis, order preview |
| `/orders` | Order preview queue, approval, manual TradingView execution |
| `/paper-trades` | Paper trade management and approval |

See the [User Guide](../../docs/USER_GUIDE.md) for a full walkthrough.
