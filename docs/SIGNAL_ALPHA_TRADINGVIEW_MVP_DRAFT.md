# Signal Alpha — TradingView Manual-Execution MVP (Draft for Review)

**Status: §10–11 and §22 milestone 1 are now implemented** (manual-execution tracking: schema, service, endpoints — see §22). The rest of this draft is still not merged into `SIGNAL_ALPHA_DESIGN.md` / `CLAUDE.md` / `HARDENING_PLAN.md`. Where this draft conflicts with the current repo (which is built around a future direct-IBKR-execution model), the conflict is called out explicitly rather than silently resolved.

**Note on framing (added after review):** despite the title, TradingView contributes almost nothing technically to this design — no order prefill, no writable layout API, no execution API, no URL-based order-ticket population, even with IBKR connected via TradingView's Trading Panel. The real simplification this pivot delivers is *not building broker execution at all* (dropping the IBKR Gateway/OAuth dependency entirely — see `SIGNAL_ALPHA_DESIGN.md` §9). TradingView is simply the user's own choice of manual-execution venue; the design would be identical if the user traded somewhere else. See §14 for the full explanation.

---

## 1. Executive Summary

Signal Alpha pivots its execution model away from a future direct-to-IBKR order API and toward **TradingView as the manual execution surface**, with the user's existing TradingView↔IBKR broker connection (via TradingView's own Trading Panel) doing the actual order entry. Signal Alpha's job stays scan → thesis → risk-check → order preview → audit; it never places, modifies, or cancels an order itself. The user is always the one who types the order into TradingView and hits send.

This removes the single largest source of complexity and risk in the roadmap so far: IBKR's Client Portal Gateway (local process, manual 2FA, session babysitting) or IBKR's OAuth API (which, per research done in this project, is not currently approved for retail/individual accounts of any type — see `docs/SIGNAL_ALPHA_DESIGN.md` §9). Under this model, Signal Alpha never needs an IBKR execution credential at all.

## 2. Product Positioning

**Is:** a research, scanner, risk, and trade-decision support system for human-directed trading.

**Is not:** an AI broker, autonomous trader, financial advisor, guaranteed signal engine, or auto-trading bot. It does not hold custody of funds or securities, does not place orders, and does not calculate or file tax.

This positioning is a legal/compliance load-bearing wall, not just marketing copy — see §19 and §20.

## 3. MVP User Personas

- **Solo operator / primary user** (the actual current user of this repo): technically sophisticated, runs their own IBKR account, wants systematic scanning and thesis generation but insists on manually pulling the trigger on every order. Primary persona for MVP; the entire system is currently designed around a single-operator deployment (shared-secret auth, no multi-tenant DB isolation).
- **Future "approver" role** (not built yet): a second human who reviews and approves order previews without necessarily being the one who scans. Relevant once/if this becomes multi-user; not needed for the current single-operator deployment.

## 4. Full User Journey

1. Scanner runs (scheduled or on-demand), scores the universe, populates candidates.
2. User opens Daily Market Brief, sees ranked candidates.
3. User opens a candidate's Thesis View — AI-generated bull/bear/catalyst/risk summary.
4. User requests (or system auto-generates, above `thesis_min_score`) an Order Preview.
5. Deterministic risk engine evaluates the preview; status attached (approved-for-manual-review / blocked / needs-smaller-size / paper-only / needs-more-data / watch-only).
6. If approved for manual review: user clicks **"Open in TradingView"** — deep-links to the symbol's chart on TradingView. (Order details are *displayed* in Signal Alpha next to the button, not injected into TradingView — see §14 for why.)
7. User manually places the order in TradingView against their IBKR-linked account, or decides not to.
8. User returns to Signal Alpha and records what happened: Executed as suggested / Executed with changes / Rejected / Watch only / Paper tracked / Cancelled. If "executed with changes," records actual price/qty/order type/notes.
9. Signal Alpha tracks the resulting position (if executed) against the original thesis over time: P&L, thesis validity, new catalysts, exit conditions.
10. Everything above is audit-logged.

## 5. High-Level Architecture

