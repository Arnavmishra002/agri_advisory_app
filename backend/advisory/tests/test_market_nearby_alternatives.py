from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from advisory.services.unified_realtime_service import MarketPricesService


class MarketNearbyAlternativesTests(SimpleTestCase):
    def setUp(self):
        self.service = MarketPricesService()

    def test_official_apmc_name_matches_farmer_facing_mandi_alias(self):
        result = self.service._apply_mandi_pricing(
            {
                "status": "success",
                "is_live": True,
                "top_crops": [{
                    "crop_name": "Wheat",
                    "mandi_name": "Lucknow APMC",
                    "modal_price": 2400,
                    "is_live": True,
                }],
            },
            "Lucknow",
            "Lucknow Mandi",
        )

        self.assertEqual(len(result["top_crops"]), 1)
        self.assertEqual(result["top_crops"][0]["mandi_name"], "Lucknow APMC")
        self.assertEqual(result["top_crops"][0]["price_source"], "live_mandi")

    @patch.object(MarketPricesService, "_mandi_coordinate_lookup")
    @patch.object(MarketPricesService, "get_prices")
    def test_returns_only_verified_nearby_rows_with_real_mandi_names(
        self,
        get_prices,
        coordinate_lookup,
    ):
        coordinate_lookup.return_value = {
            "unnao mandi": (26.55, 80.49),
            "lucknow mandi": (26.85, 80.95),
            "agra mandi": (27.18, 78.01),
        }
        get_prices.return_value = {
            "is_live": True,
            "data_source": "Agmarknet/data.gov.in",
            "reported_date": "2026-07-13",
            "top_crops": [
                {
                    "crop_name": "Wheat",
                    "mandi_name": "Lucknow Mandi",
                    "modal_price": 2550,
                    "date": "2026-07-13",
                    "is_live": True,
                },
                {
                    "crop_name": "Wheat",
                    "mandi_name": "Agra Mandi",
                    "modal_price": 2600,
                    "date": "2026-07-13",
                    "is_live": True,
                },
                {
                    "crop_name": "Wheat",
                    "mandi_name": "Unknown Mandi",
                    "modal_price": 2500,
                    "date": "2026-07-13",
                    "is_live": False,
                },
            ],
        }

        result = self.service.get_nearby_live_prices(
            "Unnao",
            selected_mandi="Unnao Mandi",
            state="Uttar Pradesh",
            radius_km=150,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["mandi_name"], "Lucknow Mandi")
        self.assertNotEqual(result[0]["mandi_name"], "Unnao Mandi")
        self.assertTrue(result[0]["is_live"])
        self.assertLessEqual(result[0]["distance_km"], 150)
        get_prices.assert_called_once_with(
            "Unnao",
            mandi=None,
            crop=None,
            lat=None,
            lon=None,
            state="Uttar Pradesh",
            include_estimates=False,
        )

    @patch("advisory.api.viewsets.market.market_service.get_nearby_live_prices")
    @patch("advisory.api.viewsets.market.market_service.get_prices")
    def test_mandi_endpoint_keeps_selected_unavailable_and_adds_separate_alternatives(
        self,
        get_prices,
        get_nearby_live_prices,
    ):
        get_prices.return_value = {
            "status": "unavailable",
            "is_live": False,
            "top_crops": [],
            "message": "No current official arrival rows for 'Unnao Mandi'.",
        }
        get_nearby_live_prices.return_value = [
            {
                "crop_name": "Wheat",
                "mandi_name": "Lucknow Mandi",
                "modal_price": 2550,
                "date": "2026-07-13",
                "distance_km": 63.4,
                "is_live": True,
            }
        ]

        response = APIClient().get(
            "/api/market-prices/mandi-prices/",
            {
                "mandi": "Unnao Mandi",
                "location": "Unnao",
                "state": "Uttar Pradesh",
                "latitude": 26.55,
                "longitude": 80.49,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_live"])
        self.assertEqual(response.data["top_crops"], [])
        self.assertEqual(
            response.data["nearby_live_alternatives"][0]["mandi_name"],
            "Lucknow Mandi",
        )
        get_nearby_live_prices.assert_called_once()
