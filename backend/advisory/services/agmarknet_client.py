"""
Official Agmarknet 2.0 REST API (api.agmarknet.gov.in/v1).

Used for live mandi modal/min/max prices when data.gov.in is slow or unavailable.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

AGMARKNET_BASE = "https://api.agmarknet.gov.in/v1"
DEFAULT_TIMEOUT = (5, 30)  # connect, read seconds

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
            "User-Agent": "KrishiMitra-AI/3.0 (Agricultural Advisory; +https://krishimitra.in)",
            "Accept": "application/json",
            "Content-Type": "application/json",
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
            filters, "market", "markets", "market_list", "apmc_list"
        )
        out: List[Dict[str, Any]] = []
        seen = set()
        for item in markets_raw:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("market_name")
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
                "live": True,
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

        base_payload: Dict[str, Any] = {"state_id": state_id}
        if crop:
            commodity_id = self._resolve_commodity_id(crop, filters)
            if commodity_id:
                base_payload["commodity_id"] = commodity_id
        if mandi:
            market_id = self._resolve_market_id(mandi, state_id, filters)
            if market_id:
                base_payload["market_id"] = market_id

        records: List[Dict[str, Any]] = []
        for day_offset in range(4):
            day = (date.today() - timedelta(days=day_offset)).isoformat()
            payload = {**base_payload, "from_date": day, "to_date": day}
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
            "timestamp": datetime.now().isoformat(),
            "top_crops": crops[:20],
            "total_records": len(crops),
            "message": f"{len(crops)} live mandi records from Agmarknet",
        }

    def _get_filters(self) -> Optional[Dict[str, Any]]:
        now = datetime.now()
        if self._filters_cache and self._filters_cache_at:
            if now - self._filters_cache_at < self._filters_ttl:
                return self._filters_cache

        try:
            resp = self.session.get(
                f"{AGMARKNET_BASE}/daily-price-arrival/filters",
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
        url = f"{AGMARKNET_BASE}/daily-price-arrival/report"
        # Portal uses form-encoded query params (not JSON body)
        attempts = (
            {"data": payload, "headers": {"Content-Type": "application/x-www-form-urlencoded"}},
            {"json": payload},
        )
        for kwargs in attempts:
            try:
                resp = self.session.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
                if resp.status_code != 200:
                    continue
                return resp.json()
            except requests.RequestException:
                continue
        logger.warning("Agmarknet report failed for %s", payload)
        return None

    def _resolve_state(
        self, location: str, filters: Dict[str, Any]
    ) -> Tuple[Optional[Any], Optional[str]]:
        states = self._list_from_filters(filters, "state", "states", "state_list", "statelist")
        loc = location.lower().strip()
        candidates: List[str] = [location.strip()]
        for key, aliases in STATE_NAME_ALIASES.items():
            if key in loc:
                candidates.extend(aliases)

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
                if cn == name_l or cn in name_l or name_l in cn:
                    return sid, name
                if any(w in name_l for w in cn.split() if len(w) > 3):
                    return sid, name
        return None, None

    def _resolve_commodity_id(self, crop: str, filters: Dict[str, Any]) -> Optional[Any]:
        commodities = self._list_from_filters(
            filters, "commodity", "commodities", "commodity_list", "commodityadminlist"
        )
        crop_l = crop.lower().strip()
        for item in commodities:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("commodity_name")
                or item.get("name")
                or item.get("Commodity")
                or ""
            ).lower()
            if crop_l in name or name in crop_l:
                return item.get("commodity_id") or item.get("id") or item.get("cmdt_id")
        return None

    def _resolve_market_id(
        self, mandi: str, state_id: Any, filters: Dict[str, Any]
    ) -> Optional[Any]:
        markets = self._list_from_filters(filters, "market", "markets", "market_list")
        mandi_l = mandi.lower().strip()
        for item in markets:
            if not isinstance(item, dict):
                continue
            if str(item.get("state_id", "")) != str(state_id):
                continue
            name = (
                item.get("market_name")
                or item.get("name")
                or item.get("Market")
                or ""
            ).lower()
            if mandi_l in name or name in mandi_l:
                return item.get("market_id") or item.get("id")
        return None

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
        from .unified_realtime_service import CROP_HINDI, MSP_2024_25

        crops: List[Dict[str, Any]] = []
        for rec in records:
            crop_name = (
                rec.get("commodity_name")
                or rec.get("Commodity")
                or rec.get("commodity")
                or rec.get("crop")
                or ""
            )
            if not crop_name:
                continue

            modal = self._pick_price(
                rec,
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
            min_p = min_p if min_p is not None else round(modal * 0.95, 2)
            max_p = max_p if max_p is not None else round(modal * 1.05, 2)

            crop_key = str(crop_name).lower().strip()
            msp = MSP_2024_25.get(crop_key)
            profit = round(((modal - msp) / msp * 100), 1) if msp else None

            crops.append({
                "crop_name": str(crop_name).title(),
                "crop_name_hindi": CROP_HINDI.get(crop_key, crop_name),
                "price_source": "live_mandi",
                "is_live": True,
                "mandi_name": (
                    rec.get("market_name")
                    or rec.get("Market")
                    or rec.get("market")
                    or mandi
                    or f"{location} मंडी"
                ),
                "state": rec.get("state_name") or rec.get("State") or state,
                "min_price": round(min_p, 2),
                "max_price": round(max_p, 2),
                "modal_price": round(modal, 2),
                "msp": msp,
                "profit_vs_msp": profit,
                "profit_indicator": "📈" if profit and profit > 0 else "📉",
                "variety": rec.get("variety_name") or rec.get("Variety") or "",
                "grade": rec.get("grade") or rec.get("Grade") or "",
                "date": (
                    rec.get("arrival_date")
                    or rec.get("Arrival_Date")
                    or rec.get("date")
                    or date.today().strftime("%d/%m/%Y")
                ),
                "unit": "₹/quintal",
            })
        return crops


agmarknet_client = AgmarknetClient()
