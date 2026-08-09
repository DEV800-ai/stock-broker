# Hardening Plan — Security Review Follow-ups

**Status:** Active tracking doc
**Origin:** Two independent reviews of the repo (2026-08-05) — a red-team security pass and an architecture/positioning pass — cross-checked against actual code, not taken at face value. Findings below are only the ones verified against `apps/api/src`.
**Relationship to other docs:** Extends the roadmap in `CLAUDE.md` and the milestone plan in `docs/SIGNAL_ALPHA_DESIGN.md` §10. That design doc predates some of the current implementation — risk engine, order preview/approval, and audit log (its Milestones C, D, F) already exist in code. This doc tracks what's left, not what to build from scratch.

Check items off as they land. Each item notes which review raised it and whether it's a hard gate on Phase 4 (live IBKR execution).

---

## Verified current state (as of this review)

Already implemented and confirmed by reading the code (not just claimed):
- Scanner → composite score → watchlist (`scanner/runner.py`, `ranking/scorer.py`)
- Thesis agent with "never recommend buy/sell" system prompt, JSON schema output, `input_hash` caching, `AgentRun` logging on non-cached calls (`ai/thesis_agent.py`)
- Deterministic risk engine, 13 rules incl. kill switch, no margin/options/shorting, position/sector/loss limits, earnings proximity, cooldown (`risk/rules.py`)
- Order preview → risk evaluation → human approval → paper trade (`orders/service.py`)
- Audit log written in the same DB transaction as the state change (`audit/service.py`)
- Finnhub news categorization with keyword fallback (`data/finnhub.py`)
- `IBKRClient` already has session/auth, contract search, market data, **and** `get_accounts`, `get_positions`, `place_order`, `get_orders`, `cancel_order` (`data/ibkr.py`) — these are written but **not called from anywhere else in the codebase**. This is further along than it looks; the gap is wiring + isolation, not missing implementation.

What's missing entirely: any authentication/authorization layer, an agent tool/MCP-style gateway, realistic paper fills, and a real (non-paper) portfolio provider.

---

## Phase 3 (current) — hardening before Phase 3 is "done"

These are gaps in what's already built, not new scope.