```
                     ┌─────────────────────────┐
                     │        Frontend         │
                     │  (Next.js, apps/web)    │
                     └────────────┬────────────┘
                                  │ X-API-Key / X-Human-Key
                     ┌────────────▼────────────┐
                     │      FastAPI (apps/api)  │
                     ├──────────────────────────┤
   ┌─────────────┐   │  scanner                 │
   │ Data sources│◄──┤  thesis (AI, Claude)     │
   │ (Finnhub,   │   │  risk engine             │
   │  yfinance,  │   │  orders (preview only)   │
   │  SEC EDGAR, │   │  manual-execution track. │◄──── user confirms outcome
   │  TV MCP*)   │   │  post-decision monitoring│
   └─────────────┘   │  agent-control/kill      │
                      │  audit                  │
                      └────────────┬─────────────┘
                                   │
                            ┌──────▼──────┐
                            │  PostgreSQL │
                            └─────────────┘

   User's browser, separately:
   TradingView (charting + Trading Panel) ──manual order entry──► IBKR (via TV's own broker link)

   * TradingView MCP, if used, is a read-only research adapter only — never touches order placement.
```

Signal Alpha and TradingView/IBKR are **not integrated at the API level** in this model. The only "integration" is a browser deep-link (open a URL) and a human typing numbers into two different apps.

## 6. Component Diagram (text form)

```
apps/api/src/broker/
├── scanner/                  (unchanged)
├── ai/                       (unchanged — thesis generation, provider.py)
├── risk/                     (unchanged — engine.py, rules.py, types.py)
├── orders/
│   └── service.py            (CHANGED — order preview no longer references
│                               broker execution adapters at all; "execution_mode"
│                               field fixed to "MANUAL_TRADINGVIEW")
├── execution/
│   ├── base.py                (BrokerAdapter ABC — becomes vestigial, see §21)
│   ├── paper_adapter.py       (unchanged — still used for paper-trading simulation)
│   └── ibkr_adapter.py        (UNCHANGED placeholder, but its purpose shifts from
│                               "future live-order integration" to "not needed
│                               under this model, kept only if a future phase
│                               revisits direct execution")
├── manual_execution/          (NEW)
│   └── service.py             (record_outcome: executed/rejected/watch/paper/
│                               cancelled/executed_with_changes)
├── portfolio/
│   └── ibkr_provider.py       (unchanged — still useful for READ-ONLY position/
│                               P&L context; this is a separate concern from
│                               execution and still requires *some* IBKR
│                               connection for live data, either Gateway or a
│                               read-only path — not resolved by this pivot)
├── agent_control/             (unchanged)
└── audit/                     (unchanged, extended with new event types — §17)
```

## 7. Data Flow: Scan → Manual TradingView Execution

```
scanner run
  → candidates persisted (composite_score, etc.)
  → thesis generated for candidates above thesis_min_score (agent_runs logged)
  → order preview requested
      → risk engine evaluates (deterministic, reads AgentControl kill/autonomy state)
      → preview persisted with immutable risk_evaluation_id attached
  → user clicks "Open in TradingView"
      → audit_log(action="tradingview_open", entity=preview.id, ticker=...)
      → frontend opens https://www.tradingview.com/chart/?symbol=<EXCHANGE>:<TICKER> in a new tab
  → user manually trades (or doesn't) in TradingView
  → user returns, submits outcome via POST /manual-execution/{preview_id}
      → audit_log(action="manual_execution_recorded", details={...})
      → if executed (as-is or with changes): PaperTrade-equivalent "real position"
        record created for tracking (see §16 — this reuses the existing
        PaperTrade-style tracking model, not a new one)
  → post-decision monitoring job periodically re-evaluates thesis validity,
    current price, P&L against the recorded entry
```

## 8. Backend Services

