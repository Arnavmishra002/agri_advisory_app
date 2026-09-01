"""Resolve a farmer's location onto Agmarknet's own filter IDs.

Agmarknet 2.0 exposes its whole filter space in one call --
``/v1/dashboard-filters/?dashboard_name=marketwise_price_arrival`` -- covering
37 states/UTs, 746 districts, 4,179 markets and 28 commodities. Without those
IDs a price query can only ask for the national "All States" aggregate, which
is what this app did before: a farmer near Noida was shown an all-India average
rather than the figure reported for their own district.

Measured on 2026-09-01 for the same commodity and date:

    all-India aggregate ...... Wheat  (national basket)
    Uttar Pradesh average .... Wheat  2523.70
    Gautam Budh Nagar ........ Wheat  2541.83   <- what the farmer should see

so resolving to a district is worth doing. Individual mandis are sparse (DADRI
APMC returned one row, for Maize, with no price at all), which is why the
caller escalates district -> state -> national rather than insisting on a
single market.

Two name-matching problems make this non-trivial, and both are handled here:

* Agmarknet spells several states its own way -- "Keralam", "Chattisgarh",
  "NCT of Delhi", "Pondicherry". A farmer in Kerala would otherwise never
  match and would silently fall back to the national number.
* District names come from reverse geocoding, so they arrive in the
  geocoder's spelling: Nominatim says "Gautam Buddha Nagar" where Agmarknet
  says "Gautam Budh Nagar". Exact matching fails; normalised + fuzzy matching
  succeeds.

Districts and markets are ~400 KB together, so they are fetched at runtime and
cached rather than committed. The stable half (states, commodities, groups,
grades, varieties) is bundled in ``data/agmarknet_reference.json`` so state
level resolution keeps working even when the upstream call fails.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

FILTERS_URL = "https://api.agmarknet.gov.in/v1/dashboard-filters/"
DASHBOARD = "marketwise_price_arrival"

_CACHE_KEY = "agmarknet:filters:v1"
_CACHE_TTL = 24 * 60 * 60          # the filter space changes very rarely
_HTTP_TIMEOUT = (5, 20)            # connect, read

_REFERENCE_PATH = Path(__file__).resolve().parent.parent / "data" / "agmarknet_reference.json"

# Agmarknet's spelling on the left of each pair is what we must end up matching.
# Everything here is a real divergence from the name a geocoder or a farmer
# would supply, verified against the live filter payload.
_STATE_ALIASES = {
    "kerala": "keralam",
    "chhattisgarh": "chattisgarh",
    "delhi": "nct of delhi",
    "new delhi": "nct of delhi",
    "national capital territory of delhi": "nct of delhi",
    "puducherry": "pondicherry",
    "pondicherry ut": "pondicherry",
    "jammu kashmir": "jammu and kashmir",
    "jammu & kashmir": "jammu and kashmir",
    "andaman nicobar": "andaman and nicobar",
    "andaman & nicobar islands": "andaman and nicobar",
    "dadra & nagar haveli": "dadra and nagar haveli",
    "daman & diu": "daman and diu",
    "orissa": "odisha",
    "uttaranchal": "uttarakhand",
    "pondichery": "pondicherry",
}

# Words that carry no identifying information in a district name.
_DISTRICT_NOISE = re.compile(
    r"\b(district|dist|zila|zilla|division|revenue|rural|urban)\b", re.I
)


def _norm(value: Optional[str]) -> str:
    """Lower-case, strip punctuation and collapse spaces for name matching."""
    if not value:
        return ""
    text = str(value).lower().strip()
    text = text.replace("&", " and ")
    text = _DISTRICT_NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class AgmarknetFilterRegistry:
    """Lazily-loaded, cached view of Agmarknet's filter space."""

    _lock = threading.Lock()

    def __init__(self) -> None:
        self._reference: Optional[Dict[str, Any]] = None

    # ── bundled reference (always available) ──────────────────────────────

    @property
    def reference(self) -> Dict[str, Any]:
        if self._reference is None:
            try:
                self._reference = json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - packaging error
                logger.error("agmarknet reference bundle unreadable: %s", exc)
                self._reference = {"states": [], "commodities": [], "all_ids": {}}
        return self._reference

    @property
    def all_ids(self) -> Dict[str, int]:
        return self.reference.get("all_ids", {})

    # ── live filter payload (districts + markets) ─────────────────────────

    def _fetch(self) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(
                FILTERS_URL, params={"dashboard_name": DASHBOARD}, timeout=_HTTP_TIMEOUT
            )
            resp.raise_for_status()
            data = (resp.json() or {}).get("data") or {}
            if not data.get("district_data") or not data.get("market_data"):
                logger.warning("agmarknet filter payload missing districts/markets")
                return None
            return {
                "states": data.get("state_data", []),
                "districts": data.get("district_data", []),
                "markets": data.get("market_data", []),
                "commodities": data.get("cmdt_data", []),
            }
        except Exception as exc:
            # Never fatal: the caller degrades to state or national coverage.
            logger.warning("agmarknet filter fetch failed: %s", exc)
            return None

    def load(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Return the full filter space, or None when it cannot be obtained."""
        if not force_refresh:
            cached = cache.get(_CACHE_KEY)
            if cached:
                return cached
        with self._lock:
            if not force_refresh:
                cached = cache.get(_CACHE_KEY)
                if cached:
                    return cached
            payload = self._fetch()
            if payload:
                cache.set(_CACHE_KEY, payload, _CACHE_TTL)
            return payload

    # ── resolution ────────────────────────────────────────────────────────

    def resolve_state(self, name: Optional[str]) -> Optional[Tuple[int, str]]:
        """Map a state name onto Agmarknet's state_id, aliases included."""
        target = _norm(name)
        if not target:
            return None
        target = _STATE_ALIASES.get(target, target)
        states = self.reference.get("states", [])
        for sid, sname in states:
            if sid == self.all_ids.get("state"):
                continue                      # skip the "All States/UTs" entry
            if _norm(sname) == target:
                return int(sid), sname
        # Agmarknet's own spelling may still differ from every alias we know.
        lookup = {_norm(s[1]): s for s in states if s[0] != self.all_ids.get("state")}
        close = difflib.get_close_matches(target, list(lookup), n=1, cutoff=0.86)
        if close:
            sid, sname = lookup[close[0]]
            return int(sid), sname
        return None

    def resolve_district(
        self, state_id: int, name: Optional[str]
    ) -> Optional[Tuple[int, str]]:
        """Map a geocoded district name onto Agmarknet's district_id."""
        target = _norm(name)
        if not target or state_id is None:
            return None
        payload = self.load()
        if not payload:
            return None
        in_state = [
            d for d in payload["districts"]
            if d.get("state_id") == state_id and d.get("id") != self.all_ids.get("district")
        ]
        if not in_state:
            return None
        lookup = {_norm(d.get("district_name")): d for d in in_state}
        if target in lookup:
            d = lookup[target]
            return int(d["id"]), d["district_name"]
        # "Gautam Buddha Nagar" (Nominatim) vs "Gautam Budh Nagar" (Agmarknet).
        close = difflib.get_close_matches(target, list(lookup), n=1, cutoff=0.80)
        if close:
            d = lookup[close[0]]
            return int(d["id"]), d["district_name"]
        # Last resort: a containment match catches "Bangalore Rural" vs "Bangalore".
        for key, d in lookup.items():
            if key and (key in target or target in key):
                return int(d["id"]), d["district_name"]
        return None

    def markets_for(
        self, state_id: Optional[int] = None, district_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Real Agmarknet markets, narrowed to a state and/or district."""
        payload = self.load()
        if not payload:
            return []
        all_market = self.all_ids.get("market")
        out = []
        for m in payload["markets"]:
            if m.get("id") == all_market:
                continue
            if state_id is not None and m.get("state_id") != state_id:
                continue
            if district_id is not None and m.get("district_id") != district_id:
                continue
            out.append({
                "market_id": int(m["id"]),
                "market_name": m.get("mkt_name"),
                "district_id": m.get("district_id"),
                "state_id": m.get("state_id"),
            })
        return sorted(out, key=lambda x: (x["market_name"] or "").lower())

    def link_market(
        self, name: Optional[str], state_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Attach an Agmarknet market_id to a mandi from our own registry.

        Our registry carries coordinates (so we can say "2.3 km away");
        Agmarknet carries the market_id needed to ask for a price. Neither
        alone is enough, and the names differ in predictable ways -- we hold
        "Noida", Agmarknet holds "Noida APMC"; we hold "Azadpur", it holds
        "APMC Azadpur". Stripping the APMC/market noise and matching on what
        is left links 20 of the 26 mandis our Delhi-NCR list shows.

        Returns None rather than a guess when nothing matches closely, so an
        unlinked mandi simply falls back to district coverage.
        """
        target = _norm(re.sub(r"\b(apmc|mandi|market|new grain market|main)\b", " ", str(name or ""), flags=re.I))
        if not target:
            return None
        payload = self.load()
        if not payload:
            return None
        all_market = self.all_ids.get("market")
        candidates: Dict[str, Dict[str, Any]] = {}
        for m in payload["markets"]:
            if m.get("id") == all_market:
                continue
            if state_id is not None and m.get("state_id") != state_id:
                continue
            key = _norm(re.sub(r"\b(apmc|mandi|market|new grain market|main)\b", " ",
                               str(m.get("mkt_name") or ""), flags=re.I))
            if key and key not in candidates:
                candidates[key] = m
        m = candidates.get(target)
        if m is None:
            close = difflib.get_close_matches(target, list(candidates), n=1, cutoff=0.88)
            if close:
                m = candidates[close[0]]
        if m is None:
            # Our registry names carry a locality qualifier the official list
            # omits: "Noida Sector 33" against Agmarknet's "Noida APMC". Match
            # on a leading whole-token prefix, which links those without
            # letting "Meerut" grab "Meerut Road" style near-misses: the
            # candidate must be at least two tokens' worth of real name, and
            # must align on a token boundary rather than mid-word.
            target_tokens = target.split()
            best: Optional[Tuple[int, Dict[str, Any]]] = None
            for key, cand in candidates.items():
                key_tokens = key.split()
                if len(key) < 4 or len(key_tokens) > len(target_tokens):
                    continue
                if target_tokens[: len(key_tokens)] != key_tokens:
                    continue
                # Prefer the longest prefix, so "new delhi" beats "new".
                if best is None or len(key_tokens) > best[0]:
                    best = (len(key_tokens), cand)
            if best:
                m = best[1]
        if m is None:
            return None
        return {
            "market_id": int(m["id"]),
            "market_name": m.get("mkt_name"),
            "district_id": m.get("district_id"),
            "state_id": m.get("state_id"),
        }

    def resolve_commodity(self, name: Optional[str]) -> Optional[Tuple[int, str]]:
        """Map a crop name onto Agmarknet's commodity_id.

        Agmarknet labels carry qualifiers a farmer never types -- "Wheat" is
        plain but gram is "Bengal Gram(Gram)(Whole)" -- so match on the leading
        word group as well as the full label.
        """
        target = _norm(name)
        if not target:
            return None
        rows = [c for c in self.reference.get("commodities", [])
                if c[0] != self.all_ids.get("commodity")]
        for cid, cname, *_ in rows:
            if _norm(cname) == target:
                return int(cid), cname
        for cid, cname, *_ in rows:
            head = _norm(str(cname).split("(")[0])
            if head and (head == target or target in head or head in target):
                return int(cid), cname
        lookup = {_norm(str(c[1]).split("(")[0]): c for c in rows}
        close = difflib.get_close_matches(target, list(lookup), n=1, cutoff=0.85)
        if close:
            cid, cname, *_ = lookup[close[0]]
            return int(cid), cname
        return None

    def resolve_location(
        self, state: Optional[str], district: Optional[str] = None
    ) -> Dict[str, Any]:
        """One call for the price client: the tightest scope we can address.

        ``coverage`` says how local the answer will actually be, so the caller
        can label it honestly instead of implying a mandi-exact quote.
        """
        result: Dict[str, Any] = {
            "state_id": None, "state_name": None,
            "district_id": None, "district_name": None,
            "coverage": "national",
        }
        resolved_state = self.resolve_state(state)
        if not resolved_state:
            return result
        result["state_id"], result["state_name"] = resolved_state
        result["coverage"] = "state"
        resolved_district = self.resolve_district(result["state_id"], district)
        if resolved_district:
            result["district_id"], result["district_name"] = resolved_district
            result["coverage"] = "district"
        return result


agmarknet_filters = AgmarknetFilterRegistry()
