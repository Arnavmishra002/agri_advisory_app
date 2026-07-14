from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from advisory.api.location_utils import resolve_request_location
from advisory.services.location_context import LocationContext


class LocationResolutionTests(TestCase):
    def test_explicit_unconfirmed_location_never_falls_back_to_delhi_or_ip(self):
        request = SimpleNamespace(
            query_params={},
            data={"location_confirmed": False},
        )

        with patch("advisory.api.location_utils.location_resolver.resolve") as resolver:
            ctx = resolve_request_location(request)

        resolver.assert_not_called()
        self.assertEqual(ctx.display_name, "")
        self.assertEqual(ctx.source, "unconfirmed")
        self.assertEqual(ctx.confidence, 0.0)

    def test_location_name_payload_is_used_as_text_location(self):
        request = SimpleNamespace(
            query_params={},
            data={"location_name": "Lucknow"},
        )
        expected = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Lucknow",
            district="Lucknow",
            state="Uttar Pradesh",
            source="text_search",
            confidence=0.9,
        )

        with patch("advisory.api.location_utils.location_resolver.resolve", return_value=expected) as resolver:
            ctx = resolve_request_location(request)

        resolver.assert_called_once_with(
            latitude=None,
            longitude=None,
            location_query="Lucknow",
            accuracy_meters=None,
        )
        self.assertEqual(ctx.display_name, "Lucknow")
        self.assertEqual(ctx.state, "Uttar Pradesh")
