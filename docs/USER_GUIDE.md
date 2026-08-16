# Stock Broker — User Guide

This guide walks through the day-to-day workflow: running a scan, reviewing the watchlist, generating a research thesis, and managing paper trades.

---

## Table of contents

1. [Starting the app](#1-starting-the-app)
2. [Dashboard](#2-dashboard)
3. [Running a scan](#3-running-a-scan)
4. [Reviewing the watchlist](#4-reviewing-the-watchlist)
5. [Generating an AI thesis](#5-generating-an-ai-thesis)
6. [Reading a thesis](#6-reading-a-thesis)
7. [Managing paper trades](#7-managing-paper-trades)
8. [Understanding scores](#8-understanding-scores)
9. [Ticker status workflow](#9-ticker-status-workflow)
10. [Important limits](#10-important-limits)

---

## 1. Starting the app

Make sure both services are running before opening the UI.

**API** (terminal 1):
```bash
cd apps/api
PYTHONPATH=src .venv/bin/uvicorn broker.main:app --reload
```

**Frontend** (terminal 2):
```bash
cd apps/web
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## 2. Dashboard

The dashboard (`/dashboard`) gives a system health snapshot:

| Indicator | What it means |
|---|---|
| **DB** | PostgreSQL connection is healthy |
| **IBKR Gateway** | Client Portal Gateway is reachable (optional) |
| **OpenAI** | OpenAI API key is configured |
| **Universe** | Total tickers loaded, how many have price bar history |
| **Recent scan runs** | Status, start time, tickers scanned/flagged |

If **OpenAI** shows as unavailable, check that `OPENAI_API_KEY` is set in `apps/api/.env`.

---

## 3. Running a scan

Go to **Top Ideas** (`/ideas`) and click **Run Scan**.

The scan runs in the background and typically takes 1–3 minutes for the default universe (500 tickers). It will:

1. Seed any new tickers into the universe
2. Fetch up to 220 days of daily OHLCV bars via yfinance
3. Score every ticker (volume, momentum, relative strength, gap)
4. Flag tickers with `composite_score ≥ 0.30` onto the watchlist

The page refreshes the run list automatically. A completed run shows **tickers scanned** and **tickers flagged**.

> If a scan shows **failed**, check the API logs — the most common cause is a network timeout on yfinance bulk fetches.

---

## 4. Reviewing the watchlist

Stay on **Top Ideas** (`/ideas`).

Tickers are displayed as cards ranked by composite score. Click a card to open its detail panel, where you can set its status:

| Status | Meaning |
|---|---|
| **WATCH** | Scanner flagged it — initial review stage |
| **RESEARCH** | You've decided it warrants deeper investigation |
| **PAPER** | You've opened a paper trade for it |
| **AVOID** | Ruled out — hidden from default view |

Each card shows:
- Rank and ticker symbol
- Current status badge
- Composite score bar (0–100%)
- **View Thesis** button (if a thesis exists)
- **Generate Thesis** button (if score ≥ 50% and no thesis yet)

---

## 5. Generating an AI thesis

Click **Generate Thesis** on any watchlist card with score ≥ 50%.

The button changes to **Generating…** while the request is in flight. Thesis generation:

1. Fetches the latest Finnhub news for the ticker (last 7 days)
2. Builds a prompt with all signal scores + recent headlines
3. Calls Claude to produce a structured research summary
4. Stores the result and links it back to the watchlist entry

The card automatically switches to **View Thesis** once generation completes (polls every 2 seconds, times out after ~60 seconds).

> Theses are cached by day. Running **Generate Thesis** again on the same ticker on the same day returns the cached result unless you use the `force_refresh` API parameter directly.

---

## 6. Reading a thesis

Click **View Thesis** to open the thesis panel. It contains:

| Section | Description |
|---|---|
| **Why Interesting** | What the technical signals indicate |
| **Risk Factors** | Key technical or macro risks |
| **Sector Context** | Sector-level backdrop (if relevant) |
| **News Summary** | Digest of the most relevant recent headlines |
| **Catalysts** | Near-term events or conditions to watch |
| **Confidence** | `HIGH` / `MEDIUM` / `LOW` — Claude's assessment of signal clarity |

> The thesis describes market conditions objectively. It never recommends buying or selling.

---

## 7. Managing paper trades

Go to **Paper Trades** (`/paper-trades`).

Paper trades simulate positions without real money. To create one:

1. A paper trade starts in **pending_approval** status
2. Click **Approve** to move it to **open** (simulates entry)
3. Click **Reject** to discard it

No paper trade moves to **open** without explicit human approval — this mirrors the human-in-the-loop model that will be required for live trading in Phase 4.

Tracked fields per trade: entry price, target price, stop price, shares, P&L, close reason.

---

## 8. Understanding scores

The scanner produces four sub-scores (each 0.0–1.0) combined into a weighted composite:

| Sub-score | Weight | What it measures |
|---|---|---|
| **Volume** | 25% | Today's volume vs 20-day average (1× avg → 0.0, 3× avg → 1.0) |
| **Momentum** | 35% | RSI-14 position, 1-day/5-day price change, above SMA-50/200 |
| **Relative Strength** | 30% | 20-day return vs sector ETF (excess return vs peers) |
| **Gap** | 10% | Overnight gap-up size (+2% → ~0.2, +10% → 1.0) |

**Composite score thresholds:**

| Score | Effect |
|---|---|
| ≥ 0.30 | Added to watchlist |
| ≥ 0.50 | Eligible for AI thesis generation |

Signals fired (shown in scan results):

| Signal | Condition |
|---|---|
| `volume_surge` | Volume ratio ≥ 2× |
| `rsi_momentum` | RSI-14 between 50 and 70 |
| `5d_breakout` | 5-day return ≥ 5% |
| `gap_up` | Gap ≥ 2% |
| `above_both_smas` | Price above both SMA-50 and SMA-200 |

---

## 9. Ticker status workflow

```
(scanner flags ticker)
        ↓
     WATCH          ← default on entry
        ↓
    RESEARCH        ← you decide it's worth deeper look
        ↓
     PAPER          ← you open a paper trade
        ↓
     AVOID          ← ruled out at any stage
```

Status is updated manually from the watchlist. There is no automatic promotion between stages.

---

## 10. Important limits

- **No live trading is available in the current build.** Paper trades are simulated only.
- The thesis is an analytical description, not financial advice. It will never say "buy" or "sell."
- IBKR Gateway requires manual 2FA login on every startup — it cannot be automated.
- Finnhub free tier is rate-limited. If news fetching is slow or empty, check your `FINNHUB_API_KEY`.
- yfinance data is for research/prototype use only. For production accuracy, switch to IBKR market data.
