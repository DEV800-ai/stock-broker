import logging
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from broker.config import settings

logger = logging.getLogger(__name__)

# IBKR Client Portal Gateway runs locally; TLS cert is self-signed
_VERIFY_SSL = False


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


class IBKRClient:
    """Thin wrapper around the IBKR Client Portal Web API.

    Requires the IBKR Gateway process to be running and authenticated.
    The gateway URL defaults to https://localhost:5000 (set IBKR_GATEWAY_URL to override).

    Usage:
        client = IBKRClient()
        if not client.is_authenticated():
            raise RuntimeError("Start IBKR Gateway and log in at https://localhost:5000")
        bars = client.get_bars(conid=265598, period="6m", bar="1d")
    """

    def __init__(self, gateway_url: str | None = None) -> None:
        self.base = (gateway_url or settings.ibkr_gateway_url).rstrip("/")
        self._session = _make_session()

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self.base}/v1/api{path}"
        resp = self._session.get(url, params=params, verify=_VERIFY_SSL, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict | None = None) -> dict | list:
        url = f"{self.base}/v1/api{path}"
        resp = self._session.post(url, json=json or {}, verify=_VERIFY_SSL, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        try:
            data = self._get("/iserver/auth/status")
            return bool(data.get("authenticated"))
        except Exception:
            return False

    def tickle(self) -> bool:
        """Keep the gateway session alive. Call every 60s."""
        try:
            self._post("/tickle")
            return True
        except Exception as exc:
            logger.warning("IBKR tickle failed: %s", exc)
            return False

    def reauthenticate(self) -> bool:
        """Attempt re-authentication. Returns True if session is now authenticated."""
        try:
            self._post("/iserver/reauthenticate")
            time.sleep(3)
            return self.is_authenticated()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Contract / symbol resolution
    # ------------------------------------------------------------------

    def search_contract(self, ticker: str) -> dict | None:
        """Resolve a US equity ticker to an IBKR contract (returns conid)."""
        try:
            results = self._get("/iserver/secdef/search", params={"symbol": ticker, "secType": "STK"})
            if not results:
                return None
            # Prefer US exchange (SMART or primary US listing)
            for item in results:
                if item.get("secType") == "STK" and item.get("currency") == "USD":
                    return item
            return results[0]
        except Exception as exc:
            logger.debug("Contract search failed for %s: %s", ticker, exc)
            return None

    def resolve_conid(self, ticker: str) -> int | None:
        """Return the IBKR conid for a US equity ticker, or None if not found."""
        contract = self.search_contract(ticker)
        if contract:
            return contract.get("conid")
        return None

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_snapshot(self, conids: list[int], fields: list[str] | None = None) -> list[dict]:
        """Get latest market snapshot for a list of conids.

        fields: IBKR field IDs. Defaults to last price (31), bid (84), ask (86), volume (7762).
        Returns list of dicts keyed by field ID.
        """
        if not conids:
            return []
        default_fields = fields or ["31", "84", "86", "7762", "7741"]  # last, bid, ask, volume, change%
        conids_str = ",".join(str(c) for c in conids)
        fields_str = ",".join(default_fields)
        try:
            return self._get("/iserver/marketdata/snapshot", params={"conids": conids_str, "fields": fields_str})
        except Exception as exc:
            logger.warning("Snapshot failed for %d conids: %s", len(conids), exc)
            return []

    def get_bars(self, conid: int, period: str = "1y", bar: str = "1d") -> pd.DataFrame:
        """Fetch historical OHLCV bars for a single conid.

        period: e.g. "6m", "1y", "2y"
        bar: e.g. "1d", "1w"
        Returns DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            data = self._get(
                "/hmds/history",
                params={"conid": conid, "period": period, "bar": bar, "outsideRth": False},
            )
            raw = data.get("data", [])
            if not raw:
                return pd.DataFrame()
            df = pd.DataFrame(raw)
            # IBKR returns timestamps in ms
            df["date"] = pd.to_datetime(df["t"], unit="ms").dt.date
            df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
            return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
        except Exception as exc:
            logger.warning("get_bars failed for conid=%d: %s", conid, exc)
            return pd.DataFrame()

    # ------------------------------------------------------------------
    # Portfolio / account
    # ------------------------------------------------------------------

    def get_accounts(self) -> list[dict]:
        try:
            return self._get("/portfolio/accounts")
        except Exception:
            return []

    def get_positions(self, account_id: str) -> list[dict]:
        try:
            return self._get(f"/portfolio/{account_id}/positions/0")
        except Exception:
            return []

    def get_ledger(self, account_id: str) -> dict:
        """Cash balances and net liquidation value, keyed by currency ("BASE" is the
        account's base-currency summary)."""
        try:
            return self._get(f"/portfolio/{account_id}/ledger")
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Orders (paper trading — Phase 3)
    # ------------------------------------------------------------------

    def place_order(self, account_id: str, order: dict) -> dict:
        """Submit an order. order must match IBKR order schema.
        Only used in Phase 3+ after human approval.
        """
        return self._post(f"/iserver/account/{account_id}/orders", json={"orders": [order]})

    def get_orders(self, account_id: str) -> list[dict]:
        try:
            data = self._get("/iserver/account/orders")
            return data.get("orders", [])
        except Exception:
            return []
