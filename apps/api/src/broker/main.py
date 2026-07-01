from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from broker.routers import health, paper_trades, scanner, thesis, universe, watchlist

app = FastAPI(title="Stock Broker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(health.router, prefix=PREFIX, tags=["health"])
app.include_router(universe.router, prefix=PREFIX, tags=["universe"])
app.include_router(scanner.router, prefix=PREFIX, tags=["scanner"])
app.include_router(watchlist.router, prefix=PREFIX, tags=["watchlist"])
app.include_router(thesis.router, prefix=PREFIX, tags=["thesis"])
app.include_router(paper_trades.router, prefix=PREFIX, tags=["paper-trades"])
