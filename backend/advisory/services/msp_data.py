"""Authoritative Minimum Support Price references for marketing season 2026-27.

The values below are the base variants used by KrishiMitra when a commodity has
multiple announced variants (for example common paddy, hybrid jowar and medium
staple cotton).  Sugarcane is deliberately excluded because it has an FRP, not
an MSP.  Mandi prices must never be derived from this table.
"""

import re
from typing import Dict, Optional


MSP_MARKETING_SEASON = "2026-27"

# Canonical crop IDs used by the crop database. Values are rupees per quintal.
MSP_OFFICIAL_2026_27: Dict[str, int] = {
    # Kharif crops
    "rice": 2441,  # Paddy (Common); Grade A is Rs 2,461
    "jowar": 4023,  # Hybrid; Maldandi is Rs 4,073
    "bajra": 2900,
    "ragi": 5205,
    "maize": 2410,
    "tur": 8450,
    "moong": 8780,
    "urad": 8200,
    "groundnut": 7517,
    "sunflower": 8343,
    "soybean": 5708,
    "sesame": 10346,
    "niger": 10052,
    "cotton": 8267,  # Medium staple; long staple is Rs 8,667
    # Rabi crops
    "wheat": 2585,
    "barley": 2150,
    "gram": 5875,
    "masoor": 7000,
    "mustard": 6200,
    "safflower": 6540,
    # Commercial crops
    "jute": 5925,
    "copra": 12027,  # Milling copra; ball copra is Rs 12,500
}

MSP_CROP_ALIASES = {
    "arhar": "tur",
    "lentil": "masoor",
    "paddy": "rice",
}

MSP_CURRENT: Dict[str, int] = dict(MSP_OFFICIAL_2026_27)
MSP_CURRENT.update(
    {alias: MSP_OFFICIAL_2026_27[canonical] for alias, canonical in MSP_CROP_ALIASES.items()}
)

# Compatibility alias for older service imports. Values are current, despite
# the historical symbol name; new code should import MSP_CURRENT.
MSP_2024_25 = MSP_CURRENT

MSP_SOURCE_URLS = {
    "kharif": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260618&lang=3&reg=3",
    "rabi": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173566&lang=2&reg=48",
    "commercial": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2269182&lang=2&reg=48",
}


def get_current_msp(crop_id: str) -> Optional[int]:
    """Return current MSP for a canonical ID, alias, or Agmarknet label."""
    raw = (crop_id or "").strip().lower()
    direct = raw.replace("-", "_").replace(" ", "_")
    if direct in MSP_CURRENT:
        return MSP_CURRENT[direct]

    normalized = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    commodity_aliases = (
        ("bengal gram", "gram"),
        ("green gram", "moong"),
        ("black gram", "urad"),
        ("red gram", "tur"),
        ("finger millet", "ragi"),
        ("pearl millet", "bajra"),
        ("sunflower", "sunflower"),
        ("soyabean", "soybean"),
        ("soybean", "soybean"),
        ("paddy", "rice"),
        ("wheat", "wheat"),
        ("maize", "maize"),
        ("jowar", "jowar"),
        ("barley", "barley"),
        ("mustard", "mustard"),
        ("groundnut", "groundnut"),
        ("sesamum", "sesame"),
        ("sesame", "sesame"),
        ("cotton", "cotton"),
        ("safflower", "safflower"),
        ("niger", "niger"),
        ("lentil", "masoor"),
        ("masur", "masoor"),
        ("arhar", "tur"),
        ("tur", "tur"),
        ("moong", "moong"),
        ("urad", "urad"),
        ("jute", "jute"),
        ("copra", "copra"),
    )
    for label, canonical in commodity_aliases:
        if label in normalized:
            return MSP_OFFICIAL_2026_27[canonical]
    return None
