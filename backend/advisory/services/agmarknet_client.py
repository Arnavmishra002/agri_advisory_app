"""
Official Agmarknet 2.0 dashboard API (api.agmarknet.gov.in/v1).

Used for live mandi prices when data.gov.in is slow or unavailable.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

AGMARKNET_BASE = "https://api.agmarknet.gov.in/v1"
DEFAULT_TIMEOUT = (5, 30)  # connect, read seconds
DASHBOARD_NAME = "marketwise_price_arrival"
MARKET_PRICE_DASHBOARD = "cumm_data_sp"

# Location substring -> possible Agmarknet / data.gov.in state labels
STATE_NAME_ALIASES: Dict[str, List[str]] = {
    "delhi": ["Delhi", "NCT of Delhi", "National Capital Territory of Delhi"],
    "new delhi": ["Delhi", "NCT of Delhi", "National Capital Territory of Delhi"],
    "rohini": ["Delhi", "NCT of Delhi"],
    "dwarka": ["Delhi", "NCT of Delhi"],
    "saket": ["Delhi", "NCT of Delhi"],
    "karol bagh": ["Delhi", "NCT of Delhi"],
    "noida": ["Uttar Pradesh"],
    "greater noida": ["Uttar Pradesh"],
    "mumbai": ["Maharashtra"],
    "pune": ["Maharashtra"],
    "bangalore": ["Karnataka", "Bengaluru"],
    "bengaluru": ["Karnataka"],
    "chennai": ["Tamil Nadu"],
    "kolkata": ["West Bengal"],
    "hyderabad": ["Telangana"],
    "ahmedabad": ["Gujarat"],
    "jaipur": ["Rajasthan"],
    "lucknow": ["Uttar Pradesh"],
    "patna": ["Bihar"],
    "chandigarh": ["Punjab", "Haryana"],
    "indore": ["Madhya Pradesh"],
    "bhopal": ["Madhya Pradesh"],
    "nagpur": ["Maharashtra"],
    "nashik": ["Maharashtra"],
    "surat": ["Gujarat"],
    "vadodara": ["Gujarat"],
    "kanpur": ["Uttar Pradesh"],
    "varanasi": ["Uttar Pradesh"],
    "agra": ["Uttar Pradesh"],
    "meerut": ["Uttar Pradesh"],
    "ghaziabad": ["Uttar Pradesh"],
    "gurgaon": ["Haryana"],
    "gurugram": ["Haryana"],
    "faridabad": ["Haryana"],
    "amritsar": ["Punjab"],
    "ludhiana": ["Punjab"],
    "guwahati": ["Assam"],
    "kochi": ["Kerala"],
    "thiruvananthapuram": ["Kerala"],
    "visakhapatnam": ["Andhra Pradesh"],
    "vijayawada": ["Andhra Pradesh"],
    "coimbatore": ["Tamil Nadu"],
    "madurai": ["Tamil Nadu"],
    "ranchi": ["Jharkhand"],
    "raipur": ["Chhattisgarh"],
    "chhattisgarh": ["Chattisgarh"],
    "odisha": ["Odisha", "Orissa"],
    "dehradun": ["Uttarakhand"],
    "shimla": ["Himachal Pradesh"],
    "srinagar": ["Jammu and Kashmir"],
    "jammu": ["Jammu and Kashmir"],
}


class AgmarknetClient:
    """Client for Agmarknet 2.0 public price/arrival endpoints."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
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
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self._filters_cache: Optional[Dict[str, Any]] = None
        self._filters_cache_at: Optional[datetime] = None
        self._filters_ttl = timedelta(hours=12)
        self._rate_limited_until = 0.0

    def list_markets_for_location(
        self,
        location: str,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """All Agmarknet-registered markets for the resolved state (full mandi list)."""
        filters = self._get_filters()
        if not filters:
            return []

        state_id, state_name = (None, None)
        if state:
            state_id, state_name = self._resolve_state(state, filters)
        if not state_id:
            state_id, state_name = self._resolve_state(location, filters)

        state_names = {state_name.lower()} if state_name else set()
        if state:
            state_names.add(state.strip().lower())
        for key, aliases in STATE_NAME_ALIASES.items():
            if key in location.lower() or (state and key in state.lower()):
                state_names.update(a.lower() for a in aliases)

        markets_raw = self._list_from_filters(
            filters, "market_data", "market", "markets", "market_list", "apmc_list"
        )
        out: List[Dict[str, Any]] = []
        seen = set()
        for item in markets_raw:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("mkt_name")
                or item.get("market_name")
                or item.get("name")
                or item.get("Market")
                or ""
            ).strip()
            if not name or len(name) < 2:
                continue
            item_state = (
                item.get("state_name")
                or item.get("State")
                or item.get("state")
                or ""
            )
            sid = item.get("state_id") or item.get("stateId")
            match = False
            if state_id is not None and sid is not None and str(sid) == str(state_id):
                match = True
            elif item_state and state_names:
                isl = item_state.lower()
                match = any(sn in isl or isl in sn for sn in state_names)
            elif not state_names and not state_id:
                match = True
            if not match:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": name,
                "district": item.get("district_name") or item.get("district") or "",
                "state": item_state or state_name or state or "",
                "source": "Agmarknet 2.0 API",
                "registered": True,
                # Registry membership does not prove a current price submission.
                # Exact prices are verified only when the mandi is selected.
                "live": False,
                "commodity_count": 0,
            })
        out.sort(key=lambda m: m["name"].lower())
        return out

    def get_market_prices(
        self,
        location: str,
        mandi: Optional[str] = None,
        crop: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch daily mandi prices for a location; returns normalized dict or None."""
        filters = self._get_filters()
        if not filters:
            return None

        state_id, state_name = (None, None)
        if state:
            state_id, state_name = self._resolve_state(state, filters)
        if not state_id:
            state_id, state_name = self._resolve_state(location, filters)
        if not state_id:
            logger.warning(
                "Agmarknet: could not resolve state for location=%s state=%s",
                location,
                state,
            )
            return None

        commodity_filter: Dict[str, Any] = {}
        if crop:
            commodity_id = self._resolve_commodity_id(crop, filters)
            if commodity_id:
                commodity_filter["commodity"] = [commodity_id]

        market = None
        if mandi:
            market = self._resolve_market(mandi, state_id, filters)
            if not market:
                logger.info("Agmarknet: market '%s' is not registered for state %s", mandi, state_name)
                return None

        records: List[Dict[str, Any]] = []
        if market:
            # Agmarknet's own web app uses the cumulative price report for an
            # individual APMC. The marketwise report is only a state summary;
            # applying market IDs to it returns no rows even when the APMC has
            # submitted prices.
            latest_report = self._post_report({
                "dashboard": DASHBOARD_NAME,
                "state": state_id,
                "format": "json",
                "page": 1,
                "limit": 100,
            })
            latest_rows = self._extract_records(latest_report) if latest_report else []
            latest_date = self._reported_date_to_iso(
                latest_rows[0].get("reported_date") if latest_rows else None
            )
            candidate_dates = [latest_date] if latest_date else []
            candidate_dates.extend(
                (date.today() - timedelta(days=offset)).isoformat()
                for offset in range(4)
            )
            seen_dates = set()
            payloads = []
            for report_date in candidate_dates:
                if not report_date or report_date in seen_dates:
                    continue
                seen_dates.add(report_date)
                payload = {
                    "dashboard": MARKET_PRICE_DASHBOARD,
                    "state": [state_id],
                    "market": [market[0]],
                    "date": report_date,
                    "format": "json",
                    "page": 1,
                    "limit": 100,
                    **commodity_filter,
                }
                if market[1] is not None:
                    payload["district"] = [market[1]]
                payloads.append(payload)
        else:
            base_payload: Dict[str, Any] = {
                "dashboard": DASHBOARD_NAME,
                "state": state_id,
                "format": "json",
                "page": 1,
                "limit": 100,
                **commodity_filter,
            }
            # Omitting date asks Agmarknet for its latest published trading day.
            payloads = [base_payload] + [
                {**base_payload, "date": (date.today() - timedelta(days=offset)).isoformat()}
                for offset in range(4)
            ]

        for payload in payloads:
            report = self._post_report(payload)
            if not report:
                continue
            records = self._extract_records(report)
            if records:
                break

        if not records:
            return None

        crops = self._normalize_records(records, location, state_name or state_id, mandi)
        if not crops:
            return None

        return {
            "status": "success",
            "is_live": True,
            "location": location,
            "state": state_name,
            "data_source": "Agmarknet 2.0 API (api.agmarknet.gov.in)",
            "data_source_short": "Agmarknet 2.0 live",
            "reported_date": crops[0].get("reported_date", ""),
            "coverage": "market" if mandi else "state",
            "api_key_registered": False,
            "using_demo_key": False,
            "timestamp": datetime.now().isoformat(),
            "top_crops": crops[:20],
            "total_records": len(crops),
            "message": f"{len(crops)} live mandi records from Agmarknet",
        }

    @staticmethod
    def _reported_date_to_iso(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        for date_format in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, date_format).date().isoformat()
            except ValueError:
                continue
        return None

    def _get_filters(self) -> Optional[Dict[str, Any]]:
        now = datetime.now()
        if self._filters_cache and self._filters_cache_at:
            if now - self._filters_cache_at < self._filters_ttl:
                return self._filters_cache

        try:
            resp = self.session.get(
                f"{AGMARKNET_BASE}/dashboard-filters/",
                params={"dashboard_name": DASHBOARD_NAME},
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning("Agmarknet filters HTTP %s", resp.status_code)
                return None
            body = resp.json()
            if body.get("status") is False:
                logger.warning("Agmarknet filters error: %s", body.get("message"))
                return None
            data = body.get("data") if isinstance(body.get("data"), dict) else body
            self._filters_cache = data
            self._filters_cache_at = now
            return data
        except requests.RequestException as exc:
            logger.warning("Agmarknet filters unreachable: %s", exc)
            return None

    def _post_report(self, payload: Dict[str, Any]) -> Optional[Any]:
        url = f"{AGMARKNET_BASE}/dashboard-data/"
        if time.monotonic() < self._rate_limited_until:
            return None
        try:
            resp = self.session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 429:
                try:
                    retry_after = max(10, min(int(resp.headers.get("Retry-After", "60")), 300))
                except (TypeError, ValueError):
                    retry_after = 60
                self._rate_limited_until = time.monotonic() + retry_after
                logger.warning(
                    "Agmarknet dashboard rate limited; suppressing calls for %ss",
                    retry_after,
                )
                return None
            if resp.status_code != 200:
                logger.warning("Agmarknet dashboard HTTP %s", resp.status_code)
                return None
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Agmarknet dashboard request failed: %s", exc)
            return None

    def _resolve_state(
        self, location: str, filters: Dict[str, Any]
    ) -> Tuple[Optional[Any], Optional[str]]:
        states = self._list_from_filters(filters, "state_data", "state", "states", "state_list", "statelist")
        loc = location.lower().strip()
        candidates: List[str] = [location.strip()]
        for key, aliases in STATE_NAME_ALIASES.items():
            if key in loc:
                candidates.extend(aliases)

        # 1) Try exact or substring match first
        for state in states:
            if not isinstance(state, dict):
                continue
            name = (
                state.get("state_name")
                or state.get("name")
                or state.get("State")
                or ""
            ).strip()
            if not name:
                continue
            sid = state.get("state_id") or state.get("id") or state.get("stateId")
            name_l = name.lower()
            for cand in candidates:
                cn = cand.lower().strip()
                if cn and (cn == name_l or cn in name_l or name_l in cn):
                    return sid, name

        # 2) Fallback to word-based overlap (excluding generic suffixes)
        for state in states:
            if not isinstance(state, dict):
                continue
            name = (
                state.get("state_name")
                or state.get("name")
                or state.get("State")
                or ""
            ).strip()
            if not name:
                continue
            sid = state.get("state_id") or state.get("id") or state.get("stateId")
            name_l = name.lower()
            for cand in candidates:
                cn = cand.lower().strip()
                if not cn:
                    continue
                words = [w for w in cn.split() if len(w) > 3 and w not in ("pradesh", "bengal")]
                if words and any(w in name_l for w in words):
                    return sid, name
        return None, None

    def _resolve_commodity_id(self, crop: str, filters: Dict[str, Any]) -> Optional[Any]:
        commodities = self._list_from_filters(
            filters, "cmdt_data", "commodity_data", "commodity", "commodities", "commodity_list", "commodityadminlist"
        )
        crop_l = crop.lower().strip()
        for item in commodities:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("cmdt_name")
                or item.get("commodity_name")
                or item.get("name")
                or item.get("Commodity")
                or ""
            ).lower()
            if crop_l in name or name in crop_l:
                return item.get("commodity_id") or item.get("id") or item.get("cmdt_id")
        return None

    def _resolve_market(
        self, mandi: str, state_id: Any, filters: Dict[str, Any]
    ) -> Optional[Tuple[Any, Optional[Any]]]:
        markets = self._list_from_filters(filters, "market_data", "market", "markets", "market_list")
        mandi_l = mandi.lower().strip()
        mandi_core = self._market_core_name(mandi_l)
        qualified_matches: List[Tuple[Any, Optional[Any]]] = []
        for item in markets:
            if not isinstance(item, dict):
                continue
            if str(item.get("state_id", "")) != str(state_id):
                continue
            name = (
                item.get("mkt_name")
                or item.get("market_name")
                or item.get("name")
                or item.get("Market")
                or ""
            ).lower()
            name_core = self._market_core_name(name)
            if (
                mandi_l in name
                or name in mandi_l
                or (mandi_core and mandi_core == name_core)
            ):
                market_id = item.get("market_id") or item.get("id")
                district_id = item.get("district_id") or item.get("districtId")
                return market_id, district_id
            if mandi_core and name_core.startswith(f"{mandi_core} "):
                qualified_matches.append((
                    item.get("market_id") or item.get("id"),
                    item.get("district_id") or item.get("districtId"),
                ))
        if len(qualified_matches) == 1:
            return qualified_matches[0]
        return None

    @staticmethod
    def _market_core_name(value: str) -> str:
        suffixes = {"mandi", "market", "apmc", "committee", "yard"}
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
        return " ".join(
            token for token in normalized.split()
            if token not in suffixes
        ).strip()

    @staticmethod
    def _list_from_filters(filters: Dict[str, Any], *keys: str) -> List[Any]:
        for key in keys:
            val = filters.get(key)
            if isinstance(val, list):
                return val
        return []

    @staticmethod
    def _extract_records(report: Any) -> List[Dict[str, Any]]:
        if isinstance(report, list):
            return [r for r in report if isinstance(r, dict)]
        if not isinstance(report, dict):
            return []

        if report.get("status") is False:
            return []

        for key in ("data", "records", "rows", "report", "report_data", "result"):
            val = report.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
            if isinstance(val, dict):
                for inner in ("records", "rows", "data", "items"):
                    inner_val = val.get(inner)
                    if isinstance(inner_val, list):
                        return [r for r in inner_val if isinstance(r, dict)]
        return []

    @staticmethod
    def _pick_price(record: Dict[str, Any], *keys: str) -> Optional[float]:
        for key in keys:
            val = record.get(key)
            if val is None or val == "":
                continue
            try:
                return float(str(val).replace(",", "").strip())
            except (ValueError, TypeError):
                continue
        return None

    def _normalize_records(
        self,
        records: List[Dict[str, Any]],
        location: str,
        state: str,
        mandi: Optional[str],
    ) -> List[Dict[str, Any]]:
        from .unified_realtime_service import CROP_HINDI
        from .msp_data import get_current_msp

        crops: List[Dict[str, Any]] = []
        for rec in records:
            crop_name = (
                rec.get("cmdt_name")
                or rec.get("commodity_name")
                or rec.get("Commodity")
                or rec.get("commodity")
                or rec.get("crop")
                or ""
            )
            if not crop_name:
                continue

            modal = self._pick_price(
                rec,
                "as_on",
                "as_on_price",
                "modal_price",
                "Modal Price",
                "Modal_x0020_Price",
                "modal",
                "price",
            )
            if modal is None or modal <= 0:
                continue

            min_p = self._pick_price(
                rec, "min_price", "Min Price", "Min_x0020_Price", "min"
            )
            max_p = self._pick_price(
                rec, "max_price", "Max Price", "Max_x0020_Price", "max"
            )
            crop_key = str(crop_name).lower().strip()
            # The dashboard can retain an older MSP column. Compare market
            # prices only with the current official table.
            msp = get_current_msp(crop_key) or get_current_msp(str(crop_name))
            profit = round(((modal - msp) / msp * 100), 1) if msp else None

            crops.append({
                "crop_name": str(crop_name).title(),
                "crop_name_hindi": CROP_HINDI.get(crop_key, crop_name),
                "price_source": "agmarknet_market_live" if mandi else "agmarknet_state_average",
                "is_live": True,
                "mandi_name": (
                    rec.get("market_name")
                    or rec.get("Market")
                    or rec.get("market")
                    or mandi
                    or f"{state} Agmarknet average"
                ),
                "state": rec.get("state_name") or rec.get("State") or state,
                "min_price": round(min_p, 2) if min_p is not None else None,
                "max_price": round(max_p, 2) if max_p is not None else None,
                "modal_price": round(modal, 2),
                "msp": msp,
                "profit_vs_msp": profit,
                "profit_indicator": "📈" if profit and profit > 0 else "📉",
                "variety": rec.get("variety_name") or rec.get("Variety") or "",
                "grade": rec.get("grade") or rec.get("Grade") or "",
                "district": rec.get("district_name") or rec.get("District") or "",
                "arrival_quantity": self._pick_price(rec, "cumm_arr", "arrival", "Arrival"),
                "date": (
                    rec.get("reported_date")
                    or rec.get("arrival_date")
                    or rec.get("Arrival_Date")
                    or rec.get("date")
                    or date.today().strftime("%d/%m/%Y")
                ),
                "reported_date": (
                    rec.get("reported_date")
                    or rec.get("arrival_date")
                    or rec.get("Arrival_Date")
                    or rec.get("date")
                    or ""
                ),
                "unit": "₹/quintal",
            })
        return crops


agmarknet_client = AgmarknetClient()