- [x] **P0 — Add authentication + authorization to the API.** *(Red-team #1, #7)* — Done: shared-secret `X-API-Key` auth (`broker/auth.py:require_actor`), applied via `dependencies=` to every router except `/health` (`main.py`). `X-Actor` header now flows into `approved_by` on order/paper-trade approve/reject and into `audit_log(actor=...)`, replacing the hardcoded `"human"`. Frontend sends both headers from `apps/web/src/lib/api.ts` (`NEXT_PUBLIC_API_KEY` / `NEXT_PUBLIC_ACTOR`, gitignored `.env.local`). Verified: `/health` returns 200 unauthenticated, `/universe` returns 401 with missing/wrong key.
  - Remaining (not done): this is a single shared secret, not per-user auth — no real scopes (viewer/researcher/approver/admin) and no step-up confirmation. Fine for single-operator use per `SIGNAL_ALPHA_DESIGN.md` §11, but revisit before multi-user or public exposure.
- [x] **Harden JSON parsing in the thesis agent.** *(Red-team #7)* — Done: added `ThesisResponse` pydantic model (`ai/thesis_agent.py`) validated against `json.loads(raw_text)`; on `JSONDecodeError`/`ValidationError`, one retry with an explicit "return valid JSON" note appended to the prompt. If the retry also fails, raises `ThesisParseError` — no `StockThesis` row is ever created, and both raw attempts are stored on `AgentRun.output_json` (`raw_attempts`) before the outer `generate()` handler commits `run.error`. Token usage (`AgentRun.prompt_tokens`/`completion_tokens`) now accumulates across both attempts. Verified with a mocked Anthropic client: retry-then-succeed produces a valid thesis; retry-then-fail raises cleanly with both attempts preserved and no partial thesis row.
- [x] **Treat news content as untrusted input in the thesis prompt.** *(Red-team Scenario B)* — Done: `_SYSTEM_PROMPT` (`ai/thesis_agent.py`) now explicitly tells Claude the `<news_articles>` block is untrusted third-party data, not instructions, and to never follow directives found inside it. `_build_user_prompt` wraps news in `<news_articles>...</news_articles>` delimiters and strips any literal occurrence of those tag strings from the article text first, so an adversarial headline can't forge a fake closing tag and escape the block. Verified: a synthetic headline containing `</news_articles>` and injected "SYSTEM:" text is neutralized — the tag markers are stripped from the content and the real delimiters stay balanced (1 open / 1 close).
- [x] **Preview staleness / re-pricing at approval time.** *(Red-team Scenario C; also flagged as an open question in SIGNAL_ALPHA_DESIGN.md §15)* — Done: `settings.order_preview_ttl_minutes` (default 5, `.env.example`). `approve_preview` (`orders/service.py`) now rejects with `PreviewExpired` (→ 409) if `created_at` is older than the TTL — preview status is left untouched so the client must request a fresh preview rather than the system guessing a new price. Independently, the risk engine is now always re-run at approval time against current portfolio state/cooldowns/kill-switch (not just at preview time); if the re-evaluation verdict is `blocked`, the preview is flipped to `status="blocked"`, audit-logged (`approve_order_blocked_on_reeval`), and `PreviewBlockedAtApproval` is raised (→ 409) instead of silently approving. Verified against the real dev DB: (1) a fresh preview still approves normally, (2) a backdated (>TTL) preview is rejected and left `pending`, (3) engaging the kill switch between preview and approval correctly blocks approval on re-eval and persists `status="blocked"`.
  - Note: this bounds *portfolio-state* staleness, not *price* staleness directly — `limit_price` is not silently re-fetched (that would change what the human is approving); the TTL is what forces a fresh preview at a current price once it lapses.
- [x] **Upgrade paper fill realism.** *(Red-team #3, Scenario D)* — Done: `execution/paper_adapter.py`'s `simulate_fill()` now takes action/limit_price/requested_shares/avg_daily_volume and returns a `FillResult` (status, filled_shares, fill_price, theoretical_price) instead of echoing the limit price. Adverse slippage (`PAPER_FILL_SLIPPAGE_BPS`, default 5bps) is applied against the trader on every fill — BUYs fill above the limit, SELLs below. When requested size is large relative to 20-day ADV, entries (BUY) partial-fill on a linear ramp between `PAPER_FILL_PARTIAL_ADV_PCT` (10%) and `PAPER_FILL_REJECT_ADV_PCT` (25%, full rejection) — floored at `PAPER_FILL_MIN_PARTIAL_RATIO` (30%). `orders/service.py::approve_preview` now: rejects the fill outright (`FillRejected` → 409, `preview.status="rejected"`, audited as `approve_order_fill_rejected`) when size is too large for liquidity; records `PaperTrade.requested_shares` / `theoretical_entry_price` / `theoretical_exit_price` / `fill_status` alongside the existing `shares`/`entry_price`/`exit_price` so theoretical (naive limit-price) vs. executable performance can be compared directly per trade. New columns added via migration `a3c7e1f2b4d6_add_fill_realism_columns`. Verified against the real dev DB across four scenarios: small order fills in full with slippage; oversized order (15% of ADV) partial-fills; very large order (33% of ADV) is rejected with no trade/paper_trade row created and the preview left `rejected`; a SELL exit prices with adverse slippage against the trader.
  - Scoped down from the original ask: **partial fills are entry-only (BUY)**. Exits (SELL) either fill in full (with slippage) or are rejected outright — `PaperTrade` has one entry price/date and one exit price/date, so a position closed across two different exit fills would need the trade row split, which is a bigger schema change than this pass covers. **Next-bar fill is not implemented** — the simulator only ever prices at approval time and has no notion of a subsequent bar relative to that instant; would need order timestamps decoupled from approval timestamps to mean anything. Both are noted in `paper_adapter.py`'s docstring as deliberate scope cuts, not oversights.
- [x] **Fix scoring signal labeling / confirm no product-facing overclaim.** *(Second review's scoring claim was slightly overstated; low-priority accuracy check, not a functional bug.)* — Checked, no fix needed: `ranking/scorer.py` computes exactly four weighted sub-scores (`volume` 25%, `momentum` 35%, `rs` 30%, `gap` 10%); RSI-14 and SMA-50/200 are already correctly folded into `_momentum_score()` as inputs, not scored/weighted independently. `docs/USER_GUIDE.md` §"How scoring works" already states this precisely — a table listing the four sub-scores with the Momentum row spelling out "RSI-14 position, 1-day/5-day price change, above SMA-50/200" — and separately documents the boolean `signals_fired` flags (`rsi_momentum`, `above_both_smas`, etc.) as a distinct concept from the weighted sub-scores, matching `scorer.py`'s `signals` dict exactly. `README.md` and `SIGNAL_ALPHA_DESIGN.md` both describe scoring only at the "volume/momentum/RS/gap" level, no deeper claims. The only frontend surface showing RSI (`apps/web/src/app/scanner/page.tsx`) renders it as its own raw-value column next to Score, not as a labeled sub-signal — doesn't imply independent weighting. Conclusion: the second review's claim didn't hold up against the current docs/code; no changes made.

## Phase 3 → Phase 4 gate — must be true before any live-IBKR wiring starts

These map to the architecture review's "Immediate PRs" and the red-team's P0 blockers #2 and #4. None of this is urgent for Phase 3, but none of it should be skipped when Phase 4 starts.

- [ ] **Isolate broker execution behind an adapter interface + feature flag**, per `SIGNAL_ALPHA_DESIGN.md` §9/§16. `place_order`/`get_orders`/`cancel_order` already exist in `IBKRClient` but are unwired — the risk is a future developer wiring them in without the flag/approval boundary.
  - `broker/base.py` `BrokerAdapter` ABC; `broker/paper_adapter.py` and `broker/ibkr_adapter.py` behind it.
  - `ENABLE_LIVE_TRADING` env var, default off; `execution_mode` field on order previews (`paper` / `live_preview` / `live`).
  - **IBKR connection model — decided, not open:** `ibkr_adapter.py` stays on the local **Client Portal Gateway** (manual 2FA, matches `CLAUDE.md`), not IBKR's OAuth Web API. OAuth Web API would remove the local-gateway dependency, but only matters if Signal Alpha becomes a multi-user product connecting to *other people's* IBKR accounts — that makes it a third-party vendor in IBKR's terms, requiring separate IBKR compliance approval, out of scope for MVP. Because `BrokerAdapter` is already an interface, this is a future adapter class if/when needed, not a rearchitecture. See `SIGNAL_ALPHA_DESIGN.md` §9 for the full decision record.
  - A test that proves paper approval cannot reach the IBKR live-order path.
- [ ] **Real portfolio context.** Risk engine currently reads `settings.paper_account_equity` (a config constant) and open paper trades, not a real account; `earnings_date` is hardcoded `None` so earnings-blackout rules can't fire. *(Red-team #4)*
  - `IBKRPortfolioProvider` (read-only sync of positions/cash/NLV), earnings calendar ingestion, staleness detection, block previews if risk-context data is stale/incomplete.
- [ ] **Tamper-evident audit log.** Current `audit_log` is a plain table with no hash chaining — fine for Phase 3, not for live trading. *(Red-team #6)*
  - Add prev-hash chaining per event, actor identity, request/trace id, source-data snapshot hash.

## Phase 4 (live trading) — unchanged scope, now with explicit gate criteria

From `CLAUDE.md`: "Human-approved live trading via IBKR." Add to the existing gate:
- [ ] Must not ship until the Phase 3→4 gate above is fully checked off.
- [ ] Must not ship until paper trading has run for a meaningful stretch (weeks, not days) with the *upgraded* fill model and no risk-engine bugs found (per `SIGNAL_ALPHA_DESIGN.md` Milestone E).
- [ ] Explicit "you are about to place a REAL order" confirmation UX; IBKR paper account for staging before real money.

## Phase 5 (limited automation) — no change, notes only

- [ ] Agent tool/gateway layer (`scan_market`, `propose_trade`, `get_risk_evaluation`, `disable_agent`, etc., per `SIGNAL_ALPHA_DESIGN.md` §7) does not exist yet. Needed before any external agent (Claude, ChatGPT, etc.) is given scoped access to this system. Not required for Phase 3/4, but should be scoped before Phase 5 starts.

## Explicitly out of scope / do not build early

Carried over from both reviews, consistent with `SIGNAL_ALPHA_DESIGN.md` §14:
- Live IBKR execution, auto-approval, options, margin, shorting, or trading on LLM confidence alone before the gate above is met.
- Public deployment without auth (blocks even Phase 3 demo access beyond localhost/trusted users).
- "AI broker" / "Stock Broker" positioning in user-facing copy — product is a control plane, not a broker. Naming/positioning cleanup is low-priority polish, not a P0.

---

## Open item from this review round

- Confirm whether `README.md` / repo title should be updated for positioning ("Signal Alpha — agentic trading control plane" vs. current "stock-broker" naming). Low priority, product/legal framing only — no functional risk. Not scheduled yet.
