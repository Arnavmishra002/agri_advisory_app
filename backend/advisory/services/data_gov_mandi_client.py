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

Priority chain:
  1. data.gov.in OGD API (if DATA_GOV_IN_API_KEY set and not placeholder)
  2. Agmarknet direct dashboard API (no key needed — 25 commodities)
  3. In-memory seed prices (12-06-2026 real data — labeled clearly)

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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

from .msp_data import MSP_2024_25 as _CANONICAL_MSP

# ── Configuration ─────────────────────────────────────────────────────────────
_DATA_GOV_BASE    = "https://api.data.gov.in/resource"
_RESOURCE_ID      = "9ef84268-d588-465a-a308-a864a43d0070"  # Agmarknet daily prices
_CACHE_TTL_SECS   = 3600   # 1 hour — prices update once daily at ~9 AM IST
_REQUEST_TIMEOUT  = (8, 20)  # (connect, read) seconds
_MAX_RECORDS      = 100      # per API call

# ── Placeholder fragments — never use these as real keys ─────────────────────
_PLACEHOLDERS = frozenset({
    "your_", "placeholder", "change_me", "xxx", "example",
    "insert", "api_key", "here", "demo", "test",
})


def _is_valid_key(key: str) -> bool:
    if not key or len(key) < 10:
        return False
    lower = key.lower()
    return not any(p in lower for p in _PLACEHOLDERS)