- `scanner` — unchanged.
- `ai` — unchanged (thesis generation).
- `risk` — unchanged engine; `execution_mode` is now always `MANUAL_TRADINGVIEW` for any order preview reaching the human, since there is no other mode in this MVP.
- `orders` — order preview only; drop any code path that assumes a subsequent automated submission step.
- `manual_execution` (new) — records human-reported trade outcomes against a preview.
- `portfolio` — read-only IBKR snapshot (unchanged, still unwired into risk sizing per existing repo decision).
- `agent_control` — unchanged (kill switch, autonomy mode).
- `audit` — unchanged, extended.
- `reports` — unchanged (paper-trading health report), extended to also report on manually-executed trades.

## 9. Frontend Screens

Maps directly to the prompt's requested screens, with reuse of existing screens/components where this repo already has them:

| Screen | Status |
|---|---|
| Daily Market Brief | exists (watchlist/scanner views) |
| Watchlist | exists |
| Stock Detail Page | exists |
| Thesis View | exists |
| Risk Review | exists (risk evaluation shown on preview) |
| Order Preview | exists — needs `execution_mode` badge + "Open in TradingView" button added |
| Open in TradingView | new — just a deep-link button + copyable order-details block, no new page |
| Manual Execution Confirmation | new — small form: outcome dropdown + optional actual price/qty/notes |
| Paper Tracking | exists |
| Portfolio/Exposure View | exists |
| Audit Log | exists |
| Settings and Kill Switch | exists (agent-control UI) |

## 10. Database Schema (delta only)

No new tables needed if manual-execution outcomes are modeled as an extension of the existing `paper_trades`-style table rather than a parallel schema. Recommended: reuse `PaperTrade` with a new `is_live: bool` / `source: "paper" | "manual_tradingview"` column, since P&L tracking, entry/exit, and status transitions (`pending_approval` → `open` → `closed`) are otherwise identical. Concretely:

```
paper_trades
  + source: str  ("paper" | "manual_tradingview")   -- NOT NULL, default "paper"
  + reported_by: str                                 -- actor who confirmed the outcome
  + execution_notes: str | None                      -- "executed with changes" free text
  + outcome: str                                      -- executed|executed_with_changes|rejected|
                                                          watch_only|paper_tracked|cancelled
```

Avoids a schema fork between paper and "real but manually confirmed" trades — they share the same lifecycle and reporting.

## 11. API Design (delta only)

```
POST /api/v1/order-previews/{id}/open-tradingview
  → audit-logs the open action, returns the deep-link URL (no state change)

POST /api/v1/manual-execution/{preview_id}
  body: { outcome, actual_price?, actual_quantity?, actual_order_type?, notes? }
  → Depends(require_human_actor)   -- this is a human-only action, same pattern
                                       already used for order/paper-trade approval
  → creates/updates the paper_trades row with source="manual_tradingview"
  → audit-logs
```

Everything else (scanner, thesis, risk, agent-control, audit) is unchanged.

## 12. Agent/Tool Interface Design

No new agent tools are needed or wanted. Explicitly: no tool is exposed to the LLM or any agent process that can place, modify, or cancel an order, in TradingView or anywhere else. The LLM's only output surface remains thesis text (structured, schema-validated) and it never touches the risk engine's verdict or the order preview's numeric fields beyond `reason`/`bull_case`/`bear_case` narrative text.

## 13. Risk Engine Design

Unchanged from the existing `risk/engine.py` design. One addition: since there is no automated execution path in this model at all, the risk engine's "Approved for manual review" verdict becomes the terminal state for any accepted trade — there is no subsequent "Approved for automated execution" tier to ever build. This actually simplifies the existing gate criteria in `HARDENING_PLAN.md`'s Phase 4 section, which was scoped around eventually allowing IBKR order submission — that gate largely goes away under this model (see §21).

## 14. TradingView Integration Design

**Deep-link only — no order prefill, confirmed even with IBKR connected via the Trading Panel.** TradingView does not publish an API or documented URL scheme for pre-populating the Trading Panel's order ticket (symbol, side, quantity, price, order type) from an external application — this was checked specifically against TradingView's own Advanced Charting Library / Trading Terminal docs, which only expose a `PreOrder`/broker-API surface for brokers building a white-label integration (e.g. IBKR itself could theoretically build this), not for a third-party app to inject an order into a user's existing tradingview.com session. TradingView's **Order Presets** feature (a static, user-configured-in-advance preset selected manually inside TradingView) is the closest native feature, but it can't take a dynamically computed per-ticker price from an external source either. Implemented as:

