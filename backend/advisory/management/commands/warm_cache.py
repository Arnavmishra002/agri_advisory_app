"""
Management command: warm the Agmarknet price cache at startup.

Run from Procfile / Dockerfile CMD after `manage.py migrate`:
    python manage.py warm_cache

This ensures the first real user request sees sub-100ms market data
instead of waiting for the live Agmarknet API call.
"""

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pre-warm the Agmarknet price cache and weather geocode cache."

    def handle(self, *args, **options):
        self.stdout.write("Warming Agmarknet Direct cache...")
        try:
            from advisory.services.agmarknet_direct_client import agmarknet_direct
            result = agmarknet_direct.get_national_prices(force_refresh=True)
            count = len(result.get("top_crops", [])) if result else 0
            is_live = result.get("is_live", False) if result else False
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Agmarknet: {count} commodities loaded "
                    f"({'LIVE' if is_live else 'seed fallback'})"
                )
            )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  Agmarknet cache warm failed: {exc}"))

        self.stdout.write("Warming weather cache for major cities...")
        cities = [
            ("Delhi",     28.6139, 77.2090),
            ("Mumbai",    19.0760, 72.8777),
            ("Lucknow",   26.8467, 80.9462),
            ("Jaipur",    26.9124, 75.7873),
            ("Patna",     25.5941, 85.1376),
            ("Bhopal",    23.2599, 77.4126),
            ("Chandigarh",30.7333, 76.7794),
            ("Hyderabad", 17.3850, 78.4867),
            ("Pune",      18.5204, 73.8567),
        ]
        try:
            from advisory.services.unified_realtime_service import weather_service
            ok = 0
            for name, lat, lon in cities:
                try:
                    d = weather_service.get_weather(name, lat, lon, lang="hi")
                    if d.get("is_live"):
                        ok += 1
                except Exception:
                    pass
            self.stdout.write(
                self.style.SUCCESS(f"  Weather: {ok}/{len(cities)} cities cached")
            )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  Weather cache warm failed: {exc}"))

        self.stdout.write(self.style.SUCCESS("Cache warm complete."))