def _get_api_key() -> Optional[str]:
    key = os.getenv("DATA_GOV_IN_API_KEY", "")
    return key if _is_valid_key(key) else None


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
      data.gov.in OGD API → Agmarknet direct → seed prices (always returns data)
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
        Returns full response dict — always has data (fallback chain guarantees it).
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

        # 3. Try data.gov.in OGD API
        api_key = _get_api_key()
        if api_key:
            result = self._fetch_data_gov(api_key, commodity=commodity, state=state)
            if result and result.get("top_crops"):
                logger.info(
                    "data_gov_mandi: data.gov.in returned %d crops (commodity=%s state=%s)",
                    len(result["top_crops"]), commodity, state,
                )
                self._cache_set(cache_key, result)
                return result
            logger.warning("data_gov_mandi: data.gov.in returned no records — trying Agmarknet")

        # 4. Try Agmarknet direct dashboard API (no key needed)
        agmarknet_result = self._fetch_agmarknet_direct(commodity=commodity)
        if agmarknet_result and agmarknet_result.get("top_crops"):
            logger.info(
                "data_gov_mandi: Agmarknet direct returned %d crops",
                len(agmarknet_result["top_crops"]),
            )
            self._cache_set(cache_key, agmarknet_result)
            return agmarknet_result

        # 5. Seed fallback — always works
        logger.info("data_gov_mandi: all live sources failed — serving seed prices")
        seed = self._get_seed_result(commodity=commodity)
        # Don't cache seeds — retry live sources next request
        return seed

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
        """Fetch from official OGD Platform API."""
        params: Dict[str, Any] = {
            "api-key": api_key,
            "format":  "json",
            "limit":   _MAX_RECORDS,
            "offset":  0,
        }
        if commodity:
            params["filters[commodity]"] = commodity.title()
        if state:
            params["filters[state]"] = state

        url = f"{_DATA_GOV_BASE}/{_RESOURCE_ID}"

        try:
            resp = self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            raw = resp.json()

            records = raw.get("records") or raw.get("data") or []
            if not records:
                logger.warning("data.gov.in: empty records for commodity=%s state=%s", commodity, state)
                return None

            return self._format_datagov_response(records, is_live=True)

        except requests.exceptions.Timeout:
            logger.warning("data.gov.in: request timed out")
        except requests.exceptions.HTTPError as exc:
            logger.warning("data.gov.in: HTTP %s — %s", exc.response.status_code, exc)
        except requests.exceptions.ConnectionError as exc:
            logger.warning("data.gov.in: connection error: %s", exc)
        except (ValueError, KeyError) as exc:
            logger.warning("data.gov.in: parse error: %s", exc)
        except Exception as exc:
            logger.error("data.gov.in: unexpected error: %s", exc)
        return None

    def _format_datagov_response(
        self,
        records: List[Dict[str, Any]],
        is_live: bool = True,
    ) -> Dict[str, Any]:
        """Normalise data.gov.in OGD records to our standard shape."""
        # OGD field names: commodity, state, district, market, min_price, max_price, modal_price, arrival_date
        top_crops: List[Dict[str, Any]] = []
        seen: Dict[str, bool] = {}  # deduplicate by crop_id

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
                r.get("date") or datetime.now(tz=timezone.utc).strftime("%d-%m-%Y")
            )

            # For national view: deduplicate crop_id, keep highest modal_price record
            if crop_id in seen:
                existing = next((c for c in top_crops if c["crop_id"] == crop_id), None)
                if existing and modal_price > existing["modal_price"]:
                    top_crops.remove(existing)
                else:
                    continue

            seen[crop_id] = True
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

        # Sort: highest modal price first within category
        top_crops.sort(key=lambda x: x["modal_price"], reverse=True)

        reported = top_crops[0]["reported_date"] if top_crops else ""
        return {
            "status":              "success",
            "is_live":             is_live,
            "data_source":         "data.gov.in Official API (Agmarknet OGD)",
            "data_source_short":   "data.gov.in (live)",
            "reported_date":       reported,
            "top_crops":           top_crops,
            "total_records":       len(top_crops),
            "message":             f"Live mandi prices from data.gov.in ({len(top_crops)} commodities)",
            "api_key_registered":  True,
            "using_demo_key":      False,
            "coverage":            "national",
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

    # ── Seed data fallback ────────────────────────────────────────────────────

    def _get_seed_result(self, commodity: Optional[str] = None) -> Dict[str, Any]:
        """Return hardcoded seed prices — always available."""
        from .agmarknet_direct_client import _SEED_PRICES, _AGMARKNET_TO_CROP_ID, _CROP_HINDI as _AGMARKNET_HINDI

        top_crops = []
        for r in _SEED_PRICES:
            raw_name  = (r.get("cmdt_name") or "").lower().strip()
            crop_id   = _AGMARKNET_TO_CROP_ID.get(raw_name, raw_name.replace(" ", "_"))
            if commodity and commodity.lower() not in crop_id and commodity.lower() not in raw_name:
                continue
            try:
                modal_price = round(float(r.get("as_on_price") or 0), 2)
            except (ValueError, TypeError):
                continue
            msp = _MSP_2024_25.get(crop_id) or (float(r["msp_price"]) if r.get("msp_price") else None)
            profit_vs_msp = None
            if msp and msp > 0:
                profit_vs_msp = round(((modal_price - msp) / msp) * 100, 1)
            top_crops.append({
                "crop_name":       r.get("cmdt_name", crop_id.title()),
                "crop_name_hindi": _AGMARKNET_HINDI.get(crop_id, ""),
                "crop_id":         crop_id,
                "modal_price":     modal_price,
                "msp":             msp,
                "profit_vs_msp":   profit_vs_msp,
                "trend":           (r.get("trend") or "").lower(),
                "category":        r.get("cmdt_grp_name", ""),
                "mandi_name":      "National Average (Reference)",
                "state":           "All India",
                "reported_date":   r.get("reported_date", ""),
                "price_source":    "seed_fallback",
                "is_live":         False,
            })

        return {
            "status":             "success",
            "is_live":            False,
            "data_source":        "Reference Prices (Agmarknet 12-06-2026 — live API temporarily unavailable)",
            "data_source_short":  "Reference data",
            "reported_date":      "12-06-2026",
            "top_crops":          top_crops,
            "total_records":      len(top_crops),
            "message":            "Using reference prices — live API retried every hour automatically",
            "api_key_registered": bool(_get_api_key()),
            "using_demo_key":     False,
            "coverage":           "national",
            "timestamp":          datetime.now(tz=timezone.utc).isoformat(),
        }

    # ── Redis cache helpers ───────────────────────────────────────────────────

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
