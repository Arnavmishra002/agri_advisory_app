#!/usr/bin/env python3
"""
Unified Indian location resolution for all KrishiMitra services.

Priority (Uber/Rapido-style):
  1. GPS coordinates + accuracy (≤10 m → building-level reverse geocode)
  2. Text search (village / town / city / society name)
  3. IP geolocation (coarse)
  4. Default (Delhi) — clearly labeled

All realtime services (weather, mandi, crop, pest, chatbot) should use
``location_resolver.resolve()`` or ``LocationContext`` from API helpers.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..rate_limiters import nominatim_limiter, rate_limit

# Global lock — ensures only one Nominatim reverse call runs at a time,
# eliminating "Rate limit exceeded" errors when multiple services fire
# simultaneously on page load (weather + market + crop + field advisory).
_nominatim_lock = threading.Lock()

# In-process cache: (lat_rounded, lon_rounded) -> LocationContext
# Prevents duplicate Nominatim calls for the same GPS coordinates.
_reverse_cache: Dict[tuple, Any] = {}

logger = logging.getLogger(__name__)

# India bounding box (approximate)
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.5, 37.1
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 97.5

DEFAULT_LAT, DEFAULT_LON = 28.6139, 77.2090

# Fast lookup for major cities (avoids IP fallback when Nominatim is rate-limited)
KNOWN_INDIAN_PLACES: Dict[str, Dict[str, Any]] = {
    "delhi": {"lat": 28.7041, "lon": 77.1025, "city": "Delhi", "state": "Delhi", "region": "North"},
    "new delhi": {"lat": 28.6139, "lon": 77.2090, "city": "New Delhi", "state": "Delhi", "region": "North"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "city": "Mumbai", "state": "Maharashtra", "region": "West"},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "city": "Bangalore", "state": "Karnataka", "region": "South"},
    "bengaluru": {"lat": 12.9716, "lon": 77.5946, "city": "Bengaluru", "state": "Karnataka", "region": "South"},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867, "city": "Hyderabad", "state": "Telangana", "region": "South"},
    "chennai": {"lat": 13.0827, "lon": 80.2707, "city": "Chennai", "state": "Tamil Nadu", "region": "South"},
    "kolkata": {"lat": 22.5726, "lon": 88.3639, "city": "Kolkata", "state": "West Bengal", "region": "East"},
    "pune": {"lat": 18.5204, "lon": 73.8567, "city": "Pune", "state": "Maharashtra", "region": "West"},
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714, "city": "Ahmedabad", "state": "Gujarat", "region": "West"},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "city": "Jaipur", "state": "Rajasthan", "region": "North"},
    "lucknow": {"lat": 26.8467, "lon": 80.9462, "city": "Lucknow", "state": "Uttar Pradesh", "region": "North"},
    "chandigarh": {"lat": 30.7333, "lon": 76.7794, "city": "Chandigarh", "state": "Chandigarh", "region": "North"},
    "indore": {"lat": 22.7196, "lon": 75.8577, "city": "Indore", "state": "Madhya Pradesh", "region": "Central"},
    "bhopal": {"lat": 23.2599, "lon": 77.4126, "city": "Bhopal", "state": "Madhya Pradesh", "region": "Central"},
    "patna": {"lat": 25.5941, "lon": 85.1376, "city": "Patna", "state": "Bihar", "region": "East"},
    "nagpur": {"lat": 21.1458, "lon": 79.0882, "city": "Nagpur", "state": "Maharashtra", "region": "Central"},
    "noida": {"lat": 28.5355, "lon": 77.3910, "city": "Noida", "state": "Uttar Pradesh", "region": "North"},
    "gurgaon": {"lat": 28.4595, "lon": 77.0266, "city": "Gurgaon", "state": "Haryana", "region": "North"},
    "gurugram": {"lat": 28.4595, "lon": 77.0266, "city": "Gurugram", "state": "Haryana", "region": "North"},
    "ludhiana": {"lat": 30.9010, "lon": 75.8573, "city": "Ludhiana", "state": "Punjab", "region": "North"},
    "amritsar": {"lat": 31.6340, "lon": 74.8723, "city": "Amritsar", "state": "Punjab", "region": "North"},
}

NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
BIGDATACLOUD_REVERSE = "https://api.bigdatacloud.net/data/reverse-geocode-client"

# Nominatim zoom: 18 ≈ building, 16 ≈ street, 14 ≈ village, 10 ≈ city
def _zoom_for_accuracy(accuracy_meters: Optional[float]) -> int:
    if accuracy_meters is None:
        return 17  # assume phone GPS
    if accuracy_meters <= 10:
        return 18
    if accuracy_meters <= 50:
        return 17
    if accuracy_meters <= 200:
        return 16
    if accuracy_meters <= 1000:
        return 14
    if accuracy_meters <= 5000:
        return 12
    return 10


def _in_india(lat: float, lon: float) -> bool:
    return (
        INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX
        and INDIA_LON_MIN <= lon <= INDIA_LON_MAX
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class LocationContext:
    """Resolved location used by every advisory service."""

    latitude: float
    longitude: float
    display_name: str
    city: str = ""
    village: str = ""
    locality: str = ""
    sublocality: str = ""
    district: str = ""
    state: str = ""
    pincode: str = ""
    region: str = ""
    country: str = "India"
    location_type: str = "unknown"
    accuracy_meters: Optional[float] = None
    accuracy_label: str = "medium"
    source: str = "default"
    confidence: float = 0.5
    is_gps: bool = False
    full_address: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def query_label(self) -> str:
        """Best string for data.gov.in / government APIs (state-aware)."""
        return self.display_name

    @property
    def coords(self) -> Tuple[float, float]:
        return self.latitude, self.longitude


class LocationResolver:
    """Resolve GPS, text, or IP into a single LocationContext."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "KrishiMitra-AI/3.0 (agricultural-advisory; contact@krishimitra.in)",
            "Accept": "application/json",
        })

    def resolve(
        self,
        *,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_query: Optional[str] = None,
        accuracy_meters: Optional[float] = None,
        use_ip_fallback: bool = True,
    ) -> LocationContext:
        if latitude is not None and longitude is not None:
            try:
                lat, lon = float(latitude), float(longitude)
                if _in_india(lat, lon):
                    ctx = self._resolve_gps(lat, lon, accuracy_meters)
                    if ctx:
                        return ctx
                else:
                    logger.warning("Coordinates outside India: %s, %s", lat, lon)
            except (TypeError, ValueError):
                pass

        query = (location_query or "").strip()
        if query and query.lower() not in ("", "detected location", "unknown"):
            ctx = self._resolve_known_place(query)
            if ctx:
                return ctx
            ctx = self._resolve_text(query)
            if ctx:
                return ctx
            ctx = self._resolve_known_place(query, fuzzy=True)
            if ctx:
                return ctx
            # User typed a place — do not replace with IP geolocation
            return self._text_fallback_context(query)

        if use_ip_fallback:
            ctx = self._resolve_ip()
            if ctx:
                return ctx

        return self._default_context()

    def search(self, query: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Forward geocode — cities, towns, villages, societies across India."""
        query = query.strip()
        if len(query) < 2:
            return []

        results: List[Dict[str, Any]] = []
        seen = set()

        for item in self._nominatim_search(query, limit=limit):
            key = (round(item["lat"], 5), round(item["lon"], 5), item["name"].lower())
            if key in seen:
                continue
            seen.add(key)
            results.append(item)

        if not results:
            ctx = self._resolve_known_place(query, fuzzy=True)
            if ctx:
                results.append({
                    "name": ctx.display_name,
                    "city": ctx.city,
                    "village": ctx.village or "",
                    "state": ctx.state,
                    "district": ctx.district or "",
                    "region": ctx.region or _region_from_state(ctx.state),
                    "type": "city",
                    "lat": ctx.latitude,
                    "lon": ctx.longitude,
                    "full_address": f"{ctx.display_name}, {ctx.state}, India",
                    "importance": 0.9,
                    "source": "known_city_catalog",
                })

        return results[:limit]

    def _resolve_gps(
        self, lat: float, lon: float, accuracy_meters: Optional[float]
    ) -> Optional[LocationContext]:
        # Merge BigDataCloud + Nominatim for village/society/locality (Swiggy-style labels)
        bdc = self._reverse_bigdatacloud(lat, lon, accuracy_meters)
        nom = self._reverse_nominatim(lat, lon, accuracy_meters)
        if bdc and nom:
            return self._merge_reverse_results(bdc, nom, accuracy_meters)
        if bdc:
            return bdc
        if nom:
            return nom

        return LocationContext(
            latitude=lat,
            longitude=lon,
            display_name=f"{lat:.4f}, {lon:.4f}",
            accuracy_meters=accuracy_meters,
            accuracy_label=_accuracy_label(accuracy_meters),
            source="gps_coordinates_only",
            confidence=0.6,
            is_gps=True,
            location_type="coordinates",
        )

    @staticmethod
    def _merge_reverse_results(
        bdc: LocationContext,
        nom: LocationContext,
        accuracy_meters: Optional[float],
    ) -> LocationContext:
        """Prefer finest-grained name from either provider (society > village > town)."""
        sublocality = nom.sublocality or bdc.sublocality or ""
        village = nom.village or bdc.village or ""
        locality = nom.locality or bdc.locality or ""
        city = nom.city or bdc.city or ""
        district = nom.district or bdc.district or ""
        state = nom.state or bdc.state or ""
        display = _pick_display_name(
            sublocality=sublocality,
            locality=locality,
            village=village,
            city=city,
            district=district,
            state=state,
        )
        full_address = nom.full_address or bdc.full_address or display
        zoom = _zoom_for_accuracy(accuracy_meters)
        confidence = max(bdc.confidence, nom.confidence)
        if accuracy_meters is not None and accuracy_meters <= 10:
            confidence = min(0.98, confidence + 0.03)
        return LocationContext(
            latitude=bdc.latitude,
            longitude=bdc.longitude,
            display_name=display,
            city=city,
            village=village,
            locality=locality,
            sublocality=sublocality,
            district=district,
            state=state,
            pincode=nom.pincode or bdc.pincode,
            region=nom.region or bdc.region,
            country="India",
            location_type=_infer_type(village, city, district),
            accuracy_meters=accuracy_meters,
            accuracy_label=_accuracy_label(accuracy_meters),
            source=f"gps_merged({bdc.source}+{nom.source})",
            confidence=confidence,
            is_gps=True,
            full_address=full_address,
        )

    def _reverse_bigdatacloud(
        self, lat: float, lon: float, accuracy_meters: Optional[float]
    ) -> Optional[LocationContext]:
        try:
            resp = self.session.get(
                BIGDATACLOUD_REVERSE,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "localityLanguage": "en",
                },
                timeout=(3, 12),
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("countryCode") != "IN":
                return None

            locality = data.get("locality") or ""
            city = data.get("city") or data.get("locality") or ""
            state = data.get("principalSubdivision") or ""
            district = ""
            sublocality = ""
            info = data.get("localityInfo") or {}
            for layer in info.get("administrative", []):
                order = layer.get("order", 99)
                name = layer.get("name", "")
                if order in (8, 9, 10) and not sublocality:
                    sublocality = name
                if order == 4 and not district:
                    district = name
                if order == 5 and not district:
                    district = name

            village = locality if locality and locality != city else ""
            display = _pick_display_name(
                sublocality="",
                locality=locality,
                village=village,
                city=city,
                district=district,
                state=state,
            )

            return LocationContext(
                latitude=lat,
                longitude=lon,
                display_name=display,
                city=city,
                village=village,
                locality=locality,
                sublocality=sublocality,
                district=district,
                state=state,
                pincode=data.get("postcode") or "",
                region=_region_from_state(state),
                country="India",
                location_type=_infer_type(village, city, district),
                accuracy_meters=accuracy_meters,
                accuracy_label=_accuracy_label(accuracy_meters),
                source="bigdatacloud_reverse",
                confidence=0.94 if (accuracy_meters or 100) <= 10 else (
                    0.92 if (accuracy_meters or 100) <= 50 else 0.85
                ),
                is_gps=True,
                full_address=data.get("locality", display),
            )
        except requests.RequestException as exc:
            logger.debug("BigDataCloud reverse failed: %s", exc)
        return None

    def _reverse_nominatim(
        self, lat: float, lon: float, accuracy_meters: Optional[float]
    ) -> Optional["LocationContext"]:
        """Thread-safe, cached Nominatim reverse geocode.

        Uses a global lock so concurrent requests from multiple services
        (weather, market, crop, field-advisory) on page load never fire
        Nominatim simultaneously — which caused 'Rate limit exceeded' HTTP 500.
        Results are cached in-process by rounded coordinates.
        """
        # Round to ~100 m grid for cache key
        cache_key = (round(lat, 3), round(lon, 3))
        cached = _reverse_cache.get(cache_key)
        if cached is not None:
            return cached

        with _nominatim_lock:
            # Double-check inside lock (another thread may have filled it)
            cached = _reverse_cache.get(cache_key)
            if cached is not None:
                return cached

            # Honour Nominatim 1 req/sec policy
            if not nominatim_limiter.is_allowed("_reverse_nominatim"):
                wait = nominatim_limiter.wait_time("_reverse_nominatim")
                logger.debug("Nominatim rate limit — sleeping %.2fs", wait)
                time.sleep(max(wait, 0.05))

            try:
                zoom = _zoom_for_accuracy(accuracy_meters)
                resp = self.session.get(
                    NOMINATIM_REVERSE,
                    params={
                        "lat": lat,
                        "lon": lon,
                        "format": "json",
                        "addressdetails": 1,
                        "zoom": zoom,
                    },
                    timeout=(3, 15),
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                address = data.get("address") or {}
                if address.get("country_code", "").lower() not in ("in", "ind"):
                    return None

                parsed = _parse_osm_address(address, data.get("display_name", ""))
                display = _pick_display_name(**parsed)

                result = LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=display,
                    city=parsed["city"],
                    village=parsed["village"],
                    locality=parsed["locality"],
                    sublocality=parsed["sublocality"],
                    district=parsed["district"],
                    state=parsed["state"],
                    pincode=parsed["pincode"],
                    region=_region_from_state(parsed["state"]),
                    country="India",
                    location_type=_infer_type(
                        parsed["village"], parsed["city"], parsed["district"]
                    ),
                    accuracy_meters=accuracy_meters,
                    accuracy_label=_accuracy_label(accuracy_meters),
                    source="nominatim_reverse",
                    confidence=0.9 if zoom >= 17 else 0.8,
                    is_gps=True,
                    full_address=data.get("display_name", display),
                )
                # Cache for the lifetime of this worker process
                _reverse_cache[cache_key] = result
                return result

            except requests.RequestException as exc:
                logger.debug("Nominatim reverse failed: %s", exc)
            return None

    def _resolve_known_place(self, query: str, fuzzy: bool = False) -> Optional[LocationContext]:
        """Resolve major Indian cities without external geocoding."""
        key = query.strip().lower()
        entry = KNOWN_INDIAN_PLACES.get(key)
        if not entry and fuzzy:
            for name, data in KNOWN_INDIAN_PLACES.items():
                if name in key or key in name:
                    entry = data
                    key = name
                    break
        if not entry:
            return None
        city = entry["city"]
        return LocationContext(
            latitude=entry["lat"],
            longitude=entry["lon"],
            display_name=city,
            city=city,
            state=entry["state"],
            region=entry.get("region", ""),
            country="India",
            location_type="city",
            accuracy_meters=500,
            accuracy_label="medium",
            source="known_city_catalog",
            confidence=0.82,
            is_gps=False,
        )

    def _text_fallback_context(self, query: str) -> LocationContext:
        """Last resort when geocoders fail but user provided a place name."""
        return LocationContext(
            latitude=DEFAULT_LAT,
            longitude=DEFAULT_LON,
            display_name=query.strip(),
            city=query.strip(),
            source="text_query_ungeocoded",
            confidence=0.45,
            accuracy_label="low",
            is_gps=False,
        )

    def _resolve_text(self, query: str) -> Optional[LocationContext]:
        hits = self._nominatim_search(query, limit=1)
        if not hits:
            return None
        hit = hits[0]
        lat, lon = hit["lat"], hit["lon"]
        ctx = self._resolve_gps(lat, lon, accuracy_meters=500)
        if ctx:
            ctx.source = "text_geocode+" + ctx.source
            ctx.confidence = min(ctx.confidence, 0.88)
            ctx.is_gps = False
            if hit.get("name"):
                ctx.display_name = hit["name"]
            return ctx

        return LocationContext(
            latitude=lat,
            longitude=lon,
            display_name=hit["name"],
            city=hit.get("city", ""),
            state=hit.get("state", ""),
            district=hit.get("district", ""),
            region=hit.get("region", ""),
            source="nominatim_search",
            confidence=0.75,
            location_type=hit.get("type", "place"),
            full_address=hit.get("full_address", ""),
        )

    @rate_limit(nominatim_limiter)
    def _nominatim_search(self, query: str, limit: int = 12) -> List[Dict[str, Any]]:
        try:
            resp = self.session.get(
                NOMINATIM_SEARCH,
                params={
                    "q": f"{query}, India",
                    "format": "json",
                    "limit": limit,
                    "countrycodes": "in",
                    "addressdetails": 1,
                },
                timeout=(3, 15),
            )
            if resp.status_code != 200:
                return []
            out = []
            for row in resp.json():
                address = row.get("address") or {}
                parsed = _parse_osm_address(address, row.get("display_name", ""))
                name = _pick_display_name(**parsed)
                out.append({
                    "name": name,
                    "city": parsed["city"],
                    "village": parsed["village"],
                    "state": parsed["state"],
                    "district": parsed["district"],
                    "region": _region_from_state(parsed["state"]),
                    "type": _infer_type(
                        parsed["village"], parsed["city"], parsed["district"]
                    ),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "full_address": row.get("display_name", name),
                    "importance": row.get("importance", 0),
                })
            out.sort(key=lambda x: x.get("importance", 0), reverse=True)
            return out
        except requests.RequestException as exc:
            logger.warning("Nominatim search failed: %s", exc)
            return []

    def _resolve_ip(self) -> Optional[LocationContext]:
        try:
            # FIX: Use HTTPS to prevent MITM spoofing of user location
            resp = self.session.get("https://ip-api.com/json/", timeout=5)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != "success" or data.get("country") != "India":
                return None
            lat, lon = float(data["lat"]), float(data["lon"])
            ctx = self._resolve_gps(lat, lon, accuracy_meters=5000)
            if ctx:
                ctx.source = "ip_geolocation+" + ctx.source
                ctx.accuracy_meters = 5000
                ctx.accuracy_label = "low"
                ctx.confidence = 0.55
                ctx.is_gps = False
                return ctx
        except requests.RequestException:
            pass
        return None

    def _default_context(self) -> LocationContext:
        return LocationContext(
            latitude=DEFAULT_LAT,
            longitude=DEFAULT_LON,
            display_name="Delhi",
            city="Delhi",
            state="Delhi",
            region="North",
            source="default_fallback",
            confidence=0.3,
            accuracy_label="low",
        )


def _parse_osm_address(address: dict, display_name: str) -> Dict[str, str]:
    sublocality = (
        address.get("neighbourhood")
        or address.get("suburb")
        or address.get("quarter")
        or address.get("residential")
        or address.get("hamlet")
        or ""
    )
    village = (
        address.get("village")
        or address.get("hamlet")
        or address.get("locality")
        or ""
    )
    city = (
        address.get("city")
        or address.get("town")
        or address.get("municipality")
        or address.get("county")
        or ""
    )
    district = (
        address.get("state_district")
        or address.get("district")
        or address.get("county")
        or ""
    )
    state = address.get("state") or address.get("province") or ""
    pincode = address.get("postcode") or ""
    locality = address.get("locality") or village or sublocality or ""

    if not city and village:
        city = village

    return {
        "sublocality": sublocality,
        "locality": locality,
        "village": village,
        "city": city,
        "district": district,
        "state": state,
        "pincode": pincode,
        "display_name": display_name,
    }


def _pick_display_name(
    *,
    sublocality: str = "",
    locality: str = "",
    village: str = "",
    city: str = "",
    district: str = "",
    state: str = "",
    **_,
) -> str:
    """Prefer society/block → village → town → district (Rapido-style label)."""
    for part in (sublocality, locality, village, city, district, state):
        if part and str(part).strip():
            return str(part).strip()
    return "India"


def _infer_type(village: str, city: str, district: str) -> str:
    if village:
        return "village"
    if city:
        return "city"
    if district:
        return "district"
    return "place"


def _accuracy_label(accuracy_meters: Optional[float]) -> str:
    if accuracy_meters is None:
        return "high"
    if accuracy_meters <= 10:
        return "gps_10m"
    if accuracy_meters <= 50:
        return "high"
    if accuracy_meters <= 500:
        return "medium"
    return "low"


def _region_from_state(state: str) -> str:
    s = (state or "").lower()
    if any(k in s for k in ("delhi", "punjab", "haryana", "rajasthan", "himachal", "uttarakhand", "jammu", "kashmir", "ladakh")):
        return "North"
    if any(k in s for k in ("maharashtra", "gujarat", "goa")):
        return "West"
    if any(k in s for k in ("karnataka", "tamil", "kerala", "andhra", "telangana")):
        return "South"
    if any(k in s for k in ("bengal", "odisha", "bihar", "jharkhand", "assam", "tripura", "manipur", "meghalaya", "mizoram", "nagaland", "sikkim", "arunachal")):
        return "East"
    if any(k in s for k in ("madhya", "chhattisgarh", "uttar pradesh")):
        return "Central"
    return "Unknown"


# Singleton used across services
location_resolver = LocationResolver()


@lru_cache(maxsize=256)
def resolve_location_cached(
    lat: Optional[float],
    lon: Optional[float],
    query: Optional[str],
    accuracy_rounded: Optional[int],
) -> LocationContext:
    """Cached resolve — accuracy rounded to 10 m buckets for cache keys."""
    return location_resolver.resolve(
        latitude=lat,
        longitude=lon,
        location_query=query,
        accuracy_meters=float(accuracy_rounded) if accuracy_rounded is not None else None,
    )