```
GET builds: https://www.tradingview.com/chart/?symbol=<EXCHANGE>:<TICKER>
POST /api/v1/orders/{preview_id}/open-tradingview  → audit-logs the open action, returns {"url": ...}
```

(`orders/service.py::tradingview_url()`, ticker's exchange looked up from `stock_universe.exchange`, defaulting to `NASDAQ` if unknown.)

This opens the correct chart/symbol in a new tab. The order details computed by Signal Alpha (action, quantity, order type, limit price, time-in-force) are displayed in Signal Alpha's own UI next to the button — recommended as a **copy-to-clipboard button**, not just static text, so the user can paste rather than re-read-and-retype into TradingView's order ticket. This is a real, permanent UX gap, not an oversight: product copy should say plainly "You'll need to re-enter these values in TradingView" rather than imply a one-click handoff.

**Reframing this integration honestly**: none of the above is TradingView doing work for Signal Alpha — it's a link-out plus a clipboard convenience. Connecting IBKR to TradingView (via TradingView's own broker link) reduces the user's work *during execution* (no separate broker login, order routes straight through) but does **not** reduce the handoff friction between "Signal Alpha computed an order" and "that order exists in TradingView's ticket." Worth being upfront about this in any product copy — the value of this design is dropping broker-execution scope from Signal Alpha entirely, not a slick TradingView integration.

Optional (not MVP): TradingView **alert webhooks** can POST into Signal Alpha when an alert fires — useful as an *inbound* signal source (e.g., "price crossed X" triggers a rescan), not for outbound order placement. This is a one-way, read-only integration from Signal Alpha's perspective.

## 15. TradingView MCP Research-Adapter Design

If a TradingView MCP server is added, it is wired in exactly like the existing data adapters (`FinnhubAdapter`, etc.) under a `MarketAnalysisAdapter` umbrella — read-only: technical snapshots, screeners, sentiment. It is never given order-placement, order-modification, or account-access tools, and it never receives or stores TradingView account credentials. No `TradingViewBrokerAdapter` is built in this MVP or planned.

**Evaluated two real implementations, with a concrete recommendation:**
- `atilaahmettaner/tradingview-mcp` — **recommended if one is added.** Server-side only: no TradingView login, no local app, fetches from public endpoints (Yahoo Finance, screeners, 30+ indicators, backtesting, news/sentiment). Fits the read-only adapter boundary cleanly — nothing to misuse even in the worst case.
- `tradesdontlie/tradingview-mcp` — **do not use.** Attaches to an already-logged-in **TradingView Desktop app** via Chrome DevTools Protocol (`--remote-debugging-port=9222`) and remote-controls it (symbol/timeframe changes, Pine Script injection, alert management, drawing tools, "UI automation"). It currently has no order-placement tool, but architecturally it's a live automation channel into an authenticated session, not a stateless data API — exactly the shape of risk §19 point 6 is meant to rule out, regardless of whether credentials are stored. A future version (or a prompt-injected instruction) could extend "UI automation" to clicking Buy.

## 16. Manual Execution Tracking Design — IMPLEMENTED

Reuses the `PaperTrade` lifecycle (`pending_approval → open → closed`, entry/exit price, P&L calc) with the `source`/`outcome`/`reported_by`/`execution_notes` columns added in §10 (migration `b3d5f7a9c1e3_add_manual_execution_tracking`).

