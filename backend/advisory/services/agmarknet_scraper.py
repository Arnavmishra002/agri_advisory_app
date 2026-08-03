"""Agmarknet 2.0 live-price client (real-time, location-aware).

Agmarknet migrated from the old SearchCmmMkt.aspx WebForms page to a React SPA
(Agmarknet 2.0) backed by a clean JSON API. This client calls that API directly
— which is more reliable than HTML scraping and returns today's prices filtered
by commodity and state.

Endpoints (base https://api.agmarknet.gov.in/v1/), verified live 2026-08:
  GET  /dashboard-commodities-filter -> {status, data:[{id, cmdt_name, ...}]}
  GET  /dashboard-market-filter      -> {status, data:[{id, mkt_name, state_id,
                                          state_name, district_id, district_name,...}]}
  POST /dashboard-data/              -> {status:"success",
                                          data:{records:[{cmdt_name, as_on_price,
                                          msp_price, as_on_arrival, reported_date,
                                          one_day_ago_price, two_day_ago_price,
                                          cmdt_grp_name, trend}]}}

The POST payload was captured from the live site's own request and confirmed to
return real rows for e.g. commodity=[23] (Onion), state=34 (Uttar Pradesh).

Output: records in the OGD field shape (commodity/state/district/market/
min_price/max_price/modal_price/arrival_date) so data_gov_mandi_client's
existing _format_datagov_response() + filter_fresh_live_rows() label and vet
them identically to API rows. Fails soft (returns []) — never fabricates.

Kept the module name/`fetch_records` signature so data_gov_mandi_client's
fallback wiring is unchanged.
"""

import logging
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.agmarknet.gov.in/v1"
_COMMODITIES_URL = f"{_BASE}/dashboard-commodities-filter"
_MARKETS_URL = f"{_BASE}/dashboard-market-filter"
_DATA_URL = f"{_BASE}/dashboard-data/"
_TIMEOUT = (5, 20)
_FILTER_TTL = 6 * 3600  # commodity/state maps rarely change

# "All" selector ids from the live payload contract.
_ALL_GROUP = 100000
_ALL_COMMODITY = 100001
_ALL_STATE = 100006
_ALL_DISTRICT = 100007
_ALL_MARKET = 100009
_ALL_VARIETY = 100021

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class AgmarknetLiveClient:
    """Location-aware Agmarknet 2.0 price client. Fails soft (returns [])."""

    def __init__(self):
        self._session: Optional[requests.Session] = None
        self._commodity_map: Dict[str, int] = {}
        self._commodity_ts = 0.0
        self._state_map: Dict[str, int] = {}
        self._state_ts = 0.0

    def _sess(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": _UA,
                "Accept": "application/json",
                "Origin": "https://agmarknet.gov.in",
                "Referer": "https://agmarknet.gov.in/",
            })
            self._session = s
        return self._session

    # ── filter maps (cached) ────────────────────────────────────────────────
    def _load_commodities(self) -> Dict[str, int]:
        if self._commodity_map and (time.time() - self._commodity_ts) < _FILTER_TTL:
            return self._commodity_map
        try:
            r = self._sess().get(_COMMODITIES_URL, timeout=_TIMEOUT)
            if r.status_code == 200 and (r.json().get("status") == "success"):
                m = {}
                for c in r.json().get("data", []) or []:
                    name = str(c.get("cmdt_name", "")).strip().lower()
                    if name and isinstance(c.get("id"), int):
                        m[name] = c["id"]
                if m:
                    self._commodity_map, self._commodity_ts = m, time.time()
        except Exception as exc:
            logger.warning("agmarknet: commodity filter failed: %s", exc)
        return self._commodity_map

    def _load_states(self) -> Dict[str, int]:
        if self._state_map and (time.time() - self._state_ts) < _FILTER_TTL:
            return self._state_map
        try:
            r = self._sess().get(_MARKETS_URL, timeout=_TIMEOUT)
            if r.status_code == 200 and (r.json().get("status") == "success"):
                m = {}
                for mk in r.json().get("data", []) or []:
                    sname = str(mk.get("state_name", "")).strip().lower()
                    sid = mk.get("state_id")
                    if sname and isinstance(sid, int):
                        m.setdefault(sname, sid)
                if m:
                    self._state_map, self._state_ts = m, time.time()
        except Exception as exc:
            logger.warning("agmarknet: market/state filter failed: %s", exc)
        return self._state_map

    @staticmethod
    def _match(name: Optional[str], table: Dict[str, int]) -> Optional[int]:
        if not name:
            return None
        w = name.strip().lower()
        if w in table:
            return table[w]
        for k, v in table.items():  # fuzzy: startswith / contains
            if k.startswith(w) or w in k:
                return v
        return None

    # ── public API (unchanged signature) ────────────────────────────────────
    def fetch_records(
        self,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
        market: Optional[str] = None,
        days: int = 3,
    ) -> List[Dict[str, Any]]:
        """Return OGD-shaped live price records, or [] on any failure."""
        try:
            commodity_id = self._match(commodity, self._load_commodities()) if commodity else None
            state_id = self._match(state, self._load_states()) if state else None

            payload = {
                "dashboard": "marketwise_price_arrival",
                "date": date.today().isoformat(),
                "group": [_ALL_GROUP],
                "commodity": [commodity_id] if commodity_id else [_ALL_COMMODITY],
                "state": state_id if state_id else _ALL_STATE,
                "district": [_ALL_DISTRICT],
                "market": [_ALL_MARKET],
                "variety": _ALL_VARIETY,
                "grades": [4],
                "format": "json",
                "limit": 100,
            }
            resp = self._sess().post(_DATA_URL, json=payload, timeout=_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("agmarknet 2.0 data POST %s", resp.status_code)
                return []
            raw = resp.json()
            if raw.get("status") not in ("success", "Success", True, 1):
                logger.warning("agmarknet 2.0 non-success: %s", raw.get("message"))
                return []
            records = (raw.get("data") or {}).get("records") or []
            out: List[Dict[str, Any]] = []
            state_label = (state or "").strip()
            for r in records:
                modal = self._num(r.get("as_on_price"))
                if modal <= 0:
                    continue
                out.append({
                    "commodity": r.get("cmdt_name", ""),
                    "state": state_label,       # request-scoped (API row is state-agg)
                    "district": "",
                    "market": f"{state_label} (state average)" if state_label else "All-India average",
                    "min_price": modal,
                    "max_price": modal,
                    "modal_price": modal,
                    "arrival_date": self._iso_date(r.get("reported_date")),
                })
            logger.info("agmarknet 2.0: %d live rows (commodity=%s state=%s)",
                        len(out), commodity, state)
            return out
        except Exception as exc:  # never fabricate on failure
            logger.warning("agmarknet 2.0 client failed: %s", exc)
            return []

    @staticmethod
    def _num(v) -> float:
        try:
            return float(str(v).replace(",", "").strip())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _iso_date(raw: str) -> str:
        raw = (raw or "").strip()
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return raw


# Singleton + backward-compatible alias (data_gov_mandi_client imports this name).
agmarknet_live_client = AgmarknetLiveClient()
agmarknet_scraper = agmarknet_live_client
