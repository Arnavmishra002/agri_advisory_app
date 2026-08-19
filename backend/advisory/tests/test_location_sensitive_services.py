from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.crop import CropAdvisoryViewSet, CropViewSet
from advisory.api.viewsets.field_advisory import FieldAdvisoryViewSet
from advisory.api.viewsets.iot import IoTBlockchainViewSet
from advisory.api.viewsets.market import MarketPricesViewSet
from advisory.api.viewsets.misc import SMSIVRViewSet, TextToSpeechViewSet
from advisory.api.viewsets.weather import WeatherViewSet
from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI


class LocationSensitiveServiceContractTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _get(self, path, viewset, action):
        request = self.factory.get(path, {"location_confirmed": "false"})
        return viewset.as_view({"get": action})(request)

    @patch("advisory.api.viewsets.weather.weather_service.get_weather")
    def test_weather_requires_confirmed_location_before_provider_call(self, provider):
        response = self._get("/api/weather/", WeatherViewSet, "list")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "LOCATION_REQUIRED")
        self.assertFalse(response.data["location_context"]["confirmed"])
        provider.assert_not_called()

    @patch("advisory.api.viewsets.market.market_service.get_prices")
    def test_market_requires_confirmed_location_before_provider_call(self, provider):
        response = self._get("/api/market-prices/", MarketPricesViewSet, "list")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "LOCATION_REQUIRED")
        provider.assert_not_called()

    @patch("advisory.api.viewsets.crop.crop_recommendation_engine.recommend_from_context")
    def test_crop_recommendation_requires_confirmed_location(self, recommender):
        response = self._get("/api/advisories/", CropAdvisoryViewSet, "list")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "LOCATION_REQUIRED")
        recommender.assert_not_called()

    @patch("advisory.api.viewsets.field_advisory.field_sensor_service._fetch_open_meteo_soil_weather")
    def test_field_soil_profile_requires_confirmed_location(self, provider):
        response = self._get(
            "/api/field-advisory/soil_profile/",
            FieldAdvisoryViewSet,
            "soil_profile",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "LOCATION_REQUIRED")
        provider.assert_not_called()

    @patch("advisory.api.viewsets.iot.iot_blockchain.get_iot_sensor_data")
    def test_iot_requires_confirmed_location(self, provider):
        response = self._get(
            "/api/iot-blockchain/sensor_data/",
            IoTBlockchainViewSet,
            "sensor_data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "LOCATION_REQUIRED")
        provider.assert_not_called()

    @patch("advisory.api.viewsets.weather.weather_service.get_weather")
    def test_weather_propagates_each_confirmed_gps_location(self, provider):
        provider.return_value = {"status": "success", "is_live": True}
        view = WeatherViewSet.as_view({"get": "list"})

        delhi = view(self.factory.get(
            "/api/weather/",
            {"latitude": 28.6139, "longitude": 77.2090},
        ))
        mumbai = view(self.factory.get(
            "/api/weather/",
            {"latitude": 19.0760, "longitude": 72.8777},
        ))

        self.assertEqual(delhi.status_code, 200)
        self.assertEqual(mumbai.status_code, 200)
        self.assertAlmostEqual(delhi.data["location_context"]["latitude"], 28.6139)
        self.assertAlmostEqual(mumbai.data["location_context"]["latitude"], 19.0760)
        self.assertEqual(provider.call_args_list[0].args[1:3], (28.6139, 77.2090))
        self.assertEqual(provider.call_args_list[1].args[1:3], (19.0760, 72.8777))

    @patch("advisory.api.viewsets.market.market_service.get_prices")
    def test_market_propagates_confirmed_location_to_provider(self, provider):
        provider.return_value = {"status": "success", "is_live": True, "top_crops": []}
        request = self.factory.get(
            "/api/market-prices/",
            {"latitude": 19.0760, "longitude": 72.8777, "crop": "onion"},
        )

        response = MarketPricesViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(provider.call_args.kwargs["lat"], 19.0760)
        self.assertEqual(provider.call_args.kwargs["lon"], 72.8777)
        self.assertAlmostEqual(response.data["location_context"]["longitude"], 72.8777)

    @patch("advisory.api.viewsets.crop.market_service.get_prices")
    @patch("advisory.api.viewsets.crop.crop_recommendation_engine.recommend_from_context")
    def test_crop_information_uses_canonical_services_not_legacy_aggregator(
        self, recommender, market
    ):
        recommender.return_value = {
            "recommendations": [{"crop_name": "Onion", "score": 82.0}],
            "data_source": "KrishiMitra crop engine",
        }
        market.return_value = {
            "status": "success",
            "is_live": True,
            "top_crops": [{"crop_name": "Onion", "modal_price": 2100}],
            "data_source": "data.gov.in",
        }
        request = self.factory.get(
            "/api/crops/",
            {"latitude": 19.0760, "longitude": 72.8777, "crop": "onion"},
        )

        response = CropViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["crop_info"]["crop_name"], "Onion")
        self.assertTrue(response.data["market_data_quality"]["is_live"])

    @patch("advisory.models.FarmerProfile.objects.filter")
    def test_whatsapp_without_profile_location_does_not_default_to_delhi(self, profiles):
        profiles.return_value.first.return_value = None

        ctx = SMSIVRViewSet()._build_location_context("919999999999")

        self.assertIsNone(ctx.latitude)
        self.assertIsNone(ctx.longitude)
        self.assertFalse(ctx.confirmed)

    @patch("advisory.api.viewsets.misc.TextToSpeechViewSet._render_tts")
    @patch("advisory.services.chat_intelligence_service.chat_intelligence_service.answer")
    def test_advisory_audio_without_profile_does_not_default_to_delhi(self, answer, render):
        answer.return_value = {"response": "Please confirm your location."}
        render.return_value = Response({"status": "ok"})
        request = self.factory.post(
            "/api/tts/advisory-audio/",
            {"query": "Will it rain tomorrow?", "language": "en"},
            format="json",
        )

        TextToSpeechViewSet.as_view({"post": "advisory_audio"})(request)

        ctx = answer.call_args.args[1]
        self.assertIsNone(ctx.latitude)
        self.assertIsNone(ctx.longitude)
        self.assertFalse(ctx.confirmed)

    def test_legacy_pest_fallback_is_never_labeled_live_or_success(self):
        data = UltraDynamicGovernmentAPI()._get_fallback_pest_data("Lucknow")

        self.assertEqual(data["status"], "unavailable")
        self.assertFalse(data["is_live"])
        self.assertEqual(data["data_source"], "unavailable")