Built:
- `orders/service.py::create_preview()` accepts `execution_mode: "paper" | "manual_tradingview"`.
- `orders/service.py::approve_preview()` branches on `execution_mode` — for `manual_tradingview` it skips `PaperAdapter`'s simulated fill entirely, just marks the preview `approved` and stops; no position is created yet.
- `manual_execution/service.py::record_outcome()` — the human-reported step. Validates the preview is `execution_mode="manual_tradingview"` and still `approved` (so it can only be recorded once — a second call correctly raises `InvalidPreviewState`, verified). For `executed`/`executed_with_changes` outcomes it creates the `PaperTrade` row (`source="manual_tradingview"`, actual price/qty if provided, else falls back to the preview's numbers) and links `preview.paper_trade_id`; other outcomes (`rejected`/`watch_only`/`paper_tracked`/`cancelled`) just close out the preview with no position row. Preview moves to a new terminal status `manual_recorded`.
- `POST /api/v1/orders/{preview_id}/open-tradingview` — `require_actor` (not human-only; it's a no-state-change navigation/audit action, not an approval).
- `POST /api/v1/manual-execution/{preview_id}` — `require_human_actor`, per `CLAUDE.md`'s rule that confirmation/approval-style actions never use plain `require_actor`.

Verified end-to-end against local Postgres: preview created with `execution_mode="manual_tradingview"` → risk-blocked correctly when no thesis attached (existing `has_thesis` rule, unaffected by this change) → with a thesis attached, approved without invoking the fill simulator → `open-tradingview` returned the correct deep-link and audit-logged it → `record_outcome` created a `PaperTrade` with `source="manual_tradingview"`, the reported actual price/quantity, and `execution_notes` → a second `record_outcome` call on the same preview correctly rejected with `InvalidPreviewState`. This means `reports/paper_trading_health.py` can be extended to break out `source` in a later milestone without any further schema change.

## 17. Audit Log Design

Extends the existing `audit_log()` call pattern (already used throughout this codebase) with two new `action` values: `tradingview_open` and `manual_execution_recorded`. No new audit infrastructure needed — `broker/audit/service.py` already supports arbitrary `action`/`entity_type`/`entity_id`/`details` payloads. Tamper-resistance (hash-chaining audit rows) remains a documented future item, not required for MVP — matches the existing audit design's current state in this repo.

## 18. Security Architecture

Reuses everything already built in this repo:
- `X-API-Key` shared-secret auth (`require_actor`) on all routes.
- `X-Human-Key` second-secret auth (`require_human_actor`) — the new `POST /manual-execution/{preview_id}` endpoint should use `require_human_actor`, consistent with the existing rule in `CLAUDE.md` that approval/confirmation-style actions never use plain `require_actor`.
- No TradingView or IBKR credentials are ever stored by Signal Alpha under this model — there's nothing to store, since Signal Alpha never authenticates to either service for execution.
- Encryption at rest/in transit: unchanged (Railway-managed Postgres + TLS).

## 19. Red-Team Assessment

1. **Prompt injection from news** — unchanged mitigation: news/filing text is passed to the LLM as untrusted data within a structured prompt, never as instructions; the risk engine is deterministic Python and reads none of the LLM's raw output, only its structured, schema-validated fields.
2. **Fake/low-quality news** — source ranking + multi-source confirmation remain a backlog item, not yet built; today's mitigation is that no trade executes without human review of the full thesis including sources cited.
3. **Stale market data** — order previews already carry timestamps and an expiry TTL (`ORDER_PREVIEW_TTL_MINUTES`, existing); this is unaffected by the TradingView pivot since staleness matters just as much for a manually-executed trade as an automated one — arguably more, since more time passes between preview and the user actually typing the order into TradingView.
4. **Unauthorized approval** — `require_human_actor` gate on the new endpoint prevents this exactly as it does for existing paper-trade/order approval.
5. **User overtrusts AI** — unchanged mitigations (no buy/sell verbs, bull/bear shown together); arguably *lower* risk here than a live-auto-trading model, since a human must independently operate TradingView regardless of what Signal Alpha says.
6. **TradingView misuse (automation attempt)** — the explicit non-goal in this design: no credential storage, no browser automation service, no MCP order-placement tool. This needs to be an enforced code-review rule (no `playwright`/`selenium`-style TradingView automation ever gets added), not just a document statement.
7. **Paper performance misleads user** — existing slippage/partial-fill simulation applies to `source="paper"` rows; `source="manual_tradingview"` rows use the user-reported actual price, which is more honest than simulation but depends on the user reporting accurately — worth a UI nudge to report promptly rather than after the fact from memory.
8. **Risk engine bypass** — unchanged: risk evaluation is backend-enforced and attached immutably to the preview before any UI can show "Open in TradingView"; this pivot doesn't add any new bypass surface since there's no new automated path to protect.
9. **Data provider failure** — unchanged mitigations (fallback sources, confidence degradation); TradingView itself is never a data dependency for scanning/thesis in this design (only MCP, if used, and that's optional/read-only).
10. **Legal/compliance mispositioning** — this pivot actually *reduces* legal exposure versus a future direct-IBKR-execution model, since Signal Alpha never touches order placement, never holds a broker relationship, and the disclaimer surface ("research and decision support, not a broker") becomes simpler to defend because it's now also architecturally true, not just a stated intent.

## 20. Compliance and Tax Considerations

- Signal Alpha is not the broker of record under this or any planned model; that doesn't change.
- Tax reporting stays entirely at the broker level (IBKR / Interactive Israel-HYBRID, Form 867 for Israeli residents) — Signal Alpha makes no tax claims and performs no tax calculations.
- Recommended: a CSV export of `manual_execution`-sourced trades (ticker, dates, prices, quantities) for the user to hand to an accountant or import into a tax tool — this is a reporting convenience, explicitly not a tax computation, and should be labeled as such in the UI.

## 21. Failure Modes and Mitigations

The main new failure mode introduced by this pivot: **the user forgets to report back what happened in TradingView**, leaving Signal Alpha's tracking state out of sync with reality (thinks "pending" when actually executed, or vice versa). Mitigation: no automated fix is possible (there's deliberately no read access into the user's TradingView/IBKR execution), so this is a UX problem — reminder prompts, and the Daily Market Brief surfacing "N previews awaiting outcome confirmation."

## 22. MVP Milestone Plan

1. **DONE** — `manual_execution` service + endpoints + `paper_trades` schema delta (§10–11, §16). Backend only; verified via curl + a scratch `SessionLocal` script against local Postgres, no frontend yet.
2. Add "Open in TradingView" button + copy-to-clipboard order-detail block to the existing Order Preview screen (frontend, not started).
3. Add the Manual Execution Confirmation form (frontend, not started).
4. Extend `reports/paper_trading_health.py` to break out `source="manual_tradingview"` separately (not started).
5. Update `SIGNAL_ALPHA_DESIGN.md` §9 and `CLAUDE.md`'s Phase roadmap to reflect this as the actual execution model (see §24 next steps; not started).

## 23. What Not to Build in MVP

Everything the original prompt excludes: direct live trading from the app, TradingView automation/browser automation, IBKR live order API, options, margin, shorting, full automation, LLM-only trade decisions, any feature that bypasses human decision-making, order prefill into TradingView (not possible anyway, see §14), and a `TradingViewBrokerAdapter`.

## 24. Future Roadmap / Open Questions for This Repo Specifically

- **`docs/HARDENING_PLAN.md` Phase 4** currently reads "Human-approved live trading via IBKR" — under this pivot that phase is largely superseded; the gate criteria written there (weeks of bug-free paper trading, `ENABLE_LIVE_TRADING` flag, `IBKRAdapter.submit_order`) become dormant, not deleted, in case a future phase revisits direct execution once IBKR opens retail OAuth (per this repo's own research, currently not approved for retail accounts).
- **Read-only portfolio access still needs an IBKR connection** of some kind (Gateway or otherwise) — this pivot solves *execution*, not *reading current positions/cash for risk sizing*. `portfolio/ibkr_provider.py` already exists for this and remains a separate, smaller-scope integration than execution ever was.
- This document does not yet propose specific copy changes to `CLAUDE.md`'s "Key rules" section or the Phase roadmap list — that's the natural next edit once this draft is approved.

---

*This draft intentionally does not modify any file outside itself. Next step, pending approval: merge the relevant deltas into `SIGNAL_ALPHA_DESIGN.md`, `CLAUDE.md`, and `HARDENING_PLAN.md`, and implement §22's milestone list.*
