import hashlib
import json
import logging
import time
from datetime import date, datetime

import anthropic
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from broker.config import settings
from broker.data.finnhub import fetch_company_news, format_news_for_prompt, score_news
from broker.models.news import NewsItem
from broker.models.scan import ScanResult
from broker.models.thesis import AgentRun, StockThesis
from broker.models.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a financial research analyst. Your job is to describe why a stock's \
recent technical signals are noteworthy and what risks apply. You describe \
market data objectively — you never recommend buying or selling.

Respond ONLY with valid JSON matching this schema (no markdown, no preamble):
{
  "why_interesting": "<2-4 sentences describing what the signals indicate>",
  "risk_factors": "<2-3 sentences on key technical or macro risks>",
  "sector_context": "<1-2 sentences on sector-level context if relevant, or null>",
  "news_summary": "<1-3 sentences summarising the most relevant recent news, or null if none>",
  "catalysts": "<1-2 sentences on potential near-term catalysts to watch, or null>",
  "confidence": "high" | "medium" | "low"
}
"""


def _input_hash(ticker: str, scan_date: str, signals: dict | None) -> str:
    payload = json.dumps({"ticker": ticker, "date": scan_date, "signals": signals}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _fmt(v: float | None, decimals: int = 2) -> str:
    return f"{v:.{decimals}f}" if v is not None else "N/A"


def _build_user_prompt(ticker: str, scan: ScanResult | None, news_text: str = "") -> str:
    if scan is None:
        base = f"Ticker: {ticker}\nNo scan data available. Describe general considerations."
    else:
        signals_fired = list(scan.signals_fired.keys()) if scan.signals_fired else []
        lines = [
            f"Ticker: {ticker}",
            f"Scan date: {scan.scan_date}",
            f"Price: ${_fmt(scan.price)}",
            f"1-day change: {_fmt(scan.pct_change_1d and scan.pct_change_1d * 100)}%",
            f"5-day change: {_fmt(scan.pct_change_5d and scan.pct_change_5d * 100)}%",
            f"20-day change: {_fmt(scan.pct_change_20d and scan.pct_change_20d * 100)}%",
            f"RSI-14: {_fmt(scan.rsi_14)}",
            f"Volume ratio (vs 20-day avg): {_fmt(scan.volume_ratio)}x",
            f"Above SMA-50: {scan.above_sma50}",
            f"Above SMA-200: {scan.above_sma200}",
            f"Composite score: {_fmt(scan.composite_score, 3)} (volume={_fmt(scan.volume_score, 3)}, "
            f"momentum={_fmt(scan.momentum_score, 3)}, rs={_fmt(scan.rs_score, 3)}, gap={_fmt(scan.gap_score, 3)})",
            f"Signals fired: {', '.join(signals_fired) if signals_fired else 'none'}",
        ]
        base = "\n".join(lines)

    if news_text:
        base += f"\n\nRecent news (last 7 days):\n{news_text}"
    return base


class ThesisAgent:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(self, ticker: str, scan_result_id: int | None = None, force_refresh: bool = False) -> StockThesis:
        scan = self._load_scan(scan_result_id, ticker)

        if scan and scan.composite_score is not None and scan.composite_score < settings.thesis_min_score:
            raise ValueError(
                f"{ticker} composite_score {scan.composite_score:.3f} is below "
                f"thesis_min_score {settings.thesis_min_score}"
            )

        today = str(date.today())
        signals = scan.signals_fired if scan else None
        ihash = _input_hash(ticker, today, signals)

        if not force_refresh:
            cached = self._find_cached(ticker, ihash)
            if cached:
                logger.info("Returning cached thesis for %s (hash=%s)", ticker, ihash[:8])
                return cached

        articles = fetch_company_news(ticker)
        news_text = format_news_for_prompt(articles)
        computed_news_score = score_news(articles)

        user_prompt = _build_user_prompt(ticker, scan, news_text)
        input_json = {"ticker": ticker, "scan_result_id": scan_result_id, "prompt": user_prompt}

        run = AgentRun(
            agent="thesis_agent",
            ticker=ticker,
            input_hash=ihash,
            input_json=input_json,
            model=settings.claude_model,
        )
        self.db.add(run)
        self.db.flush()

        t0 = time.monotonic()
        try:
            thesis = self._call_claude(run, ticker, scan, articles, user_prompt, ihash, computed_news_score)
        except Exception as exc:
            run.error = str(exc)
            self.db.commit()
            logger.exception("Thesis generation failed for %s", ticker)
            raise
        finally:
            run.latency_ms = int((time.monotonic() - t0) * 1000)
            self.db.commit()

        return thesis

    # ------------------------------------------------------------------

    def _load_scan(self, scan_result_id: int | None, ticker: str) -> ScanResult | None:
        if scan_result_id:
            return self.db.get(ScanResult, scan_result_id)
        return self.db.scalars(
            select(ScanResult)
            .where(ScanResult.ticker == ticker)
            .order_by(desc(ScanResult.scan_date), desc(ScanResult.id))
        ).first()

    def _find_cached(self, ticker: str, ihash: str) -> StockThesis | None:
        run = self.db.scalars(
            select(AgentRun)
            .where(AgentRun.agent == "thesis_agent")
            .where(AgentRun.ticker == ticker)
            .where(AgentRun.input_hash == ihash)
            .where(AgentRun.error == None)  # noqa: E711
            .order_by(desc(AgentRun.created_at))
        ).first()
        if not run:
            return None
        return self.db.scalars(
            select(StockThesis)
            .where(StockThesis.ticker == ticker)
            .order_by(desc(StockThesis.generated_at))
        ).first()

    def _call_claude(
        self,
        run: AgentRun,
        ticker: str,
        scan: ScanResult | None,
        articles: list[dict],
        user_prompt: str,
        ihash: str,
        news_score: float,
    ) -> StockThesis:
        response = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        run.prompt_tokens = response.usage.input_tokens
        run.completion_tokens = response.usage.output_tokens

        raw_text = response.content[0].text
        parsed = json.loads(raw_text)

        thesis = StockThesis(
            ticker=ticker,
            scan_result_id=scan.id if scan else None,
            model=settings.claude_model,
            why_interesting=parsed["why_interesting"],
            risk_factors=parsed["risk_factors"],
            sector_context=parsed.get("sector_context"),
            news_summary=parsed.get("news_summary"),
            catalysts=parsed.get("catalysts"),
            confidence=parsed.get("confidence"),
            news_score=news_score if articles else None,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            raw_response={"text": raw_text, "input_hash": ihash},
        )
        self.db.add(thesis)
        self.db.flush()

        self._store_news_items(ticker, articles)
        run.output_json = {"thesis_id": thesis.id}
        self._backfill_watchlist(ticker, thesis.id)
        return thesis

    def _store_news_items(self, ticker: str, articles: list[dict]) -> None:
        from datetime import timezone

        from broker.data.finnhub import classify_article

        for a in articles:
            url = a.get("url") or ""
            if not url:
                continue
            exists = self.db.scalars(
                select(NewsItem)
                .where(NewsItem.ticker == ticker)
                .where(NewsItem.source_url == url)
            ).first()
            if exists:
                continue
            event_type, weight = classify_article(a)
            published_at = datetime.fromtimestamp(a.get("datetime", 0), tz=timezone.utc).replace(tzinfo=None)
            item = NewsItem(
                ticker=ticker,
                headline=a.get("headline", ""),
                summary=a.get("summary"),
                source=a.get("source"),
                source_url=url,
                published_at=published_at,
                event_type=event_type,
                event_weight=weight,
            )
            self.db.add(item)

    def _backfill_watchlist(self, ticker: str, thesis_id: int) -> None:
        entry = self.db.scalars(
            select(WatchlistEntry)
            .where(WatchlistEntry.ticker == ticker)
            .order_by(desc(WatchlistEntry.watchlist_date), desc(WatchlistEntry.id))
        ).first()
        if entry and entry.thesis_id != thesis_id:
            entry.thesis_id = thesis_id
