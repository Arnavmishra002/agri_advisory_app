from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.crop import CropAdvisoryViewSet
from advisory.services.location_context import LocationContext


class CropReleaseContractTests(SimpleTestCase):
    def test_location_survives_provider_outage_without_invented_field_inputs(self):
        unavailable = (
            {"status": "unavailable", "is_live": False, "current": {}, "forecast_7day": []},
            {"status": "unavailable", "is_live": False, "top_crops": []},
            {"weather": "timeout", "market": "timeout"},
        )
        for name, state, lat, lon in (
            ("Delhi", "Delhi", 28.6139, 77.2090),
            ("Mumbai", "Maharashtra", 19.0760, 72.8777),
        ):
            with self.subTest(location=name):
                ctx = LocationContext(latitude=lat, longitude=lon, display_name=name, state=state, source="manual")
                with patch("advisory.api.viewsets.crop.resolve_request_location", return_value=ctx), patch(
                    "advisory.services.crop_recommendation_engine.CropRecommendationEngine._fetch_realtime_context",
                    return_value=unavailable,
                ) as fetch:
                    request = APIRequestFactory().get("/api/advisories/", {"season": "kharif"})
                    response = CropAdvisoryViewSet.as_view({"get": "list"})(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(fetch.call_args.args[1:3], (lat, lon))
                self.assertTrue(response.data["coordinates"])
                self.assertFalse(response.data["weather_is_live"])
                self.assertFalse(response.data["market_is_live"])
                self.assertIsNone(response.data["soil_type"])
                self.assertIsNone(response.data["irrigation"])
                self.assertTrue(response.data["clarification_required"])
                self.assertTrue(response.data["recommendations"])
                for crop in response.data["recommendations"]:
                    self.assertIsNone(crop["market_price"])
