from unittest.mock import Mock, patch
from datetime import datetime, timezone

from django.test import TestCase

from advisory.services.enhanced_market_prices import EnhancedMarketPricesService
from advisory.services.agmarknet_direct_client import AgmarknetDirectClient
from advisory.services.data_gov_mandi_client import DataGovMandiClient
from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from advisory.services.unified_realtime_service import MarketPricesService
from advisory.services.market_data_quality import (
    build_dated_official_reference,
    filter_fresh_live_rows,
)


class MarketDataSecurityTests(TestCase):
    def test_official_rows_older_than_one_day_are_not_current(self):
        rows, age, _ = filter_fresh_live_rows(
            [{
                "crop_name": "Wheat",
                "modal_price": 2400,
                "reported_date": "27-07-2026",
                "is_live": True,
            }],
            now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
        )

        self.assertEqual(rows, [])
        self.assertIsNone(age)

    def test_recent_older_official_rows_are_kept_only_as_dated_reference(self):
        rows, age, reported = build_dated_official_reference(
            [{
                "crop_name": "Wheat",
                "modal_price": 2577.54,
                "reported_date": "27-07-2026",
                "is_live": True,
                "price_source": "agmarknet_state_average",
            }],
            now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
        )

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["is_live"])
        self.assertEqual(rows[0]["freshness"], "dated_official")
        self.assertEqual(reported, "27-07-2026")
        self.assertGreater(age, 24 * 60)

    @patch("advisory.services.data_gov_mandi_client.data_gov_mandi_client.get_national_prices")
    @patch("advisory.services.agmarknet_client.agmarknet_client.get_market_prices")
    def test_market_service_exposes_dated_official_state_reference_without_calling_it_live(
        self, agmarknet, national
    ):
        national.return_value = {
            "status": "unavailable",
            "is_live": False,
            "top_crops": [],
        }
        agmarknet.return_value = {
            "status": "success",
            "is_live": True,
            "coverage": "state",
            "state": "Uttar Pradesh",
            "data_source": "Agmarknet 2.0 API",
            "reported_date": "27-07-2026",
            "top_crops": [{
                "crop_name": "Wheat",
                "modal_price": 2527.65,
                "reported_date": "27-07-2026",
                "is_live": True,
                "price_source": "agmarknet_state_average",
            }],
        }

        with patch(
            "advisory.services.market_data_quality.datetime",
            wraps=datetime,
        ) as mocked_datetime:
            mocked_datetime.now.return_value = datetime(
                2026, 7, 29, 12, tzinfo=timezone.utc
            )
            response = MarketPricesService().get_prices(
                "Varanasi", state="Uttar Pradesh"
            )

        self.assertEqual(response["status"], "unavailable")
        self.assertFalse(response["is_live"])
        self.assertTrue(response["has_dated_official_reference"])
        self.assertEqual(
            response["latest_official_rows"][0]["freshness"],
            "dated_official",
        )
        self.assertEqual(
            response["latest_official_coverage"],
            "state",
        )
        self.assertIn("No estimated price", response["message"])
        # The dated row must be announced as separate from a current price.
        # Assert the meaning, not one exact phrasing, so wording can improve.
        self.assertIn("separately", response["message"])
        self.assertNotIn("no historical fallback", response["message"].lower())

        # "message" is rendered straight into the farmer-facing price screen,
        # so it must never carry operator instructions. It previously shipped
        # the sentence "adding a DATA_GOV_IN_API_KEY widens state and mandi
        # coverage" -- displayed in English to farmers reading a Hindi UI.
        farmer_text = response["message"].lower()
        for jargon in ("api_key", "api key", "env", "agmarknet is queried",
                       "freshness window", "data_gov"):
            self.assertNotIn(jargon, farmer_text,
                             f"operator jargon {jargon!r} leaked into the farmer message")
        # The diagnostic detail still has to exist, just under its own key.
        self.assertIn("operator_note", response)
        self.assertIn("freshness window", response["operator_note"].lower())

    @patch.object(DataGovMandiClient, "_fetch_data_gov", return_value=None)
    @patch.object(DataGovMandiClient, "_fetch_agmarknet_direct", return_value=None)
    def test_live_client_returns_unavailable_instead_of_seed_prices(
        self, _direct, _data_gov
    ):
        service = DataGovMandiClient()

        response = service.get_national_prices(force_refresh=True)

        self.assertEqual(response["status"], "unavailable")
        self.assertFalse(response["is_live"])
        self.assertEqual(response["top_crops"], [])

    @patch.object(AgmarknetDirectClient, "_fetch_live", return_value=None)
    def test_agmarknet_direct_does_not_serve_seed_prices(self, _fetch_live):
        response = AgmarknetDirectClient().get_national_prices(force_refresh=True)

        self.assertIsNone(response)

    @patch("advisory.services.data_gov_mandi_client.data_gov_mandi_client.get_national_prices")
    @patch("advisory.services.agmarknet_client.agmarknet_client.get_market_prices", return_value=None)
    def test_market_service_rejects_non_live_upstream_rows(self, _agmarknet, national):
        national.return_value = {
            "status": "fallback",
            "is_live": False,
            "data_source": "seed_fallback",
            "top_crops": [{
                "crop_name": "Wheat",
                "modal_price": 2400,
                "price_source": "seed_fallback",
                "is_live": False,
            }],
        }

        response = MarketPricesService().get_prices(
            "Delhi", state="Delhi", crop="wheat"
        )

        self.assertEqual(response["status"], "unavailable")
        self.assertFalse(response["is_live"])
        self.assertEqual(response["top_crops"], [])

    def test_market_service_rejects_undated_live_rows(self):
        response = MarketPricesService._validated_live_data({
            "status": "success",
            "is_live": True,
            "data_source": "official test feed",
            "top_crops": [{
                "crop_name": "Wheat",
                "modal_price": 2400,
                "price_source": "data_gov_in_official",
                "is_live": True,
            }],
        })

        self.assertIsNone(response)

    def test_data_gov_formatter_rejects_rows_without_publication_date(self):
        response = DataGovMandiClient()._format_datagov_response([
            {
                "commodity": "Wheat",
                "modal_price": "2400",
                "market": "Test Mandi",
            }
        ])

        self.assertEqual(response, {})

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": ""})
    def test_data_gov_requests_do_not_use_hardcoded_api_key(self):
        service = EnhancedMarketPricesService()
        called_urls = []

        def fake_get(url, **kwargs):
            called_urls.append(url)
            return Mock(status_code=500)

        service.session.get = fake_get

        service._fetch_from_data_gov_in("Lucknow", "Uttar Pradesh")

        self.assertGreater(len(called_urls), 0)
        self.assertTrue(all("api-key=" not in url for url in called_urls))

    # Long enough for api_keys.is_real_key, and deliberately not shaped like a real
    # provider key -- GitHub push protection flags credential-shaped test data.
    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": "notarealkey-testfixture-only-000000000"})
    def test_data_gov_uses_env_api_key_when_configured(self):
        service = EnhancedMarketPricesService()
        called_urls = []

        def fake_get(url, **kwargs):
            called_urls.append(url)
            return Mock(status_code=500)

        service.session.get = fake_get

        service._fetch_from_data_gov_in("Lucknow", "Uttar Pradesh")

        self.assertTrue(
            any("api-key=notarealkey-testfixture-only-000000000" in url for url in called_urls)
        )

    def test_synthetic_mandi_fallback_is_labeled_non_live(self):
        service = EnhancedMarketPricesService()

        mandis = service._filter_mandis_by_location(
            [{"name": "Bad Mandi", "latitude": "bad", "longitude": 80.0}],
            "Testville",
            latitude=26.0,
            longitude=80.0,
            state="Uttar Pradesh",
        )

        self.assertGreater(len(mandis), 0)
        for mandi in mandis:
            self.assertEqual(mandi["source"], "synthetic_fallback")
            self.assertFalse(mandi["live"])
            self.assertFalse(mandi["is_live"])
            self.assertEqual(mandi["status"], "fallback")

    def test_bad_mandi_coordinate_rows_are_skipped(self):
        service = EnhancedMarketPricesService()

        mandis = service._filter_mandis_by_location(
            [
                {"name": "Bad Mandi", "latitude": "bad", "longitude": 80.0},
                {"name": "Good Mandi", "latitude": "26.1", "longitude": "80.1"},
            ],
            "Testville",
            latitude=26.0,
            longitude=80.0,
            state="Uttar Pradesh",
        )

        self.assertEqual(mandis[0]["name"], "Good Mandi")
        self.assertEqual(mandis[0]["source"], "reference database")
        self.assertFalse(mandis[0]["live"])

    @patch.object(EnhancedMarketPricesService, "_fetch_agmarknet_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_fetch_enam_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_fetch_fci_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_try_alternative_government_sources", return_value=None)
    def test_market_price_fallback_is_estimated_not_success(
        self,
        _alternative,
        _fci,
        _enam,
        _agmarknet,
    ):
        service = EnhancedMarketPricesService()

        response = service.get_market_prices("Lucknow", latitude=26.8467, longitude=80.9462)

        self.assertEqual(response["status"], "fallback")
        self.assertFalse(response["is_live"])
        self.assertLessEqual(response["data_reliability"], 0.5)
        self.assertIn("not live", response["note"].lower())
        self.assertTrue(response["crops"])
        for crop in response["crops"]:
            self.assertFalse(crop["is_live"])
            self.assertEqual(crop["price_status"], "estimated")
            self.assertEqual(crop["data_source"], "msp_reference_estimate")

    @patch.object(EnhancedMarketPricesService, "_fetch_agmarknet_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_fetch_enam_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_fetch_fci_data", return_value=None)
    @patch.object(EnhancedMarketPricesService, "_try_alternative_government_sources", return_value=None)
    def test_ultra_government_api_does_not_promote_estimated_prices(
        self,
        _alternative,
        _fci,
        _enam,
        _agmarknet,
    ):
        result = UltraDynamicGovernmentAPI()._fetch_market_prices("Lucknow")

        self.assertIsNone(result)
