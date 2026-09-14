"""
KrishiMitra — Agmarknet Direct API Client v2.1
================================================
Uses the open Agmarknet 2.0 dashboard API (no registration needed):
    POST https://api.agmarknet.gov.in/v1/dashboard-data/

Key design decisions:
  - 1-hour in-memory cache — government API updates only once per day (~9 AM IST)
  - 30-second timeout with 2 retries — API is sometimes slow
  - Browser-like headers — required to avoid bot detection
  - Live-only contract — failures return None; historical seed rows are never
    returned by public price methods

Coverage (25 commodities confirmed):
  Cereals:  Wheat, Paddy, Maize, Jowar, Bajra, Ragi, Barley
  Oilseeds: Mustard, Groundnut, Soybean, Sunflower, Safflower, Sesame, Copra
  Pulses:   Gram, Arhar/Tur, Moong, Urad, Lentil
  Fibre:    Cotton, Jute
  Cash:     Sugarcane
  Veg:      Onion, Potato, Tomato
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .market_data_quality import INDIA_TZ

logger = logging.getLogger(__name__)

AGMARKNET_API_URL = "https://api.agmarknet.gov.in/v1/dashboard-data/"
DASHBOARD         = "marketwise_price_arrival"
REQUEST_TIMEOUT   = (8, 25)    # connect 8s, read 25s — API is sometimes slow
CACHE_TTL_SECS    = 3600       # 1 hour

# ── Commodity name → our canonical crop IDs ───────────────────────────────────
_AGMARKNET_TO_CROP_ID: Dict[str, str] = {
    "wheat":                         "wheat",
    "paddy(common)":                 "rice",
    "paddy(grade a)":                "rice",
    "maize":                         "maize",
    "jowar(sorghum)":                "jowar",
    "bajra(pearl millet/cumbu)":     "bajra",
    "ragi(finger millet)":           "ragi",
    "barley(jau)":                   "barley",
    "mustard":                       "mustard",
    "groundnut":                     "groundnut",
    "soyabean":                      "soybean",
    "sunflower/sunflower seed":      "sunflower",
    "safflower":                     "safflower",
    "sesamum(sesame,gingelly,til)":  "sesame",
    "copra":                         "copra",
    "cotton":                        "cotton",
    "jute":                          "jute",
    "sugarcane":                     "sugarcane",
    "bengal gram(gram)(whole)":      "gram",
    "black gram(urd beans)(whole)":  "urad",
    "green gram(moong)(whole)":      "moong",
    "lentil(masur)(whole)":          "lentil",
    "red gram/arhar/tur(whole)":     "arhar",
    "onion":                         "onion",
    "potato":                        "potato",
    "tomato":                        "tomato",
}

_CROP_HINDI: Dict[str, str] = {
    "wheat": "गेहूँ",      "rice": "धान",       "maize": "मक्का",
    "jowar": "ज्वार",      "bajra": "बाजरा",    "ragi": "रागी",
    "barley": "जौ",        "mustard": "सरसों",  "groundnut": "मूँगफली",
    "soybean": "सोयाबीन", "sunflower": "सूरजमुखी", "safflower": "कुसुम",
    "sesame": "तिल",       "copra": "कोपरा",    "cotton": "कपास",
    "jute": "जूट",         "sugarcane": "गन्ना","gram": "चना",
    "urad": "उड़द",         "moong": "मूँग",     "lentil": "मसूर",
    "arhar": "अरहर",       "onion": "प्याज",    "potato": "आलू",
    "tomato": "टमाटर",
}

def _has_price(record: Dict[str, Any]) -> bool:
    """True only when a row carries a usable price.

    Agmarknet returns rows with a null or empty price for markets that
    reported an arrival but no rate (seen at DADRI APMC). Counting those as an
    answer would show a farmer a mandi row with no number in it.
    """
    for key in ("as_on_price", "modal_price", "price"):
        raw = record.get(key)
        if raw in (None, "", "-"):
            continue
        try:
            if float(raw) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


# Seed prices were removed. The table held real Agmarknet rows captured on
# 12-06-2026 beside a docstring promising they were "up to a day old"; by the
# time this was audited they were 88 days old. Nothing called the accessor --
# the freshness contract had already routed every path to typed unavailability
# -- so the rows survived only as a loaded gun for the next caller who skipped
# the filter. The system may state that it does not know, but may not guess.


class AgmarknetDirectClient:
    """
    Agmarknet Direct API client with retry and live-response caching.
    No authentication required.
    """

    def __init__(self):
        self.session = requests.Session()
        # Retry on connection errors and 5xx — not on 4xx
        retry = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            # Use browser-like headers to avoid bot detection
            "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/125.0.0.0 Safari/537.36",
            "Content-Type":    "application/json",
            "Accept":          "application/json, text/plain, */*",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Referer":         "https://agmarknet.gov.in/",
            "Origin":          "https://agmarknet.gov.in",
            "sec-ch-ua":       '"Google Chrome";v="125", "Chromium";v="125"',
            "sec-fetch-site":  "same-site",
            "sec-fetch-mode":  "cors",
        })
        self._cache:    Dict[str, Any]   = {}
        self._cache_ts: Dict[str, float] = {}
        self._unavailable_until = 0.0

    def _access_unavailable(self, response) -> bool:
        if response.status_code not in (401, 403, 429):
            return False
        try:
            delay = max(10, min(int(response.headers.get("Retry-After", "60")), 300))
        except (TypeError, ValueError):
            delay = 60
        self._unavailable_until = time.monotonic() + delay
        logger.warning("Agmarknet access unavailable (HTTP %s); pausing requests for %ss", response.status_code, delay)
        return True

    # ── Public API ────────────────────────────────────────────────────────────

    def get_national_prices(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch today's national commodity prices.
        Returns cached official data if < 1 hour old, otherwise None on failure.
        """
        cache_key = "national"
        if not force_refresh and cache_key in self._cache:
            age = time.time() - self._cache_ts.get(cache_key, 0)
            if age < CACHE_TTL_SECS:
                return self._cache[cache_key]

        # Try live API
        records = self._fetch_live()
        if records:
            reported = records[0].get("reported_date", "") if records else ""
            result = self._format_response(records, reported, is_live=True)
            if not result.get("top_crops"):
                logger.warning("Agmarknet Direct: response contained no fresh official rows")
                return None
            self._cache[cache_key]    = result
            self._cache_ts[cache_key] = time.time()
            logger.info("Agmarknet Direct: loaded %d live prices for %s", len(records), reported)
            return result

        logger.warning("Agmarknet Direct: live API unavailable; no fallback prices returned")
        return None

    def get_prices_for_crops(self, crop_ids: List[str]) -> List[Dict[str, Any]]:
        """Return price rows filtered to the requested crop IDs."""
        data = self.get_national_prices()
        if not data:
            return []
        return [r for r in data.get("top_crops", []) if r.get("crop_id") in crop_ids]

    def is_available(self) -> bool:
        """Return True only when the live dashboard API produces price rows."""
        data = self.get_national_prices(force_refresh=True)
        return bool(data and data.get("is_live") and data.get("top_crops"))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_live(self) -> Optional[List[Dict[str, Any]]]:
        """Try the live API. Returns records list or None on any failure."""
        if time.monotonic() < self._unavailable_until:
            return None
        try:
            # These are Agmarknet's documented "All" selector IDs. Sending the
            # complete dashboard contract mirrors the official web request and
            # avoids relying on implicit backend defaults.
            payload = {
                "dashboard": DASHBOARD,
                "date": datetime.now(INDIA_TZ).date().isoformat(),
                "group": [100000],
                "commodity": [100001],
                "state": 100006,
                "district": [100007],
                "market": [100009],
                "variety": 100021,
                "grades": [4],
                "format": "json",
                "limit": 100,
            }
            resp = self.session.post(
                AGMARKNET_API_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            if self._access_unavailable(resp):
                return None
            resp.raise_for_status()
            raw = resp.json()
            # API returns "status": "success" (string) or status: true (bool) — handle both
            status_val = raw.get("status")
            if status_val not in (True, "success", "Success", 1):
                logger.warning("Agmarknet API non-success: status=%s msg=%s", status_val, raw.get("message"))
                return None
            records = raw.get("data", {}).get("records", [])
            return records if records else None
        except requests.exceptions.Timeout:
            logger.warning("Agmarknet Direct: timeout — no live price rows available")
        except requests.exceptions.ConnectionError as exc:
            logger.warning("Agmarknet Direct: connection error: %s", exc)
        except Exception as exc:
            logger.error("Agmarknet Direct: unexpected error: %s", exc)
        return None

    def fetch_scoped(
        self,
        *,
        state_id: Optional[int] = None,
        district_id: Optional[int] = None,
        market_id: Optional[int] = None,
        commodity_id: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Ask Agmarknet for the most local rows it will actually answer with.

        The default query this client used to send is the national "All States"
        aggregate. Agmarknet also accepts state, district and market IDs, and
        the narrower the scope the more relevant the number: measured on
        2026-09-01 for the same reported date, Wheat came back as 2523.70 for
        the Uttar Pradesh average and 2541.83 for Gautam Budh Nagar.

        Individual mandis are sparse, though -- DADRI APMC returned a single
        Maize row with no price -- so this escalates outward rather than
        insisting on the tightest scope, and reports which scope actually
        answered so the caller can label it honestly. It never invents a row:
        an empty result stays empty.
        """
        ALL = {"state": 100006, "district": 100007, "market": 100009, "commodity": 100001}
        attempts: List[Tuple[str, Dict[str, Any]]] = []
        if market_id:
            attempts.append(("market", {"state": state_id or ALL["state"],
                                        "district": [district_id or ALL["district"]],
                                        "market": [market_id]}))
        if district_id:
            attempts.append(("district", {"state": state_id or ALL["state"],
                                          "district": [district_id],
                                          "market": [ALL["market"]]}))
        if state_id:
            attempts.append(("state", {"state": state_id,
                                       "district": [ALL["district"]],
                                       "market": [ALL["market"]]}))
        attempts.append(("national", {"state": ALL["state"],
                                      "district": [ALL["district"]],
                                      "market": [ALL["market"]]}))

        for coverage, scope in attempts:
            if time.monotonic() < self._unavailable_until:
                break
            payload = {
                "dashboard": DASHBOARD,
                "date": datetime.now(INDIA_TZ).date().isoformat(),
                "group": [100000],
                "commodity": [commodity_id or ALL["commodity"]],
                "variety": 100021,
                "grades": [4],
                "format": "json",
                "limit": limit,
            }
            payload.update(scope)
            try:
                resp = self.session.post(AGMARKNET_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
                if self._access_unavailable(resp):
                    break
                resp.raise_for_status()
                raw = resp.json()
            except Exception as exc:
                logger.warning("Agmarknet scoped query (%s) failed: %s", coverage, exc)
                continue
            if raw.get("status") not in (True, "success", "Success", 1):
                # A scope with no data answers status:false -- that is a normal
                # "nothing reported here", not an error worth aborting on.
                continue
            records = ((raw.get("data") or {}).get("records")) or []
            # Rows can carry a null price (seen at DADRI APMC); those are not
            # a price and must not be counted as a usable answer.
            priced = [r for r in records if _has_price(r)]
            if priced:
                return {"records": priced, "coverage": coverage,
                        "reported_date": priced[0].get("reported_date"),
                        "scope": scope}
        return {"records": [], "coverage": None, "reported_date": None, "scope": None}

    def get_local_prices(
        self,
        *,
        state_id: Optional[int] = None,
        district_id: Optional[int] = None,
        market_id: Optional[int] = None,
        commodity_id: Optional[int] = None,
        coverage_label: Optional[str] = None,
        state_label: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Official rows for the tightest scope Agmarknet will answer with.

        Public wrapper around :meth:`fetch_scoped` that returns the same shape
        as the other price methods, so the caller can push it through the usual
        freshness filter instead of special-casing it.

        ``coverage`` records which scope actually answered -- market, district,
        state or national -- so a district average is never presented as though
        it were the selected mandi's own quote. Returns None when no scope had
        a priced row, and never falls back to the static seed rows.
        """
        scoped = self.fetch_scoped(
            state_id=state_id,
            district_id=district_id,
            market_id=market_id,
            commodity_id=commodity_id,
        )
        records = scoped.get("records") or []
        if not records:
            return None
        coverage = scoped.get("coverage") or "national"
        data = self._format_response(
            records,
            scoped.get("reported_date") or "",
            is_live=True,
            coverage_label=coverage_label,
            state_label=state_label,
        )
        data["coverage"] = coverage
        data["data_source"] = "Agmarknet 2.0 API (api.agmarknet.gov.in)"
        return data

    def _format_response(
        self,
        records: List[Dict[str, Any]],
        reported_date: str,
        is_live: bool = True,
        coverage_label: Optional[str] = None,
        state_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert Agmarknet records to the shape used by MarketPricesService."""
        from .msp_data import get_current_msp

        top_crops = []
        for r in records:
            raw_name    = (r.get("cmdt_name") or "").lower().strip()
            crop_id     = _AGMARKNET_TO_CROP_ID.get(raw_name, raw_name.replace(" ", "_"))
            modal_price = self._safe_float(r.get("as_on_price"))
            msp_price   = get_current_msp(crop_id) or get_current_msp(raw_name)
            trend       = (r.get("trend") or "").lower()

            if modal_price is None:
                continue

            profit_vs_msp = None
            if msp_price and msp_price > 0:
                profit_vs_msp = round(((modal_price - msp_price) / msp_price) * 100, 1)

            top_crops.append({
                "crop_name":       r.get("cmdt_name", crop_id.title()),
                "crop_name_hindi": _CROP_HINDI.get(crop_id, ""),
                "crop_id":         crop_id,
                "modal_price":     modal_price,
                "msp":             msp_price,
                "profit_vs_msp":   profit_vs_msp,
                "trend":           trend,
                "category":        r.get("cmdt_grp_name", ""),
                # These default to the national labels because that is the
                # only scope this client used to query. A scoped lookup passes
                # its own labels: calling a Gautam Budh Nagar figure a
                # "National Average" would misstate where the price came from,
                # which is the one thing a price screen must not do.
                "mandi_name":      coverage_label or "National Average (Agmarknet)",
                "state":           state_label or "All India",
                "one_day_price":   self._safe_float(r.get("one_day_ago_price")),
                "two_day_price":   self._safe_float(r.get("two_day_ago_price")),
                "arrival_tonnes":  self._safe_float(r.get("as_on_arrival")),
                "reported_date":   r.get("reported_date", reported_date),
                "price_source":    "agmarknet_direct",
                "is_live":         is_live,
            })

        # Keep the parsed rows before the freshness filter runs. The live gate
        # drops anything older than 24 hours, which is correct -- a two-day-old
        # figure is not a live price. But the caller's dated-official path is
        # meant to re-emit rows aged 24 hours to 7 days as clearly dated
        # references, and it was being handed the *filtered* list, i.e. nothing.
        #
        # Observed 2026-09-08: Agmarknet resumed publishing after being frozen
        # since 30-08 and was serving 23 commodities dated 06-09-2026, every row
        # with a real price and well inside the 7-day reference window. Farmers
        # still saw an empty market screen, because the live filter consumed the
        # rows two steps before anything could offer them as a dated reference.
        unfiltered_rows = list(top_crops)

        if is_live:
            from .market_data_quality import filter_fresh_live_rows

            top_crops, age_minutes, newest_date = filter_fresh_live_rows(
                top_crops, response_date=reported_date
            )
            reported_date = newest_date
        else:
            age_minutes = None

        source_label = (
            "Agmarknet 2.0 (Live — no key needed)"
            if is_live else
            "Agmarknet 2.0 (Reference prices — live API temporarily unavailable; retrying hourly)"
        )

        return {
            "status":            "success",
            "is_live":           is_live,
            "data_source":       source_label,
            "reported_date":     reported_date,
            "data_age_minutes":  age_minutes,
            "freshness":         "latest_official" if is_live and top_crops else "historical_reference",
            "top_crops":         top_crops,
            # Rows as parsed, before the 24-hour live gate. The live contract is
            # unchanged -- top_crops still holds only rows the gate accepted --
            # but a caller can now build a dated official reference from the
            # rows it rejected instead of being handed an empty list.
            "unfiltered_rows":   unfiltered_rows,
            "total_records":     len(top_crops),
            "message":           f"Latest official national prices reported {reported_date} (Agmarknet 2.0)",
            "using_demo_key":    False,
            "api_key_registered": False,
            "coverage":          "national",
            "timestamp":         datetime.now().isoformat(),
        }

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            return round(float(val), 2)
        except (TypeError, ValueError):
            return None


# ── Module-level singleton ────────────────────────────────────────────────────
agmarknet_direct = AgmarknetDirectClient()

# Both spellings are exported deliberately. unified_realtime_service imports
# `agmarknet_direct_client` for the district-scoped Priority-0a lookup, while
# monitoring_views and data_gov_mandi_client import `agmarknet_direct`. The
# former name did not exist, so that import raised ImportError inside a
# `try/except Exception` that logs a warning and falls through to the national
# path -- meaning the entire district-scoped lookup silently never ran, and
# every farmer received a national average instead of their district's price.
# Nothing failed loudly, and the tests missed it because they patch
# get_local_prices directly rather than exercising the import.
agmarknet_direct_client = agmarknet_direct
