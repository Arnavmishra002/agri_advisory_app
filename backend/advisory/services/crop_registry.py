"""
KrishiMitra Crop Registry — Single Source of Truth
====================================================
Replaces the fragmented crop metadata spread across:
  - comprehensive_crop_database.py  (150 crop data dicts)
  - crop_catalog.py                 (search/normalize layer)
  - crop_recommendation_engine.py   (scoring, uses its own profile dicts)
  - unified_realtime_service.py     (MSP dict, CROP_HINDI dict)

All other modules IMPORT from here. No more duplicated MSP values,
Hindi names, or season labels scattered across 4 files.

Architecture:
  CropEntry     — typed dataclass for a single crop
  CropRegistry  — loads once at startup, provides get/search/normalize
  crop_registry — module-level singleton (import this)

Backward-compatible shims exported at the bottom so existing callers
(crop_catalog.crop_catalog, etc.) continue to work without changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Import MSP from the authoritative location ───────────────────────────────
# unified_realtime_service is still the canonical source; CropRegistry reads
# from it so there is exactly ONE dict to update each year.
try:
    from .unified_realtime_service import MSP_2024_25, CROP_HINDI, get_msp
except ImportError:
    MSP_2024_25 = {}
    CROP_HINDI  = {}
    def get_msp(crop_id, fallback=0):
        return MSP_2024_25.get(crop_id, fallback)


@dataclass
class CropEntry:
    """All metadata for a single Indian crop."""
    id:            str
    name:          str                       # canonical English name
    name_hindi:    str       = ""
    aliases:       List[str] = field(default_factory=list)
    category:      str       = "other"       # cereal|pulse|oilseed|vegetable|fruit|spice|fiber|cash
    season:        str       = ""            # rabi|kharif|zaid|year_round
    msp:           int       = 0             # ₹/quintal (0 = no MSP)

    # Extended agronomic profile (populated lazily from comprehensive_crop_database)
    _profile: Optional[Dict[str, Any]] = field(default=None, repr=False, compare=False)

    def profile(self) -> Dict[str, Any]:
        """Lazy-load full agronomic profile from comprehensive_crop_database."""
        if self._profile is not None:
            return self._profile
        try:
            from .comprehensive_crop_database import comprehensive_crop_database
            self._profile = comprehensive_crop_database.get_crop_info(self.id) or {}
        except Exception:
            self._profile = {}
        return self._profile

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":       self.id,
            "name":     self.name,
            "hindi":    self.name_hindi,
            "category": self.category,
            "season":   self.season,
            "msp":      self.msp,
            "has_msp":  self.msp > 0,
            "label":    f"{self.name} ({self.name_hindi})" if self.name_hindi else self.name,
            "search_term": self.name,
            "commodity_filter": self.name,
        }


# ── Raw crop rows (canonical list) ───────────────────────────────────────────
# Source of truth for id, canonical name, aliases, category, season.
# MSP is populated dynamically from MSP_2024_25 / DB.
_RAW_CROPS: List[Dict[str, Any]] = [
    # Cereals
    {"id": "wheat",      "name": "Wheat",       "aliases": ["gehun","gehu","गेहूँ"],                  "cat": "cereal",    "season": "rabi"},
    {"id": "rice",       "name": "Rice",        "aliases": ["paddy","chawal","dhan","धान","चावल"],    "cat": "cereal",    "season": "kharif"},
    {"id": "maize",      "name": "Maize",       "aliases": ["corn","makka","मक्का"],                  "cat": "cereal",    "season": "kharif"},
    {"id": "bajra",      "name": "Bajra",       "aliases": ["pearl millet","बाजरा"],                  "cat": "cereal",    "season": "kharif"},
    {"id": "jowar",      "name": "Jowar",       "aliases": ["sorghum","ज्वार"],                       "cat": "cereal",    "season": "kharif"},
    {"id": "barley",     "name": "Barley",      "aliases": ["jau","जौ"],                              "cat": "cereal",    "season": "rabi"},
    {"id": "ragi",       "name": "Ragi",        "aliases": ["finger millet","रागी"],                  "cat": "cereal",    "season": "kharif"},
    # Oilseeds
    {"id": "soybean",    "name": "Soybean",     "aliases": ["soya","सोयाबीन"],                        "cat": "oilseed",   "season": "kharif"},
    {"id": "mustard",    "name": "Mustard",     "aliases": ["sarson","rapeseed","सरसों"],              "cat": "oilseed",   "season": "rabi"},
    {"id": "groundnut",  "name": "Groundnut",   "aliases": ["peanut","moongfali","मूँगफली"],          "cat": "oilseed",   "season": "kharif"},
    {"id": "sunflower",  "name": "Sunflower",   "aliases": ["सूरजमुखी"],                             "cat": "oilseed",   "season": "rabi"},
    {"id": "sesame",     "name": "Sesame",      "aliases": ["til","तिल"],                             "cat": "oilseed",   "season": "kharif"},
    # Fiber / Cash
    {"id": "cotton",     "name": "Cotton",      "aliases": ["kapas","कपास"],                         "cat": "fiber",     "season": "kharif"},
    {"id": "sugarcane",  "name": "Sugarcane",   "aliases": ["ganna","गन्ना"],                        "cat": "cash",      "season": "year_round"},
    {"id": "jute",       "name": "Jute",        "aliases": ["पटसन"],                                 "cat": "fiber",     "season": "kharif"},
    # Pulses
    {"id": "gram",       "name": "Gram",        "aliases": ["chickpea","chana","चना"],                "cat": "pulse",     "season": "rabi"},
    {"id": "lentil",     "name": "Lentil",      "aliases": ["masoor","dal","मसूर"],                   "cat": "pulse",     "season": "rabi"},
    {"id": "moong",      "name": "Moong",       "aliases": ["green gram","mung","मूँग"],              "cat": "pulse",     "season": "kharif"},
    {"id": "urad",       "name": "Urad",        "aliases": ["black gram","उड़द"],                     "cat": "pulse",     "season": "kharif"},
    {"id": "arhar",      "name": "Arhar",       "aliases": ["tur","pigeon pea","toor","अरहर"],        "cat": "pulse",     "season": "kharif"},
    # Vegetables
    {"id": "tomato",     "name": "Tomato",      "aliases": ["tamatar","टमाटर"],                       "cat": "vegetable", "season": "zaid"},
    {"id": "potato",     "name": "Potato",      "aliases": ["aloo","आलू"],                            "cat": "vegetable", "season": "rabi"},
    {"id": "onion",      "name": "Onion",       "aliases": ["pyaz","प्याज"],                          "cat": "vegetable", "season": "rabi"},
    {"id": "garlic",     "name": "Garlic",      "aliases": ["lahsun","लहसुन"],                        "cat": "vegetable", "season": "rabi"},
    {"id": "chilli",     "name": "Chilli",      "aliases": ["chili","mirch","मिर्च"],                 "cat": "vegetable", "season": "kharif"},
    {"id": "brinjal",    "name": "Brinjal",     "aliases": ["eggplant","baingan","बैंगन"],            "cat": "vegetable", "season": "kharif"},
    {"id": "okra",       "name": "Okra",        "aliases": ["ladyfinger","bhindi","भिंडी"],           "cat": "vegetable", "season": "kharif"},
    {"id": "cauliflower","name": "Cauliflower", "aliases": ["gobi","phool gobhi","फूल गोभी"],         "cat": "vegetable", "season": "rabi"},
    {"id": "cabbage",    "name": "Cabbage",     "aliases": ["patta gobhi","पत्ता गोभी"],              "cat": "vegetable", "season": "rabi"},
    {"id": "capsicum",   "name": "Capsicum",    "aliases": ["shimla mirch","bell pepper","शिमला मिर्च"],"cat": "vegetable","season": "rabi"},
    {"id": "cucumber",   "name": "Cucumber",    "aliases": ["kheera","खीरा"],                         "cat": "vegetable", "season": "zaid"},
    {"id": "pumpkin",    "name": "Pumpkin",     "aliases": ["kaddu","कद्दू"],                         "cat": "vegetable", "season": "kharif"},
    {"id": "spinach",    "name": "Spinach",     "aliases": ["palak","पालक"],                          "cat": "vegetable", "season": "rabi"},
    {"id": "carrot",     "name": "Carrot",      "aliases": ["gajar","गाजर"],                          "cat": "vegetable", "season": "rabi"},
    # Fruits
    {"id": "mango",      "name": "Mango",       "aliases": ["aam","आम"],                              "cat": "fruit",     "season": "zaid"},
    {"id": "banana",     "name": "Banana",      "aliases": ["kela","केला"],                           "cat": "fruit",     "season": "year_round"},
    {"id": "pomegranate","name": "Pomegranate", "aliases": ["anar","अनार"],                           "cat": "fruit",     "season": "year_round"},
    {"id": "papaya",     "name": "Papaya",      "aliases": ["papita","पपीता"],                        "cat": "fruit",     "season": "year_round"},
    {"id": "guava",      "name": "Guava",       "aliases": ["amrood","अमरूद"],                        "cat": "fruit",     "season": "year_round"},
    # Spices
    {"id": "turmeric",   "name": "Turmeric",    "aliases": ["haldi","हल्दी"],                         "cat": "spice",     "season": "kharif"},
    {"id": "ginger",     "name": "Ginger",      "aliases": ["adrak","अदरक"],                          "cat": "spice",     "season": "kharif"},
    {"id": "coriander",  "name": "Coriander",   "aliases": ["dhaniya","धनिया"],                       "cat": "spice",     "season": "rabi"},
    {"id": "cumin",      "name": "Cumin",       "aliases": ["jeera","जीरा"],                          "cat": "spice",     "season": "rabi"},
    {"id": "fenugreek",  "name": "Fenugreek",   "aliases": ["methi","मेथी"],                          "cat": "spice",     "season": "rabi"},
]


def _tokenise(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z\u0900-\u097F]+", text.lower())


class CropRegistry:
    """
    Single canonical source for all crop metadata.
    Loaded once at startup, O(1) lookup by id or alias.
    """

    def __init__(self):
        self._by_id:    Dict[str, CropEntry] = {}
        self._by_token: Dict[str, str]       = {}   # token → crop_id
        self._popular_ids = [
            "wheat","rice","maize","mustard","tomato","onion","potato",
            "cotton","soybean","groundnut","gram","arhar","sugarcane",
        ]
        self._build()

    def _build(self) -> None:
        for row in _RAW_CROPS:
            crop_id   = row["id"]
            hindi     = CROP_HINDI.get(crop_id, "")
            msp_value = get_msp(crop_id, fallback=MSP_2024_25.get(crop_id, 0))

            entry = CropEntry(
                id=crop_id,
                name=row["name"],
                name_hindi=hindi,
                aliases=row.get("aliases", []),
                category=row["cat"],
                season=row.get("season", ""),
                msp=msp_value,
            )
            self._by_id[crop_id] = entry

            # Index all tokens: id, name, hindi, aliases
            for text in [crop_id, row["name"], hindi] + row.get("aliases", []):
                for tok in _tokenise(text):
                    if tok and tok not in self._by_token:
                        self._by_token[tok] = crop_id

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, crop_id: str) -> Optional[CropEntry]:
        """Get a CropEntry by canonical id. Returns None if not found."""
        return self._by_id.get(crop_id)

    def normalize(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Map any crop name/alias/Hindi text to a canonical entry dict.
        Compatible with the old crop_catalog.normalize() return shape.
        """
        if not query:
            return None
        q = query.lower().strip()
        # Direct id match
        if q in self._by_id:
            return self._by_id[q].to_dict()
        # Token match
        for tok in _tokenise(q):
            if tok in self._by_token:
                return self._by_id[self._by_token[tok]].to_dict()
        return None

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across names, Hindi, and aliases."""
        if not query:
            return self.popular(limit)
        q = query.lower()
        seen:    set           = set()
        results: List[Dict]   = []

        # 1. Direct id prefix
        for crop_id, entry in self._by_id.items():
            if crop_id.startswith(q) and crop_id not in seen:
                results.append(entry.to_dict())
                seen.add(crop_id)

        # 2. Name/alias contains
        for entry in self._by_id.values():
            if entry.id in seen:
                continue
            haystack = " ".join([entry.name, entry.name_hindi] + entry.aliases).lower()
            if q in haystack:
                results.append(entry.to_dict())
                seen.add(entry.id)

        return results[:limit]

    def popular(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [
            self._by_id[cid].to_dict()
            for cid in self._popular_ids
            if cid in self._by_id
        ][:limit]

    def all_ids(self) -> List[str]:
        return list(self._by_id.keys())

    def msp_table(self) -> Dict[str, int]:
        """Return {crop_id: msp} for all crops with MSP > 0."""
        return {
            cid: e.msp for cid, e in self._by_id.items() if e.msp > 0
        }


# ── Module-level singleton ────────────────────────────────────────────────────
crop_registry = CropRegistry()

# ── Backward-compatible shims ─────────────────────────────────────────────────
# Old code that imports from crop_catalog.py, etc., can continue to work.
# These thin wrappers delegate to crop_registry.

class _CropCatalogShim:
    """Drop-in shim so `from .crop_catalog import crop_catalog` still works."""
    def get(self, crop_id):          return crop_registry.get(crop_id)
    def normalize(self, query):      return crop_registry.normalize(query)
    def search(self, q, limit=10):   return crop_registry.search(q, limit)
    def popular(self, limit=10):     return crop_registry.popular(limit)

_catalog_shim = _CropCatalogShim()
