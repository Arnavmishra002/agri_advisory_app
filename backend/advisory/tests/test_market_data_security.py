from unittest.mock import Mock, patch

from django.test import TestCase

from advisory.services.enhanced_market_prices import EnhancedMarketPricesService


class MarketDataSecurityTests(TestCase):
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

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": "test-key"})
    def test_data_gov_uses_env_api_key_when_configured(self):
        service = EnhancedMarketPricesService()
        called_urls = []

        def fake_get(url, **kwargs):
            called_urls.append(url)
            return Mock(status_code=500)

        service.session.get = fake_get

        service._fetch_from_data_gov_in("Lucknow", "Uttar Pradesh")

        self.assertTrue(any("api-key=test-key" in url for url in called_urls))

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
