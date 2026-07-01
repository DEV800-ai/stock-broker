# Stock Broker — Frontend

Next.js 15 frontend for the Stock Broker AI research assistant.

## Dev server

```bash
npm install
npm run dev
# → http://localhost:3000
```

Requires the API to be running at `http://localhost:8000`. Override with:

```bash
NEXT_PUBLIC_API_URL=http://your-api-host npm run dev
```

## Pages

| Route | Description |
|---|---|
| `/dashboard` | System health + recent scan runs |
| `/scanner` | Trigger scans, view run history |
| `/watchlist` | Ranked ticker cards, thesis generation |
| `/paper-trades` | Paper trade management and approval |

See the [User Guide](../../docs/USER_GUIDE.md) for a full walkthrough.
