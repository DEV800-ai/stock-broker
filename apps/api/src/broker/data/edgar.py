import functools
import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from broker.config import settings

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession_nodash}/{primary_doc}"
_TIMEOUT = 10.0

# Maps SEC form type to internal event type + weight
_FORM_MAP: dict[str, tuple[str, float]] = {
    "8-K": ("material_event", 0.7),
    "10-Q": ("earnings_report", 0.6),
    "10-K": ("annual_report", 0.6),
    "S-1": ("dilution", -0.6),
    "S-3": ("dilution", -0.6),
    "424B5": ("dilution", -0.6),
    "SC 13D": ("ownership_activist", 0.5),
    "SC 13G": ("ownership_passive", 0.2),
    "4": ("insider", 0.3),
    "DEF 14A": ("proxy", 0.1),
}


def _headers() -> dict[str, str] | None:
    if not settings.sec_edgar_user_agent:
        return None
    return {"User-Agent": settings.sec_edgar_user_agent}


@functools.lru_cache(maxsize=1)
def _ticker_to_cik() -> dict[str, str]:
    headers = _headers()
    if headers is None:
        return {}

    try:
        resp = httpx.get(_TICKERS_URL, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        rows = (resp.json() or {}).values()
        return {row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in rows}
    except Exception as exc:
        logger.warning("SEC EDGAR ticker map fetch failed: %s", exc)
        return {}


def fetch_recent_filings(ticker: str, days: int = 90) -> list[dict]:
    """Fetch recent SEC filings for ticker. Returns normalized filing dicts."""
    headers = _headers()
    if headers is None:
        logger.warning("sec_edgar_user_agent not set — skipping EDGAR filings fetch")
        return []

    cik = _ticker_to_cik().get(ticker.upper())
    if not cik:
        return []

    try:
        resp = httpx.get(_SUBMISSIONS_URL.format(cik=cik), headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        recent = (resp.json() or {}).get("filings", {}).get("recent", {})
    except Exception as exc:
        logger.warning("SEC EDGAR submissions fetch failed for %s: %s", ticker, exc)
        return []

    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    cik_num = str(int(cik))

    filings = []
    for i in range(len(forms)):
        filing_date = date.fromisoformat(filing_dates[i])
        if filing_date < cutoff:
            continue
        accession_nodash = accession_numbers[i].replace("-", "")
        primary_doc = primary_docs[i] if i < len(primary_docs) else ""
        url = _ARCHIVES_URL.format(cik_num=cik_num, accession_nodash=accession_nodash, primary_doc=primary_doc)
        filings.append(
            {
                "form": forms[i],
                "filingDate": filing_dates[i],
                "accessionNumber": accession_numbers[i],
                "url": url,
            }
        )

    return filings


def classify_filing(filing: dict) -> tuple[str | None, float]:
    """Return (event_type, weight) for a normalized EDGAR filing dict."""
    return _FORM_MAP.get(filing.get("form", ""), (None, 0.0))


def score_filings(filings: list[dict]) -> float:
    """Aggregate a 0-1 score from a list of recent filings, same shape as finnhub.score_news."""
    if not filings:
        return 0.0

    total = 0.0
    for f in filings[:10]:
        _, weight = classify_filing(f)
        total += weight

    normalised = (total + 7.0) / 14.0
    return round(max(0.0, min(1.0, normalised)), 3)


def format_filings_for_prompt(filings: list[dict], max_items: int = 5) -> str:
    """Format the most recent filings into a compact prompt string."""
    if not filings:
        return ""

    lines = []
    for f in filings[:max_items]:
        event_type, _ = classify_filing(f)
        tag = f"[{event_type}] " if event_type else ""
        lines.append(f"• {f['filingDate']} (SEC EDGAR): {tag}{f['form']} filing")

    return "\n".join(lines)
