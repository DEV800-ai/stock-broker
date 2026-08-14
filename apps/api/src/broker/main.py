from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from broker.auth import require_actor
from broker.routers import (
    agent_control,
    audit,
    health,
    manual_execution,
    orders,
    paper_trades,
    reports,
    scanner,
    thesis,
    universe,
    watchlist,
)

app = FastAPI(title="Stock Broker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://stock-broker.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
AUTH = [Depends(require_actor)]

app.include_router(health.router, prefix=PREFIX, tags=["health"])
app.include_router(universe.router, prefix=PREFIX, tags=["universe"], dependencies=AUTH)
app.include_router(scanner.router, prefix=PREFIX, tags=["scanner"], dependencies=AUTH)
app.include_router(watchlist.router, prefix=PREFIX, tags=["watchlist"], dependencies=AUTH)
app.include_router(thesis.router, prefix=PREFIX, tags=["thesis"], dependencies=AUTH)
app.include_router(paper_trades.router, prefix=PREFIX, tags=["paper-trades"], dependencies=AUTH)
app.include_router(orders.router, prefix=PREFIX, tags=["orders"], dependencies=AUTH)
app.include_router(manual_execution.router, prefix=PREFIX, tags=["manual-execution"], dependencies=AUTH)
app.include_router(audit.router, prefix=PREFIX, tags=["audit"], dependencies=AUTH)
app.include_router(reports.router, prefix=PREFIX, tags=["reports"], dependencies=AUTH)
app.include_router(agent_control.router, prefix=PREFIX, tags=["agent-control"], dependencies=AUTH)
