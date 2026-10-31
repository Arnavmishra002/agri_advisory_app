from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.core.cache import cache

from advisory.services.agmarknet_client import AgmarknetClient
from advisory.services.agmarknet_direct_client import AgmarknetDirectClient
from advisory.services.market_data_quality import filter_fresh_live_rows
from advisory.services.agmarknet_filters import AgmarknetFilterRegistry


class MandiProviderBoundariesTests(SimpleTestCase):
    def test_registry_failure_is_not_refetched_for_each_lookup(self):
        cache.clear()
        self.addCleanup(cache.clear)
        registry = AgmarknetFilterRegistry()
        with patch.object(registry, "_fetch", return_value=None) as fetch:
            self.assertIsNone(registry.load())
            self.assertIsNone(registry.load())
            self.assertEqual(fetch.call_count, 1)

    def test_undated_official_row_never_becomes_todays_price(self):
        rows = AgmarknetClient()._normalize_records(
            [{"cmdt_name": "Wheat", "as_on_price": 2400}], "Lucknow", "Uttar Pradesh", None,
        )
        self.assertFalse(rows[0]["date"])
        self.assertEqual(filter_fresh_live_rows(rows)[0], [])

    def test_direct_access_denial_stops_scope_expansion(self):
        client = AgmarknetDirectClient()
        denied = Mock(status_code=403, headers={})
        with patch.object(client.session, "post", return_value=denied) as post:
            result = client.fetch_scoped(state_id=34, district_id=658, market_id=1143)
            self.assertEqual(result["records"], [])
            self.assertEqual(post.call_count, 1)
            client._fetch_live()
            self.assertEqual(post.call_count, 1)

    def test_filter_denial_is_cooled_down(self):
        client = AgmarknetClient()
        with patch.object(client.session, "get", return_value=Mock(status_code=403, headers={})) as get:
            self.assertIsNone(client._get_filters())
            self.assertIsNone(client._get_filters())
            self.assertEqual(get.call_count, 1)

    def test_dashboard_request_uses_indian_calendar_day(self):
        client = AgmarknetDirectClient()
        response = Mock(status_code=200)
        response.json.return_value = {"status": "success", "data": {"records": []}}
        with patch("advisory.services.agmarknet_direct_client.datetime") as clock, \
                patch.object(client.session, "post", return_value=response) as post:
            instant = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)
            clock.now.side_effect = lambda tz=None: instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
            client._fetch_live()
        self.assertEqual(post.call_args.kwargs["json"]["date"], "2026-09-09")
