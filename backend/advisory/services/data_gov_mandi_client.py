"""
KrishiMitra — data.gov.in Official Mandi Price Client v1.0
===========================================================
Primary market price source: OGD Platform API (data.gov.in)
  Resource: Agmarknet daily mandi prices
  Resource ID: 9ef84268-d588-465a-a308-a864a43d0070
  Docs: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi

Why this is better than scraping Agmarknet directly:
  - Official REST API — no HTML parsing, no fragile XPath selectors
  - Same data source (data.gov.in is the official Agmarknet data mirror)
  - Free API key — register at https://data.gov.in/user/register
  - Stable endpoint — government API versioning, no URL changes overnight
  - Supports: commodity filter, state filter, market filter, date filter, pagination

Live source chain:
  1. data.gov.in OGD daily feed (if DATA_GOV_IN_API_KEY set and not a placeholder)
  2. data.gov.in OGD history feed: the latest earlier trading day, live only
     while inside the freshness window, otherwise a dated official reference
  3. Agmarknet direct dashboard API (since Nov 2026 it demands a CAPTCHA from
     automated clients, so in practice this step no longer returns rows)
  4. Unavailable response with no price rows

Redis caching:
  - With REDIS_URL: 1-hour TTL, shared across all Gunicorn workers
  - Without REDIS_URL: in-process dict cache, per-worker (still 1-hour TTL)
  - Cache key: km:mandi:{commodity}:{state} (namespaced)

Coverage (data.gov.in):
  All commodities in Agmarknet + regional mandis across all 28 states
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

from .msp_data import MSP_2024_25 as _CANONICAL_MSP
from .api_keys import is_real_key
from .market_data_quality import INDIA_TZ

# ── Configuration ─────────────────────────────────────────────────────────────
_DATA_GOV_BASE    = "https://api.data.gov.in/resource"
_RESOURCE_ID      = "9ef84268-d588-465a-a308-a864a43d0070"  # Agmarknet daily prices (current day only)
# "Variety-wise Daily Market Prices Data of Commodity": the dated history of
# the same Agmarknet reports, refreshed overnight.
_HISTORY_RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
# Days to look back in the history feed, one request each.
_HISTORY_MAX_DAYS = max(1, min(int(os.getenv("MANDI_HISTORY_LOOKBACK_DAYS", "4")), 7))
_CACHE_TTL_SECS   = 3600   # 1 hour — prices update once daily at ~9 AM IST
_REQUEST_TIMEOUT  = (
    max(0.5, float(os.getenv("MANDI_HTTP_CONNECT_TIMEOUT_S", "2"))),
    max(1.0, float(os.getenv("MANDI_HTTP_READ_TIMEOUT_S", "8"))),
)  # (connect, read) seconds; fail fast rather than block advice
_MAX_RECORDS      = 100      # per API call

# ── Placeholder fragments — never use these as real keys ─────────────────────
_PLACEHOLDERS = frozenset({
    "your_", "placeholder", "change_me", "xxx", "example",
    "insert", "api_key", "here", "demo", "test",
})


def _is_valid_key(key: str) -> bool:
    """Retained name; the rule now lives in api_keys so every reader shares it."""
    return is_real_key(key)


def _get_api_key() -> Optional[str]:
    key = os.getenv("DATA_GOV_IN_API_KEY", "")
    return key if _is_valid_key(key) else None


# Agmarknet's own state spellings, which both OGD feeds keep. Checked against
# the feeds on 21 Nov 2026: "Chhattisgarh", "Puducherry" and "Delhi" match
# nothing there; these spellings do.
_OGD_STATE_SPELLINGS: Dict[str, Tuple[str, ...]] = {
    "chhattisgarh": ("Chattisgarh", "Chhattisgarh"),
    "chattisgarh": ("Chattisgarh", "Chhattisgarh"),
    "uttarakhand": ("Uttarakhand", "Uttrakhand"),
    "uttrakhand": ("Uttarakhand", "Uttrakhand"),
    "uttaranchal": ("Uttarakhand", "Uttrakhand"),
    "puducherry": ("Pondicherry", "Puducherry"),
    "pondicherry": ("Pondicherry", "Puducherry"),
    "delhi": ("NCT of Delhi",),
    "new delhi": ("NCT of Delhi",),
    "nct of delhi": ("NCT of Delhi",),
    "orissa": ("Odisha",),
}


def ogd_state_spellings(state: Optional[str]) -> Tuple[str, ...]:
    """Names to try for *state* in the OGD feeds, most likely first."""
    name = " ".join(str(state or "").split())
    if not name:
        return ()
    return _OGD_STATE_SPELLINGS.get(name.lower(), (name,))


def _row_in_state(record: Dict[str, Any], spellings: Tuple[str, ...]) -> bool:
    wanted = {s.lower() for s in spellings}
    value = " ".join(str(record.get("state") or record.get("State") or "").split()).lower()
    return value in wanted


# ── Canonical crop ID maps ────────────────────────────────────────────────────
_COMMODITY_TO_CROP_ID: Dict[str, str] = {
    "wheat":         "wheat",
    "paddy":         "rice",
    "rice":          "rice",
    "maize":         "maize",
    "jowar":         "jowar",
    "bajra":         "bajra",
    "ragi":          "ragi",
    "barley":        "barley",
    "mustard":       "mustard",
    "groundnut":     "groundnut",
    "soyabean":      "soybean",
    "soybean":       "soybean",
    "sunflower":     "sunflower",
    "sesame":        "sesame",
    "sesamum":       "sesame",
    "cotton":        "cotton",
    "jute":          "jute",
    "sugarcane":     "sugarcane",
    "gram":          "gram",
    "urad":          "urad",
    "moong":         "moong",
    "masur":         "lentil",
    "lentil":        "lentil",
    "arhar":         "arhar",
    "tur":           "arhar",
    "onion":         "onion",
    "potato":        "potato",
    "tomato":        "tomato",
    "garlic":        "garlic",
    "ginger":        "ginger",
    "chilli":        "chilli",
    "turmeric":      "turmeric",
    "banana":        "banana",
    "mango":         "mango",
}

_CROP_HINDI: Dict[str, str] = {
    "wheat": "गेहूँ",      "rice": "धान",         "maize": "मक्का",
    "jowar": "ज्वार",      "bajra": "बाजरा",       "ragi": "रागी",
    "barley": "जौ",        "mustard": "सरसों",     "groundnut": "मूँगफली",
    "soybean": "सोयाबीन",  "sunflower": "सूरजमुखी","sesame": "तिल",
    "cotton": "कपास",      "jute": "जूट",          "sugarcane": "गन्ना",
    "gram": "चना",         "urad": "उड़द",          "moong": "मूँग",
    "lentil": "मसूर",      "arhar": "अरहर",        "onion": "प्याज",
    "potato": "आलू",       "tomato": "टमाटर",      "garlic": "लहसुन",
    "ginger": "अदरक",      "chilli": "मिर्च",      "turmeric": "हल्दी",
    "banana": "केला",      "mango": "आम",
}

# MSP table used for profit-vs-MSP calculation. Keep this delegated to
# msp_data.py so market, crop, chatbot, and DB seeding cannot drift apart.
_MSP_2024_25: Dict[str, float] = {
    crop_id: float(value) for crop_id, value in _CANONICAL_MSP.items()
}


class DataGovMandiClient:
    """
    Official data.gov.in mandi price client.

    Falls back gracefully through:
      data.gov.in OGD API → Agmarknet direct → unavailable (no synthetic prices)
    """

    def __init__(self):
        self._session = self._build_session()
        # In-process cache: {cache_key: (data, timestamp)}
        self._mem_cache: Dict[str, Tuple[Any, float]] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_national_prices(
        self,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch mandi prices for a commodity/state.
        Return only official live rows. Missing live data produces an empty,
        explicit unavailable response.
        """
        cache_key = self._cache_key(commodity, state)

        # 1. Check Redis cache
        cached = self._redis_get(cache_key)
        if not force_refresh and cached:
            logger.debug("data_gov_mandi: Redis cache hit for %s", cache_key)
            return cached

        # 2. Check in-process cache
        if not force_refresh and cache_key in self._mem_cache:
            data, ts = self._mem_cache[cache_key]
            if time.time() - ts < _CACHE_TTL_SECS:
                logger.debug("data_gov_mandi: mem cache hit for %s", cache_key)
                return data

        # 3. Try data.gov.in OGD API: today's feed first, then the dated history
        # feed. The daily feed only holds the current day, and states report
        # through the day (measured 21 Nov 2026, ~10:00 IST: Tamil Nadu 5,233
        # rows, Rajasthan, Karnataka and Delhi none), so the history feed is
        # what gives most farmers their latest official price in the morning.
        api_key = _get_api_key()
        dated_candidate: Optional[Dict[str, Any]] = None
        if api_key:
            result = self._fetch_data_gov(api_key, commodity=commodity, state=state)
            if result and result.get("top_crops"):
                logger.info(
                    "data_gov_mandi: data.gov.in returned %d crops (commodity=%s state=%s)",
                    len(result["top_crops"]), commodity, state,
                )
                self._cache_set(cache_key, result)
                return result
            if result and result.get("unfiltered_rows"):
                dated_candidate = result
            history = self._fetch_data_gov_history(api_key, commodity=commodity, state=state)
            if history and history.get("top_crops"):
                logger.info(
                    "data_gov_mandi: data.gov.in history returned %d crops for %s (commodity=%s state=%s)",
                    len(history["top_crops"]), history.get("reported_date"), commodity, state,
                )
                self._cache_set(cache_key, history)
                return history
            if history and history.get("unfiltered_rows"):
                dated_candidate = history
            logger.warning("data_gov_mandi: data.gov.in has no current rows — trying Agmarknet")

        # 4. Try Agmarknet's national dashboard only for national requests.
        # It cannot satisfy a state filter and must never be presented as local.
        agmarknet_result = None
        if not state:
            agmarknet_result = self._fetch_agmarknet_direct(commodity=commodity)
        if agmarknet_result and agmarknet_result.get("top_crops"):
            logger.info(
                "data_gov_mandi: Agmarknet direct returned %d crops",
                len(agmarknet_result["top_crops"]),
            )
            self._cache_set(cache_key, agmarknet_result)
            return agmarknet_result

        # 5. Last resort: scrape the Agmarknet website (SearchCmmMkt.aspx).
        # Records come back in OGD field shape and go through the SAME formatter
        # + freshness filter, so scraped rows are labelled and vetted identically
        # to API rows — stale/undated scraped rows are dropped, never shown live.
        try:
            from .agmarknet_scraper import agmarknet_scraper
            scraped = agmarknet_scraper.fetch_records(commodity=commodity, state=state, days=3)
            if scraped:
                formatted = self._format_datagov_response(scraped, state=state, is_live=True)
                if formatted and formatted.get("top_crops"):
                    formatted["data_source"] = "Agmarknet website (scraped)"
                    formatted["data_source_short"] = "Agmarknet live (scraped)"
                    logger.info(
                        "data_gov_mandi: Agmarknet scrape returned %d fresh crops",
                        len(formatted["top_crops"]),
                    )
                    self._cache_set(cache_key, formatted)
                    return formatted
        except Exception as exc:
            logger.warning("data_gov_mandi: Agmarknet scrape failed: %s", exc)

        logger.warning(
            "data_gov_mandi: no official live rows (commodity=%s state=%s)",
            commodity,
            state,
        )
        dated = dated_candidate or {}
        return {
            "status": "unavailable",
            "is_live": False,
            # The caller turns these into a dated official reference, shown
            # with its own date and never as today's price.
            "data_source": dated.get("data_source") or "Agmarknet/data.gov.in live feeds",
            "data_source_short": "Live feed unavailable",
            "reported_date": dated.get("reported_date", ""),
            "unfiltered_rows": dated.get("unfiltered_rows", []),
            "top_crops": [],
            "total_records": 0,
            "message": "No current official mandi price rows are available.",
            "api_key_registered": bool(api_key),
            "using_demo_key": False,
            "coverage": "state" if state else "national",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def get_prices_for_crops(self, crop_ids: List[str]) -> List[Dict[str, Any]]:
        """Return price rows filtered to specific crop IDs."""
        data = self.get_national_prices()
        return [r for r in data.get("top_crops", []) if r.get("crop_id") in crop_ids]

    # ── data.gov.in OGD fetch ─────────────────────────────────────────────────

    def _fetch_data_gov(
        self,
        api_key: str,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch today's rows from the official OGD daily feed.

        ``filters[state]`` on this feed is a full-text match, so "Uttar
        Pradesh" also returned Madhya, Andhra and Himachal Pradesh rows (129
        rows against 6 exact ones on 21 Nov 2026). ``state.keyword`` is the
        exact match, and rows are checked again after the fetch.
        """
        url = f"{_DATA_GOV_BASE}/{_RESOURCE_ID}"
        spellings = ogd_state_spellings(state)
        for spelling in spellings or (None,):
            params: Dict[str, Any] = {
                "api-key": api_key,
                "format":  "json",
                "limit":   _MAX_RECORDS,
                "offset":  0,
            }
            if commodity:
                params["filters[commodity]"] = commodity.title()
            if spelling:
                params["filters[state.keyword]"] = spelling
            records = self._get_records(url, params, "daily feed")
            if records is None:
                return None
            if state:
                records = [r for r in records if _row_in_state(r, spellings)]
            if records:
                return self._format_datagov_response(records, state=state, is_live=True)
        logger.warning("data.gov.in: no daily rows for commodity=%s state=%s", commodity, state)
        return None

    def _fetch_data_gov_history(
        self,
        api_key: str,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Latest earlier trading day from the OGD history feed.

        The history feed is refreshed overnight, so the newest day it can hold
        is yesterday. Each day is one request; the first failed request ends
        the search so a slow feed costs one timeout, not several.
        """
        url = f"{_DATA_GOV_BASE}/{_HISTORY_RESOURCE_ID}"
        spellings = ogd_state_spellings(state)
        today = datetime.now(INDIA_TZ).date()
        for days_back in range(1, _HISTORY_MAX_DAYS + 1):
            day = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
            for spelling in spellings or (None,):
                # This feed's field names are capitalised, and its State filter
                # is already an exact match.
                params: Dict[str, Any] = {
                    "api-key": api_key,
                    "format": "json",
                    "limit": _MAX_RECORDS,
                    "offset": 0,
                    "filters[Arrival_Date]": day,
                }
                if spelling:
                    params["filters[State]"] = spelling
                if commodity:
                    params["filters[Commodity]"] = commodity.title()
                records = self._get_records(url, params, "history feed")
                if records is None:
                    return None
                if state:
                    records = [r for r in records if _row_in_state(r, spellings)]
                if records:
                    formatted = self._format_datagov_response(records, state=state, is_live=True)
                    if formatted:
                        formatted["data_source"] = "data.gov.in Official API (Agmarknet daily price history)"
                        formatted["data_source_short"] = "data.gov.in (latest reported day)"
                    return formatted
        return None

    def _get_records(
        self, url: str, params: Dict[str, Any], label: str
    ) -> Optional[List[Dict[str, Any]]]:
        """GET one page. [] means no rows; None means the request failed.

        The key travels in the query string, so exception text (which carries
        the full URL) is never logged.
        """
        try:
            resp = self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("data.gov.in %s: HTTP %s", label, resp.status_code)
                return None
            raw = resp.json()
            records = raw.get("records") or raw.get("data") or []
            return records if isinstance(records, list) else []
        except requests.exceptions.Timeout:
            logger.warning("data.gov.in %s: request timed out", label)
        except requests.exceptions.ConnectionError:
            logger.warning("data.gov.in %s: connection error", label)
        except (ValueError, KeyError):
            logger.warning("data.gov.in %s: response was not valid JSON", label)
        except Exception as exc:
            logger.error("data.gov.in %s: unexpected %s", label, type(exc).__name__)
        return None

    def _format_datagov_response(
        self,
        records: List[Dict[str, Any]],
        state: Optional[str] = None,
        is_live: bool = True,
    ) -> Dict[str, Any]:
        """Normalise data.gov.in OGD records to our standard shape."""
        # OGD field names: commodity, state, district, market, min_price, max_price, modal_price, arrival_date
        top_crops: List[Dict[str, Any]] = []

        for r in records:
            raw_name   = (r.get("commodity") or r.get("Commodity") or "").lower().strip()
            crop_id    = _COMMODITY_TO_CROP_ID.get(raw_name) or raw_name.replace(" ", "_")

            try:
                modal_price = round(float(r.get("modal_price") or r.get("Modal_Price") or 0), 2)
            except (ValueError, TypeError):
                continue
            if modal_price <= 0:
                continue

            msp = _MSP_2024_25.get(crop_id)
            profit_vs_msp = None
            if msp and msp > 0:
                profit_vs_msp = round(((modal_price - msp) / msp) * 100, 1)

            try:
                min_p = round(float(r.get("min_price") or r.get("Min_Price") or modal_price), 2)
                max_p = round(float(r.get("max_price") or r.get("Max_Price") or modal_price), 2)
            except (ValueError, TypeError):
                min_p = max_p = modal_price

            arrival_date = (
                r.get("arrival_date") or r.get("Arrival_Date") or
                r.get("date") or r.get("Date")
            )
            if not arrival_date:
                # Never manufacture a current date for an undated upstream row.
                continue

            top_crops.append({
                "crop_name":       (r.get("commodity") or r.get("Commodity") or crop_id).title(),
                "crop_name_hindi": _CROP_HINDI.get(crop_id, ""),
                "crop_id":         crop_id,
                "modal_price":     modal_price,
                "min_price":       min_p,
                "max_price":       max_p,
                "msp":             msp,
                "profit_vs_msp":   profit_vs_msp,
                "trend":           "up" if profit_vs_msp and profit_vs_msp > 0 else "down",
                "category":        self._guess_category(crop_id),
                "mandi_name":      r.get("market") or r.get("Market") or "National Average",
                "state":           r.get("state") or r.get("State") or "All India",
                "district":        r.get("district") or r.get("District") or "",
                "reported_date":   arrival_date,
                "price_source":    "data_gov_in_official",
                "is_live":         is_live,
            })

        if not top_crops:
            return {}

        # One real row per crop: the mandi in the middle of the reported
        # prices. The old rule kept the highest-priced mandi, which put the
        # state's best price in front of the farmer as if it were typical.
        by_crop: Dict[str, List[Dict[str, Any]]] = {}
        for row in top_crops:
            by_crop.setdefault(row["crop_id"], []).append(row)
        top_crops = []
        for rows in by_crop.values():
            rows.sort(key=lambda x: x["modal_price"])
            chosen = dict(rows[(len(rows) - 1) // 2])
            chosen["mandis_reporting"] = len(rows)
            top_crops.append(chosen)

        # Sort: highest modal price first within category
        top_crops.sort(key=lambda x: x["modal_price"], reverse=True)

        if is_live:
            from .market_data_quality import filter_fresh_live_rows

            parsed_rows = list(top_crops)
            top_crops, age_minutes, newest_date = filter_fresh_live_rows(top_crops)
            if not top_crops:
                # Too old to call live. Hand the dated rows back so the caller
                # can show them as an official reference with their own date.
                return {
                    "status": "unavailable",
                    "is_live": False,
                    "data_source": "data.gov.in Official API (Agmarknet OGD)",
                    "reported_date": parsed_rows[0].get("reported_date", ""),
                    "unfiltered_rows": parsed_rows,
                    "top_crops": [],
                    "total_records": 0,
                    "coverage": "state" if state else "national",
                }
        else:
            age_minutes, newest_date = None, ""

        reported = newest_date or (top_crops[0]["reported_date"] if top_crops else "")
        return {
            "status":              "success",
            "is_live":             is_live,
            "data_source":         "data.gov.in Official API (Agmarknet OGD)",
            "data_source_short":   "data.gov.in (live)",
            "reported_date":       reported,
            "data_age_minutes":    age_minutes,
            "freshness":           "latest_official" if is_live else "historical_reference",
            "top_crops":           top_crops,
            "total_records":       len(top_crops),
            "message":             f"Live mandi prices from data.gov.in ({len(top_crops)} commodities)",
            "api_key_registered":  True,
            "using_demo_key":      False,
            "coverage":            "state" if state else "national",
            "requested_state":     state or "",
            "timestamp":           datetime.now(tz=timezone.utc).isoformat(),
        }

    # ── Agmarknet direct fallback ─────────────────────────────────────────────

    def _fetch_agmarknet_direct(
        self, commodity: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Use the existing Agmarknet direct client as fallback."""
        try:
            from .agmarknet_direct_client import agmarknet_direct
            raw = agmarknet_direct.get_national_prices()
            if not raw or not raw.get("top_crops"):
                return None
            # Tag source correctly
            result = dict(raw)
            result["data_source_short"] = "Agmarknet 2.0"
            # Filter by commodity if requested
            if commodity:
                comm_lower = commodity.lower()
                filtered = [
                    c for c in result["top_crops"]
                    if comm_lower in c.get("crop_id", "").lower()
                    or comm_lower in c.get("crop_name", "").lower()
                ]
                if filtered:
                    result["top_crops"] = filtered
            return result
        except Exception as exc:
            logger.warning("Agmarknet direct fallback failed: %s", exc)
            return None

    # Seed data fallback removed: see the note in agmarknet_direct_client.
    # This accessor imported that table and was itself never called; the
    # live path already returns typed unavailability, which the tests assert.

    @staticmethod
    def _cache_key(commodity: Optional[str], state: Optional[str]) -> str:
        def token(value: Optional[str], fallback: str) -> str:
            if not value:
                return fallback
            return (
                str(value)
                .strip()
                .lower()
                .replace(" ", "_")
                .replace(":", "_")
                .replace("/", "_")
                .replace("\\", "_")
            )
        parts = f"{token(commodity, 'all')}:{token(state, 'national')}"
        return f"km:mandi:{parts}"

    @staticmethod
    def _redis_get(key: str) -> Optional[Dict[str, Any]]:
        try:
            from django.core.cache import caches
            cache = caches["market_cache"]
            val = cache.get(key)
            if val:
                return json.loads(val) if isinstance(val, str) else val
        except Exception:
            pass
        return None

    @staticmethod
    def _redis_set(key: str, data: Dict[str, Any]) -> None:
        try:
            from django.core.cache import caches
            cache = caches["market_cache"]
            cache.set(key, json.dumps(data, default=str), timeout=_CACHE_TTL_SECS)
        except Exception:
            pass

    def _cache_set(self, key: str, data: Dict[str, Any]) -> None:
        """Write to both Redis (if available) and in-process dict."""
        self._redis_set(key, data)
        self._mem_cache[key] = (data, time.time())

    # ── HTTP session ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent":  "KrishiMitra/4.0 (agri advisory; https://github.com/Arnavmishra002/agri_advisory_app)",
            "Accept":      "application/json",
        })
        return session

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _guess_category(crop_id: str) -> str:
        _CATEGORY_MAP = {
            "wheat": "Cereals", "rice": "Cereals", "maize": "Cereals",
            "jowar": "Cereals", "bajra": "Cereals", "ragi": "Cereals", "barley": "Cereals",
            "mustard": "Oilseeds", "groundnut": "Oilseeds", "soybean": "Oilseeds",
            "sunflower": "Oilseeds", "sesame": "Oilseeds", "cotton": "Fibre",
            "jute": "Fibre", "sugarcane": "Cash Crops",
            "gram": "Pulses", "arhar": "Pulses", "moong": "Pulses",
            "urad": "Pulses", "lentil": "Pulses",
            "onion": "Vegetables", "potato": "Vegetables", "tomato": "Vegetables",
            "garlic": "Vegetables", "ginger": "Spices", "chilli": "Spices",
            "turmeric": "Spices", "banana": "Fruits", "mango": "Fruits",
        }
        return _CATEGORY_MAP.get(crop_id, "Other")

    @staticmethod
    def has_valid_api_key() -> bool:
        """True if a real (non-placeholder) data.gov.in API key is configured."""
        return _get_api_key() is not None


# ── Module-level singleton ────────────────────────────────────────────────────
data_gov_mandi_client = DataGovMandiClient()
