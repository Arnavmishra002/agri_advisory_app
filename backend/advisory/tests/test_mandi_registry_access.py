from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from advisory.services.agmarknet_client import AgmarknetClient
from advisory.services.unified_realtime_service import MarketPricesService


@override_settings(RATE_LIMIT_ENABLED=False)
class MandiRegistryAccessTests(SimpleTestCase):
    def test_state_scope_requests_full_bounded_registry(self):
        client = APIClient()
        expected = {
            "status": "success",
            "mandis": [],
            "scope": "state",
        }
        with patch(
            "advisory.api.viewsets.market.market_service.list_mandis",
            return_value=expected,
        ) as list_mandis:
            response = client.get(
                "/api/market-prices/mandis/",
                {
                    "location": "Lucknow",
                    "state": "Uttar Pradesh",
                    "scope": "state",
                    "limit": 500,
                },
            )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(list_mandis.call_args.kwargs["include_all"])
        self.assertEqual(list_mandis.call_args.kwargs["max_results"], 500)

    def test_state_scope_keeps_all_registered_mandis_with_gps(self):
        service = MarketPricesService()
        official = [
            {
                "name": f"Official Mandi {index}",
                "state": "Uttar Pradesh",
                "source": "Agmarknet 2.0 API",
                "registered": True,
                "live": False,
            }
            for index in range(120)
        ]

        with patch(
            "advisory.services.agmarknet_client.agmarknet_client.list_markets_for_location",
            return_value=official,
        ), patch.object(service, "_merge_reference_mandis") as merge_reference, patch.object(
            service, "_has_registered_data_gov_key", return_value=False
        ), patch.object(service, "_effective_data_gov_key", return_value=None):
            result = service.list_mandis(
                "Lucknow",
                lat=26.8467,
                lon=80.9462,
                state="Uttar Pradesh",
                include_all=True,
                max_results=500,
            )

        self.assertEqual(result["scope"], "state")
        self.assertEqual(result["registered_count"], 120)
        self.assertEqual(len(result["mandis"]), 120)
        self.assertEqual(result["live_count"], 0)
        self.assertEqual(result["coverage"], "official_registry")
        self.assertEqual(result["reference_count"], 0)
        merge_reference.assert_not_called()

    def test_registry_entry_is_not_a_verified_live_price(self):
        client = AgmarknetClient()
        client._get_filters = lambda: {
            "state_data": [{"state_id": 34, "state_name": "Uttar Pradesh"}],
            "market_data": [{
                "id": 315,
                "mkt_name": "Lucknow APMC",
                "state_id": 34,
            }],
        }

        result = client.list_markets_for_location("Lucknow", state="Uttar Pradesh")

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["registered"])
        self.assertFalse(result[0]["live"])

    def test_nearby_scope_never_pads_with_unknown_distance_mandis(self):
        service = MarketPricesService()
        registry = [
            {"name": "Varanasi APMC", "state": "Uttar Pradesh", "registered": True},
            {"name": "Mirzapur APMC", "state": "Uttar Pradesh", "registered": True},
            {"name": "Agra APMC", "state": "Uttar Pradesh", "registered": True},
        ]
        enriched = [
            {**registry[0], "distance_km": 3.9},
            {**registry[1], "distance_km": 49.0},
            {**registry[2], "distance_km": None},
        ]

        with patch(
            "advisory.services.agmarknet_client.agmarknet_client.list_markets_for_location",
            return_value=registry,
        ), patch.object(service, "_merge_reference_mandis"), patch.object(
            service, "_enrich_and_sort_mandis", return_value=enriched
        ), patch.object(
            service, "_has_registered_data_gov_key", return_value=False
        ), patch.object(service, "_effective_data_gov_key", return_value=None):
            result = service.list_mandis(
                "Varanasi",
                lat=25.3176,
                lon=82.9739,
                state="Uttar Pradesh",
                radius_km=50,
                include_all=False,
            )

        self.assertEqual(
            [mandi["name"] for mandi in result["mandis"]],
            ["Varanasi APMC", "Mirzapur APMC"],
        )
        self.assertTrue(all(mandi["distance_km"] <= 50 for mandi in result["mandis"]))
