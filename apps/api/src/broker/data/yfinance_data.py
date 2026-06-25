import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def get_bars(ticker: str, days: int = 200) -> pd.DataFrame:
    """Fetch daily OHLCV bars for a ticker via yfinance.

    Returns DataFrame with columns: date, open, high, low, close, volume
    Returns empty DataFrame on failure.
    yfinance is for research/backfill only — not for live trading decisions.
    """
    try:
        start = date.today() - timedelta(days=days + 10)  # buffer for weekends/holidays
        df = yf.download(ticker, start=start.isoformat(), auto_adjust=True, progress=False, multi_level_column=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date": "bar_date"})
        df["bar_date"] = pd.to_datetime(df["bar_date"]).dt.date
        df["ticker"] = ticker
        df["volume"] = df["volume"].fillna(0).astype(int)
        return df[["ticker", "bar_date", "open", "high", "low", "close", "volume"]].tail(days)
    except Exception as exc:
        logger.warning("yfinance bars failed for %s: %s", ticker, exc)
        return pd.DataFrame()


def get_info(ticker: str) -> dict:
    """Fetch basic company metadata: name, sector, industry, market cap, exchange."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "exchange": info.get("exchange"),
        }
    except Exception as exc:
        logger.debug("yfinance info failed for %s: %s", ticker, exc)
        return {}


def get_fundamentals(ticker: str) -> dict:
    """Fetch key fundamentals for thesis context: P/E, EPS growth, revenue growth."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "eps_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as exc:
        logger.debug("yfinance fundamentals failed for %s: %s", ticker, exc)
        return {}


def get_bars_bulk(tickers: list[str], days: int = 200) -> dict[str, pd.DataFrame]:
    """Fetch bars for multiple tickers at once (yfinance bulk download is faster than one-by-one)."""
    if not tickers:
        return {}
    try:
        start = date.today() - timedelta(days=days + 10)
        raw = yf.download(
            tickers,
            start=start.isoformat(),
            auto_adjust=True,
            progress=False,
            group_by="ticker",
        )
        result: dict[str, pd.DataFrame] = {}
        if len(tickers) == 1:
            ticker = tickers[0]
            df = raw.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={"date": "bar_date"})
            df["bar_date"] = pd.to_datetime(df["bar_date"]).dt.date
            df["ticker"] = ticker
            df["volume"] = df["volume"].fillna(0).astype(int)
            result[ticker] = df[["ticker", "bar_date", "open", "high", "low", "close", "volume"]].tail(days)
        else:
            for ticker in tickers:
                if ticker not in raw.columns.get_level_values(0):
                    continue
                df = raw[ticker].dropna(subset=["Close"]).reset_index()
                df.columns = [c.lower() for c in df.columns]
                df = df.rename(columns={"date": "bar_date"})
                df["bar_date"] = pd.to_datetime(df["bar_date"]).dt.date
                df["ticker"] = ticker
                df["volume"] = df["volume"].fillna(0).astype(int)
                result[ticker] = df[["ticker", "bar_date", "open", "high", "low", "close", "volume"]].tail(days)
        return result
    except Exception as exc:
        logger.warning("yfinance bulk download failed: %s", exc)
        return {}
