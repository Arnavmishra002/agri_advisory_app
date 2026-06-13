#!/usr/bin/env python3
"""
Indian crop catalog with Google-style autocomplete search.
Used for mandi price lookup and KrishiRaksha crop selection.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .unified_realtime_service import CROP_HINDI, MSP_2024_25

# id, English name, Hindi, aliases, category
_CROP_ROWS: List[Dict[str, Any]] = [
    {"id": "wheat", "name": "Wheat", "hindi": "गेहूँ", "aliases": ["gehun", "gehu"], "category": "cereal"},
    {"id": "rice", "name": "Rice", "hindi": "धान / चावल", "aliases": ["paddy", "chawal", "dhan"], "category": "cereal"},
    {"id": "maize", "name": "Maize", "hindi": "मक्का", "aliases": ["corn", "makka"], "category": "cereal"},
    {"id": "bajra", "name": "Bajra", "hindi": "बाजरा", "aliases": ["pearl millet"], "category": "cereal"},
    {"id": "jowar", "name": "Jowar", "hindi": "ज्वार", "aliases": ["sorghum"], "category": "cereal"},
    {"id": "barley", "name": "Barley", "hindi": "जौ", "aliases": ["jau"], "category": "cereal"},
    {"id": "ragi", "name": "Ragi", "hindi": "रागी", "aliases": ["finger millet"], "category": "cereal"},
    {"id": "soybean", "name": "Soybean", "hindi": "सोयाबीन", "aliases": ["soya"], "category": "oilseed"},
    {"id": "mustard", "name": "Mustard", "hindi": "सरसों", "aliases": ["sarson", "rapeseed"], "category": "oilseed"},
    {"id": "groundnut", "name": "Groundnut", "hindi": "मूँगफली", "aliases": ["peanut", "moongfali"], "category": "oilseed"},
    {"id": "sunflower", "name": "Sunflower", "hindi": "सूरजमुखी", "aliases": [], "category": "oilseed"},
    {"id": "cotton", "name": "Cotton", "hindi": "कपास", "aliases": ["kapas"], "category": "fiber"},
    {"id": "sugarcane", "name": "Sugarcane", "hindi": "गन्ना", "aliases": ["ganna"], "category": "cash"},
    {"id": "gram", "name": "Gram", "hindi": "चना", "aliases": ["chickpea", "chana"], "category": "pulse"},
    {"id": "lentil", "name": "Lentil", "hindi": "मसूर / दाल", "aliases": ["masoor", "dal"], "category": "pulse"},
    {"id": "moong", "name": "Moong", "hindi": "मूंग", "aliases": ["green gram", "mung"], "category": "pulse"},
    {"id": "urad", "name": "Urad", "hindi": "उड़द", "aliases": ["black gram"], "category": "pulse"},
    {"id": "arhar", "name": "Arhar", "hindi": "अरहर / तुअर", "aliases": ["tur", "pigeon pea", "toor"], "category": "pulse"},
    {"id": "tomato", "name": "Tomato", "hindi": "टमाटर", "aliases": ["tamatar"], "category": "vegetable"},
    {"id": "potato", "name": "Potato", "hindi": "आलू", "aliases": ["aloo"], "category": "vegetable"},
    {"id": "onion", "name": "Onion", "hindi": "प्याज", "aliases": ["pyaz"], "category": "vegetable"},
    {"id": "garlic", "name": "Garlic", "hindi": "लहसुन", "aliases": ["lahsun"], "category": "vegetable"},
    {"id": "chilli", "name": "Chilli", "hindi": "मिर्च", "aliases": ["chili", "mirch", "red chilli"], "category": "vegetable"},
    {"id": "brinjal", "name": "Brinjal", "hindi": "बैंगन", "aliases": ["eggplant", "baingan"], "category": "vegetable"},
    {"id": "cabbage", "name": "Cabbage", "hindi": "पत्ता गोभी", "aliases": ["patta gobhi"], "category": "vegetable"},
    {"id": "cauliflower", "name": "Cauliflower", "hindi": "फूल गोभी", "aliases": ["gobi", "phool gobhi"], "category": "vegetable"},
    {"id": "okra", "name": "Okra", "hindi": "भिंडी", "aliases": ["ladyfinger", "bhindi"], "category": "vegetable"},
    {"id": "bottle gourd", "name": "Bottle Gourd", "hindi": "लौकी", "aliases": ["lauki", "ghiya"], "category": "vegetable"},
    {"id": "bitter gourd", "name": "Bitter Gourd", "hindi": "करेला", "aliases": ["karela"], "category": "vegetable"},
    {"id": "cucumber", "name": "Cucumber", "hindi": "खीरा", "aliases": ["kheera"], "category": "vegetable"},
    {"id": "pumpkin", "name": "Pumpkin", "hindi": "कद्दू", "aliases": ["kaddu"], "category": "vegetable"},
    {"id": "spinach", "name": "Spinach", "hindi": "पालक", "aliases": ["palak"], "category": "vegetable"},
    {"id": "carrot", "name": "Carrot", "hindi": "गाजर", "aliases": ["gajar"], "category": "vegetable"},
    {"id": "beetroot", "name": "Beetroot", "hindi": "चुकंदर", "aliases": ["chukandar"], "category": "vegetable"},
    {"id": "capsicum", "name": "Capsicum", "hindi": "शिमला मिर्च", "aliases": ["shimla mirch", "bell pepper"], "category": "vegetable"},
    {"id": "peas", "name": "Peas", "hindi": "मटर", "aliases": ["matar", "green pea"], "category": "vegetable"},
    {"id": "beans", "name": "Beans", "hindi": "बीन्स / सेम", "aliases": ["sem", "french beans"], "category": "vegetable"},
    {"id": "turmeric", "name": "Turmeric", "hindi": "हल्दी", "aliases": ["haldi"], "category": "spice"},
    {"id": "ginger", "name": "Ginger", "hindi": "अदरक", "aliases": ["adrak"], "category": "spice"},
    {"id": "coriander", "name": "Coriander", "hindi": "धनिया", "aliases": ["dhania", "cilantro"], "category": "spice"},
    {"id": "cumin", "name": "Cumin", "hindi": "जीरा", "aliases": ["jeera"], "category": "spice"},
    {"id": "banana", "name": "Banana", "hindi": "केला", "aliases": ["kela"], "category": "fruit"},
    {"id": "mango", "name": "Mango", "hindi": "आम", "aliases": ["aam"], "category": "fruit"},
    {"id": "apple", "name": "Apple", "hindi": "सेब", "aliases": ["seb"], "category": "fruit"},
    {"id": "grapes", "name": "Grapes", "hindi": "अंगूर", "aliases": ["angoor"], "category": "fruit"},
    {"id": "pomegranate", "name": "Pomegranate", "hindi": "अनार", "aliases": ["anar"], "category": "fruit"},
    {"id": "orange", "name": "Orange", "hindi": "संतरा", "aliases": ["santra", "kinnow"], "category": "fruit"},
    {"id": "papaya", "name": "Papaya", "hindi": "पपीता", "aliases": ["papita"], "category": "fruit"},
    {"id": "watermelon", "name": "Watermelon", "hindi": "तरबूज", "aliases": ["tarbuj"], "category": "fruit"},
    {"id": "muskmelon", "name": "Muskmelon", "hindi": "खरबूजा", "aliases": ["kharbooja"], "category": "fruit"},
    {"id": "guava", "name": "Guava", "hindi": "अमरूद", "aliases": ["amrud"], "category": "fruit"},
    {"id": "litchi", "name": "Litchi", "hindi": "लीची", "aliases": ["lychee"], "category": "fruit"},
    {"id": "coconut", "name": "Coconut", "hindi": "नारियल", "aliases": ["nariyal"], "category": "plantation"},
    {"id": "arecanut", "name": "Arecanut", "hindi": "सुपारी", "aliases": ["supari"], "category": "plantation"},
    {"id": "tea", "name": "Tea", "hindi": "चाय", "aliases": ["chai"], "category": "plantation"},
    {"id": "coffee", "name": "Coffee", "hindi": "कॉफी", "aliases": [], "category": "plantation"},
    {"id": "rubber", "name": "Rubber", "hindi": "रबड़", "aliases": [], "category": "plantation"},
    {"id": "tobacco", "name": "Tobacco", "hindi": "तंबाकू", "aliases": ["tambaku"], "category": "cash"},
    {"id": "jute", "name": "Jute", "hindi": "जूट", "aliases": [], "category": "fiber"},
]


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[\s,/\-]+", text.lower()) if len(t) >= 2]


class CropCatalog:
    """Searchable crop catalog with MSP and Hindi metadata."""

    def __init__(self):
        self._crops: List[Dict[str, Any]] = []
        self._by_id: Dict[str, Dict[str, Any]] = {}
        for row in _CROP_ROWS:
            entry = {
                "id": row["id"],
                "name": row["name"],
                "hindi": row.get("hindi") or CROP_HINDI.get(row["id"], ""),
                "aliases": list(row.get("aliases") or []),
                "category": row.get("category", "general"),
                "msp": MSP_2024_25.get(row["id"]),
                "has_msp": row["id"] in MSP_2024_25,
            }
            self._crops.append(entry)
            self._by_id[row["id"]] = entry

    def get(self, crop_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get((crop_id or "").lower().strip())

    def normalize(self, query: str) -> Optional[Dict[str, Any]]:
        """Resolve free text to a catalog crop."""
        if not query or not str(query).strip():
            return None
        q = str(query).lower().strip()
        if q in self._by_id:
            return self._by_id[q]
        for crop in self._crops:
            if q == crop["name"].lower():
                return crop
            if q == crop["hindi"].lower():
                return crop
            if any(q == a.lower() for a in crop["aliases"]):
                return crop
        # Partial match: filter out short queries and common stopwords to prevent false matches (e.g., Hindi 'का' matching 'मक्का')
        if len(q) < 3 or q in {"में", "और", "लिए", "क्या", "बारे", "सब", "को", "से", "he", "she", "it", "they", "the", "and", "for", "with", "this", "that", "you", "your"}:
            return None
        results = self.search(query, limit=1)
        return results[0] if results else None

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Google-style ranked crop suggestions."""
        query = (query or "").strip()
        if len(query) < 1:
            return self.popular(limit)

        q_lower = query.lower()
        q_tokens = _tokenize(query)
        scored: List[tuple] = []

        for crop in self._crops:
            name_l = crop["name"].lower()
            hindi_l = (crop["hindi"] or "").lower()
            aliases_l = [a.lower() for a in crop["aliases"]]
            score = 0.0

            if name_l == q_lower or crop["id"] == q_lower:
                score = 100.0
            elif q_lower in name_l or name_l.startswith(q_lower):
                score = 85.0
            elif hindi_l and (q_lower in hindi_l or hindi_l.startswith(q_lower)):
                score = 80.0
            elif any(q_lower in a or a.startswith(q_lower) for a in aliases_l):
                score = 75.0
            else:
                for tok in q_tokens:
                    if len(tok) < 3 or tok in {"का", "की", "के", "में", "और", "लिए", "क्या", "बारे", "सब", "को", "से", "he", "she", "it", "they", "the", "and", "for", "with", "this", "that", "you", "your"}:
                        continue
                    if tok in name_l or tok in crop["id"]:
                        score += 25.0
                    if hindi_l and tok in hindi_l:
                        score += 20.0
                    if any(tok in a for a in aliases_l):
                        score += 18.0

            if score > 0:
                if crop["has_msp"]:
                    score += 3.0
                scored.append((score, crop))

        scored.sort(key=lambda x: (-x[0], x[1]["name"]))
        out = []
        for _, crop in scored[:limit]:
            out.append({
                "id": crop["id"],
                "name": crop["name"],
                "hindi": crop["hindi"],
                "category": crop["category"],
                "msp": crop["msp"],
                "label": f"{crop['name']} ({crop['hindi']})" if crop["hindi"] else crop["name"],
                "search_term": crop["name"],
                "commodity_filter": crop["name"],
            })
        return out

    def popular(self, limit: int = 8) -> List[Dict[str, Any]]:
        popular_ids = [
            "wheat", "rice", "tomato", "onion", "potato", "cotton",
            "mustard", "soybean", "maize", "chilli",
        ]
        return [
            {
                "id": c["id"],
                "name": c["name"],
                "hindi": c["hindi"],
                "category": c["category"],
                "msp": c["msp"],
                "label": f"{c['name']} ({c['hindi']})" if c["hindi"] else c["name"],
                "search_term": c["name"],
                "commodity_filter": c["name"],
            }
            for cid in popular_ids
            if (c := self.get(cid))
        ][:limit]


crop_catalog = CropCatalog()
