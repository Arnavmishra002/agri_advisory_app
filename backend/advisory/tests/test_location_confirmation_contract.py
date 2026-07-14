from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.location_context import LocationResolver


class LocationConfirmationContractTests(SimpleTestCase):
    def test_missing_location_never_uses_ip_or_delhi(self):
        resolver = LocationResolver()
        with patch.object(resolver, "_resolve_ip") as ip_lookup:
            result = resolver.resolve(use_ip_fallback=True)

        ip_lookup.assert_not_called()
        self.assertEqual(result.source, "unconfirmed")
        self.assertIsNone(result.latitude)
        self.assertIsNone(result.longitude)
        self.assertNotEqual(result.display_name, "Delhi")

    def test_unresolved_manual_place_keeps_name_without_fake_coordinates(self):
        resolver = LocationResolver()
        with patch.object(
            resolver, "_resolve_known_place", return_value=None
        ), patch.object(resolver, "_resolve_text", return_value=None):
            result = resolver.resolve(location_query="My Village")

        self.assertEqual(result.source, "text_query_ungeocoded")
        self.assertEqual(result.display_name, "My Village")
        self.assertIsNone(result.latitude)
        self.assertIsNone(result.longitude)
