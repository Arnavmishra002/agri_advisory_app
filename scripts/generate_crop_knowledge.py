#!/usr/bin/env python3
"""Generate the Phase 1 crop-profile knowledge snapshot from the canonical catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "phase1" / "knowledge_base" / "crops" / "indian_crop_profiles_202.txt"
sys.path.insert(0, str(BACKEND))

from advisory.services.comprehensive_crop_database import ALL_CROP_DATA  # noqa: E402


def _display_name(crop_id: str) -> str:
    return crop_id.replace("_", " ").title()


def render_crop_knowledge() -> str:
    lines = [
        "KRISHIMITRA INDIAN CROP PROFILE CATALOG",
        "Generated from the canonical recommendation database. These are planning profiles, not live observations.",
        "Do not infer current weather, mandi prices, sensor readings, disease certainty, or chemical doses from this catalog.",
        "Verify variety, sowing window, nutrient dose, and plant-protection label with the local KVK/state package of practices.",
        "",
    ]
    for crop_id in sorted(ALL_CROP_DATA):
        profile = ALL_CROP_DATA[crop_id]
        aliases = sorted({
            str(value).strip()
            for value in (profile.get("aliases") or [])
            if str(value).strip()
        })
        states = ", ".join(profile.get("states_primary") or []) or "Location-specific verification required"
        zones = ", ".join(profile.get("agro_zones") or []) or "Not specified"
        soils = ", ".join(profile.get("soil_preference") or []) or "Local soil test required"
        rotation = ", ".join(
            (profile.get("rotation") or {}).get("preferred_previous_categories") or []
        ) or "Use a locally suitable rotation"
        market_name = (profile.get("market_mapping") or {}).get("official_commodity") or _display_name(crop_id)
        lines.extend([
            f"CROP_ID: {crop_id}",
            f"CROP: {_display_name(crop_id)} | HINDI: {profile.get('name_hindi') or 'Not specified'}",
            f"ALIASES: {' | '.join(aliases)}",
            f"CLASSIFICATION: {profile.get('category')} | SEASON: {profile.get('season')}",
            f"REGIONAL FIT: states={states}; agro-climatic zones={zones}",
            f"SOIL FIT: {soils}; pH {profile.get('ph_min')}-{profile.get('ph_max')}; salinity tolerance={profile.get('salinity_tolerance')}",
            f"CLIMATE FIT: {profile.get('temperature_min')}-{profile.get('temperature_max')} C; rainfall need about {profile.get('rainfall_mm')} mm; water requirement={profile.get('water_requirement')}",
            f"CROP CYCLE: about {profile.get('duration_days')} days; nutrient demand={profile.get('nutrient_demand')}; preferred previous crop categories={rotation}",
            f"MARKET LOOKUP NAME: {market_name}. Price policy: fresh official row only; never estimate a live price.",
            f"PROFILE SOURCE: {profile.get('agronomy_source')}. Profile version: {profile.get('profile_version')}.",
            "SAFETY: This profile supports crop selection and follow-up questions. Confirm field-specific practice with the local KVK.",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when the committed snapshot is stale")
    args = parser.parse_args()
    rendered = render_crop_knowledge()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"Crop knowledge snapshot is stale: {OUTPUT}", file=sys.stderr)
            return 1
        print(f"Crop knowledge snapshot is current ({len(ALL_CROP_DATA)} crops)")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(ALL_CROP_DATA)} crop profiles to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
