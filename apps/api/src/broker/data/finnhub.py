import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from broker.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = 10.0

# Maps Finnhub category strings to internal event types + weights
_CATEGORY_MAP: dict[str, tuple[str, float]] = {
    "earnings": ("earnings", 0.9),
    "ipo": ("ipo", 0.7),
    "mergers": ("ma", 0.8),
    "analyst": ("analyst_action", 0.6),
    "insider": ("insider", 0.5),
}


def fetch_company_news(ticker: str, days: int = 7) -> list[dict]:
    """Fetch recent company news from Finnhub. Returns raw article dicts."""
    if not settings.finnhub_api_key:
        logger.warning("finnhub_api_key not set — skipping news fetch")
        return []

    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=days)

    try:
        resp = httpx.get(
            f"{_BASE}/company-news",
            params={
                "symbol": ticker,
                "from": from_dt.strftime("%Y-%m-%d"),
                "to": to_dt.strftime("%Y-%m-%d"),
                "token": settings.finnhub_api_key,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json() or []
    except Exception as exc:
        logger.warning("Finnhub news fetch failed for %s: %s", ticker, exc)
        return []


def fetch_next_earnings_date(ticker: str) -> date | None:
    """Next scheduled earnings date for ticker (today or later), or None if unset/unknown.
    Feeds risk/rules.py::check_earnings_proximity via orders/service.py::build_risk_context."""
    if not settings.finnhub_api_key:
        logger.warning("finnhub_api_key not set — skipping earnings calendar fetch")
        return None

    today = datetime.now(timezone.utc).date()
    to_dt = today + timedelta(days=90)

    try:
        resp = httpx.get(
            f"{_BASE}/calendar/earnings",
            params={
                "symbol": ticker,
                "from": today.strftime("%Y-%m-%d"),
                "to": to_dt.strftime("%Y-%m-%d"),
                "token": settings.finnhub_api_key,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        rows = (resp.json() or {}).get("earningsCalendar", [])
        dates = [
            date.fromisoformat(row["date"])
            for row in rows
            if row.get("date")
        ]
        return min(dates) if dates else None
    except Exception as exc:
        logger.warning("Finnhub earnings calendar fetch failed for %s: %s", ticker, exc)
        return None


def classify_article(article: dict) -> tuple[str | None, float]:
    """Return (event_type, weight) for a Finnhub article dict."""
    headline = (article.get("headline") or "").lower()
    category = (article.get("category") or "").lower()

    if category in _CATEGORY_MAP:
        return _CATEGORY_MAP[category]

    # Keyword fallback
    if any(w in headline for w in ("earnings", "eps", "revenue", "guidance", "beat", "miss")):
        return "earnings", 0.9
    if any(w in headline for w in ("upgrade", "downgrade", "price target", "overweight", "buy", "sell")):
        return "analyst_action", 0.6
    if any(w in headline for w in ("contract", "partnership", "deal", "awarded")):
        return "contract", 0.8
    if any(w in headline for w in ("fda", "approval", "cleared", "regulatory")):
        return "regulatory", 0.8
    if any(w in headline for w in ("lawsuit", "investigation", "fraud", "sec ", "doj")):
        return "legal_risk", -0.7
    if any(w in headline for w in ("dilution", "offering", "shares", "secondary")):
        return "dilution", -0.5
    if any(w in headline for w in ("ceo", "cfo", "resign", "appoint", "hire")):
        return "management", 0.3

    return None, 0.0


def score_news(articles: list[dict]) -> float:
    """Aggregate a 0–1 news_score from a list of recent articles."""
    if not articles:
        return 0.0

    total = 0.0
    for a in articles[:10]:  # cap at 10 most recent
        _, weight = classify_article(a)
        total += weight

    # Normalise: ±10 max weight range → clamp to 0–1
    normalised = (total + 7.0) / 14.0
    return round(max(0.0, min(1.0, normalised)), 3)


def format_news_for_prompt(articles: list[dict], max_items: int = 5) -> str:
    """Format the most recent articles into a compact prompt string."""
    if not articles:
        return "No recent news found."

    lines = []
    for a in articles[:max_items]:
        published = datetime.fromtimestamp(a.get("datetime", 0), tz=timezone.utc).strftime("%Y-%m-%d")
        source = a.get("source", "")
        headline = a.get("headline", "").strip()
        event_type, _ = classify_article(a)
        tag = f"[{event_type}] " if event_type else ""
        lines.append(f"• {published} ({source}): {tag}{headline}")

    return "\n".join(lines)
