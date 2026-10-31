from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_WEATHER
from advisory.services.location_context import LocationContext


class ChatWeatherDisplayTests(SimpleTestCase):
    def test_tomorrow_uses_india_date_even_without_rain_probability(self):
        service = ChatIntelligenceService()
        ctx = LocationContext(latitude=26.85, longitude=80.95, display_name="Lucknow")
        weather = {"current": {"temperature": 26}, "forecast": [
            {"date": "2026-09-10", "max_temp": 32, "rainfall_mm": 8, "rain_probability": None}
        ]}
        context, _ = service._build_official_context(ctx, "Weather tomorrow?", INTENT_WEATHER, [], "en", _weather=weather)
        self.assertNotIn("None%", context)
        with patch("advisory.services.chat_intelligence_service.datetime") as clock:
            instant = datetime(2026, 9, 8, 20, tzinfo=timezone.utc)
            clock.now.side_effect = lambda tz=None: instant.astimezone(tz)
            answer = service._smart_rule_response("Weather tomorrow?", INTENT_WEATHER, [], ctx, context, "en")
        self.assertIn("Tomorrow in", answer)
        self.assertIn("unavailable", answer)
        self.assertNotIn("None%", answer)
        self.assertNotIn("7-Day Forecast", answer)
