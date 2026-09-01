"""A farmer's location must resolve onto Agmarknet's own filter IDs.

Without these IDs the price client can only ask for the national "All States"
aggregate. Measured against the live API on 2026-09-01, for the same commodity
and the same reported date, resolving one level further changed the answer:

    Uttar Pradesh average .... Wheat  2523.70
    Gautam Budh Nagar ........ Wheat  2541.83

The hard part is names, not IDs, and every case below is a real divergence
observed in the live payload rather than an invented one:

* Agmarknet spells states its own way -- "Keralam", "Chattisgarh",
  "NCT of Delhi", "Pondicherry" -- so a plain equality check silently drops
  those farmers to the national number.
* District names arrive from reverse geocoding: Nominatim returns
  "Gautam Buddha Nagar", Agmarknet stores "Gautam Budh Nagar".
* Market names differ by decoration: our registry says "Noida", Agmarknet
  says "Noida APMC"; ours says "Azadpur", theirs says "APMC Azadpur".

The registry is exercised against a fixture rather than the network so the
suite stays offline and deterministic.
"""

from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from advisory.services.agmarknet_filters import AgmarknetFilterRegistry

# Real rows copied from the live filter payload (2026-09-01).
FIXTURE = {
    "states": [[100006, "All States/UTs"], [34, "Uttar Pradesh"], [17, "Keralam"],
               [25, "NCT of Delhi"], [7, "Chattisgarh"], [27, "Pondicherry"]],
    "districts": [
        {"id": 100007, "district_name": "All Districts", "state_id": None},
        {"id": 614, "district_name": "Gautam Budh Nagar", "state_id": 34},
        {"id": 306, "district_name": "Ghaziabad", "state_id": 34},
        {"id": 317, "district_name": "Meerut", "state_id": 34},
        {"id": 900, "district_name": "Delhi", "state_id": 25},
    ],
    "markets": [
        {"id": 100009, "mkt_name": "All Markets", "district_id": None, "state_id": None},
        {"id": 1729, "mkt_name": "DADRI APMC", "district_id": 614, "state_id": 34},
        {"id": 2187, "mkt_name": "Dankaur APMC", "district_id": 614, "state_id": 34},
        {"id": 4814, "mkt_name": "Jewar APMC", "district_id": 614, "state_id": 34},
        {"id": 2803, "mkt_name": "Noida APMC", "district_id": 306, "state_id": 34},
        {"id": 3445, "mkt_name": "APMC Azadpur", "district_id": 900, "state_id": 25},
        {"id": 317, "mkt_name": "Meerut APMC", "district_id": 317, "state_id": 34},
    ],
    "commodities": [],
}


class AgmarknetFilterRegistryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.reg = AgmarknetFilterRegistry()
        self._patch = patch.object(AgmarknetFilterRegistry, "_fetch", return_value=FIXTURE)
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self.addCleanup(cache.clear)

    # ── states ────────────────────────────────────────────────────────────
    def test_plain_state_name_resolves(self):
        self.assertEqual(self.reg.resolve_state("Uttar Pradesh")[0], 34)

    def test_agmarknet_specific_state_spellings_resolve(self):
        """These four would each silently fall back to the national number."""
        for given, expected in [("Kerala", 17), ("Chhattisgarh", 7),
                                ("Delhi", 25), ("Puducherry", 27)]:
            with self.subTest(state=given):
                resolved = self.reg.resolve_state(given)
                self.assertIsNotNone(resolved, f"{given!r} did not resolve")
                self.assertEqual(resolved[0], expected)

    def test_unknown_state_returns_none_rather_than_a_guess(self):
        self.assertIsNone(self.reg.resolve_state("Atlantis"))
        self.assertIsNone(self.reg.resolve_state(""))

    # ── districts ─────────────────────────────────────────────────────────
    def test_geocoder_district_spelling_resolves(self):
        """Nominatim's 'Gautam Buddha Nagar' must find 'Gautam Budh Nagar'."""
        resolved = self.reg.resolve_district(34, "Gautam Buddha Nagar")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0], 614)

    def test_district_suffixes_are_ignored(self):
        self.assertEqual(self.reg.resolve_district(34, "Meerut District")[0], 317)

    def test_district_from_another_state_does_not_match(self):
        self.assertIsNone(self.reg.resolve_district(25, "Meerut"))

    # ── end-to-end scope resolution ───────────────────────────────────────
    def test_resolve_location_reports_the_tightest_scope(self):
        r = self.reg.resolve_location("Uttar Pradesh", "Gautam Buddha Nagar")
        self.assertEqual((r["state_id"], r["district_id"]), (34, 614))
        self.assertEqual(r["coverage"], "district")

    def test_unknown_district_degrades_to_state_not_to_nothing(self):
        r = self.reg.resolve_location("Uttar Pradesh", "Nowhere Nagar")
        self.assertEqual(r["state_id"], 34)
        self.assertIsNone(r["district_id"])
        self.assertEqual(r["coverage"], "state")

    def test_unknown_state_degrades_to_national(self):
        r = self.reg.resolve_location("Atlantis", "Nowhere")
        self.assertEqual(r["coverage"], "national")
        self.assertIsNone(r["state_id"])

    # ── linking our own geocoded mandi list to Agmarknet ids ──────────────
    def test_registry_mandi_names_link_to_agmarknet_markets(self):
        for ours, expected_id in [("Noida Sector 33 Mandi", 2803),
                                  ("Azadpur Mandi", 3445),
                                  ("Meerut Mandi", 317)]:
            with self.subTest(mandi=ours):
                linked = self.reg.link_market(ours)
                self.assertIsNotNone(linked, f"{ours!r} did not link")
                self.assertEqual(linked["market_id"], expected_id)

    def test_unlinkable_mandi_returns_none_rather_than_a_wrong_market(self):
        """A wrong link would quote another town's price as this mandi's."""
        self.assertIsNone(self.reg.link_market("Somewhere Nobody Mandi"))

    def test_markets_for_district_lists_only_that_district(self):
        markets = self.reg.markets_for(state_id=34, district_id=614)
        self.assertEqual(
            sorted(m["market_name"] for m in markets),
            ["DADRI APMC", "Dankaur APMC", "Jewar APMC"],
        )

    # ── degradation when the upstream filter call fails ───────────────────
    def test_state_resolution_still_works_with_no_network(self):
        """States are bundled, so a failed fetch must not lose state coverage."""
        with patch.object(AgmarknetFilterRegistry, "_fetch", return_value=None):
            reg = AgmarknetFilterRegistry()
            cache.clear()
            self.assertEqual(reg.resolve_state("Uttar Pradesh")[0], 34)
            self.assertIsNone(reg.resolve_district(34, "Gautam Buddha Nagar"))
            self.assertEqual(reg.resolve_location("Uttar Pradesh", "X")["coverage"], "state")

    def test_commodity_names_resolve_from_the_bundled_reference(self):
        for given, expected in [("wheat", 1), ("Maize", 4), ("mustard", 12),
                                ("tomato", 65), ("onion", 23), ("potato", 24)]:
            with self.subTest(crop=given):
                resolved = self.reg.resolve_commodity(given)
                self.assertIsNotNone(resolved, f"{given!r} did not resolve")
                self.assertEqual(resolved[0], expected)
