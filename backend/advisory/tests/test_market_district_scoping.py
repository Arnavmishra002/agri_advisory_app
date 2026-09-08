"""A farmer's price should come from their own district, not a national mean.

Agmarknet accepts state/district/market ids, but this app only ever sent the
national "All States" aggregate. Measured against the live API on 2026-09-01,
for the same commodity and the same reported date:

    Uttar Pradesh average .... Wheat 2523.70
    Gautam Budh Nagar ........ Wheat 2541.83

Individual mandis are sparse -- DADRI APMC answered with one Maize row and no
price at all -- so the client escalates market -> district -> state -> national
and reports which scope actually answered. These tests pin the three
properties that make that safe:

* a scope with no usable price is not treated as an answer;
* the coverage label always says how local the number really is, so a district
  average is never rendered as the selected mandi's own quote;
* the price cache is keyed by district, or two farmers in the same state would
  be served each other's numbers.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.agmarknet_direct_client import AgmarknetDirectClient


TODAY = date.today().strftime("%d-%m-%Y")


def _row(name="Wheat", price="2541.83", date=TODAY):
    return {
        "cmdt_name": name,
        "as_on_price": price,
        "msp_price": "2425.00",
        "trend": "up",
        "cmdt_grp_name": "Cereals",
        "reported_date": date,
    }


class ScopedPriceLookupTests(SimpleTestCase):
    def setUp(self):
        self.client = AgmarknetDirectClient()

    def test_district_rows_are_returned_and_labelled_district(self):
        with patch.object(
            AgmarknetDirectClient, "fetch_scoped",
            return_value={"records": [_row()], "coverage": "district",
                          "reported_date": TODAY, "scope": {}},
        ):
            data = self.client.get_local_prices(state_id=34, district_id=614)
        self.assertIsNotNone(data)
        self.assertEqual(data["coverage"], "district")
        self.assertTrue(data["top_crops"])

    def test_no_priced_row_anywhere_returns_none_not_an_empty_answer(self):
        """A silent empty result must not look like a successful lookup."""
        with patch.object(
            AgmarknetDirectClient, "fetch_scoped",
            return_value={"records": [], "coverage": None,
                          "reported_date": None, "scope": None},
        ):
            self.assertIsNone(self.client.get_local_prices(state_id=34, district_id=614))

    def test_coverage_label_follows_the_scope_that_actually_answered(self):
        """Escalating to the state average must not keep saying 'district'."""
        for coverage in ("market", "district", "state", "national"):
            with self.subTest(coverage=coverage):
                with patch.object(
                    AgmarknetDirectClient, "fetch_scoped",
                    return_value={"records": [_row()], "coverage": coverage,
                                  "reported_date": TODAY, "scope": {}},
                ):
                    data = self.client.get_local_prices(state_id=34, district_id=614)
                self.assertEqual(data["coverage"], coverage)

    def test_a_district_price_is_not_labelled_as_a_national_average(self):
        """The row labels must name the place the number actually describes.

        _format_response hardcoded "National Average (Agmarknet)" and
        "All India" because national was the only scope this client ever
        queried. Reusing it for a district lookup silently stamped a Gautam
        Budh Nagar figure as a national one -- a price screen misstating where
        its number came from is exactly the failure this codebase guards.
        """
        with patch.object(
            AgmarknetDirectClient, "fetch_scoped",
            return_value={"records": [_row()], "coverage": "district",
                          "reported_date": TODAY, "scope": {}},
        ):
            data = self.client.get_local_prices(
                state_id=34, district_id=614,
                coverage_label="Gautam Budh Nagar (district average, Agmarknet)",
                state_label="Uttar Pradesh",
            )
        row = data["top_crops"][0]
        self.assertIn("Gautam Budh Nagar", row["mandi_name"])
        self.assertEqual(row["state"], "Uttar Pradesh")
        self.assertNotIn("National Average", row["mandi_name"])
        self.assertNotEqual(row["state"], "All India")

    def test_unscoped_calls_keep_the_national_labels(self):
        """The default path must be unchanged for callers that pass no labels."""
        with patch.object(
            AgmarknetDirectClient, "fetch_scoped",
            return_value={"records": [_row()], "coverage": "national",
                          "reported_date": TODAY, "scope": {}},
        ):
            data = self.client.get_local_prices(state_id=None)
        row = data["top_crops"][0]
        self.assertEqual(row["mandi_name"], "National Average (Agmarknet)")
        self.assertEqual(row["state"], "All India")

    def test_seed_rows_are_never_used_by_this_path(self):
        """The 12-06-2026 static rows must not leak in as a 'local' price."""
        with patch.object(
            AgmarknetDirectClient, "fetch_scoped",
            return_value={"records": [], "coverage": None,
                          "reported_date": None, "scope": None},
        ):
            self.assertIsNone(self.client.get_local_prices(state_id=34))


class ScopedEscalationTests(SimpleTestCase):
    """fetch_scoped must skip scopes whose rows carry no usable price."""

    def setUp(self):
        self.client = AgmarknetDirectClient()

    def _reply(self, records):
        class R:
            status_code = 200
            def raise_for_status(self): return None
            def json(self_inner):
                return {"status": "success",
                        "data": {"records": records},
                        "pagination": {"total_count": len(records)}}
        return R()

    def test_a_null_priced_row_does_not_stop_the_escalation(self):
        """DADRI APMC really does answer with a priceless Maize row."""
        calls = []

        def fake_post(url, json=None, timeout=None):
            calls.append(json)
            # market scope: a row with no price; district scope: a real price
            if json["market"] != [100009]:
                return self._reply([{"cmdt_name": "Maize", "as_on_price": None,
                                     "reported_date": TODAY}])
            return self._reply([_row()])

        with patch.object(self.client.session, "post", side_effect=fake_post):
            out = self.client.fetch_scoped(state_id=34, district_id=614, market_id=1729)

        self.assertEqual(out["coverage"], "district")
        self.assertEqual(len(out["records"]), 1)
        self.assertEqual(out["records"][0]["cmdt_name"], "Wheat")
        self.assertGreaterEqual(len(calls), 2, "should have tried market before district")

    def test_all_scopes_empty_yields_no_records(self):
        with patch.object(self.client.session, "post",
                          side_effect=lambda *a, **k: self._reply([])):
            out = self.client.fetch_scoped(state_id=34, district_id=614)
        self.assertEqual(out["records"], [])
        self.assertIsNone(out["coverage"])


class PriceCacheIsolationTests(SimpleTestCase):
    """Two districts in one state must not share a cached price."""

    def test_cache_key_separates_districts(self):
        from collections import OrderedDict

        from advisory.services.unified_realtime_service import MarketPricesService

        svc = MarketPricesService()
        cache = OrderedDict()
        keys = []
        with patch.object(MarketPricesService, "_validated_live_data",
                          side_effect=lambda d: None), \
             patch.object(svc, "_cache", cache):
            for district in ("Gautam Budh Nagar", "Meerut"):
                cache.clear()
                svc.get_prices("Noida", state="Uttar Pradesh", district=district)
                keys.extend(cache.keys())

        self.assertGreaterEqual(len(keys), 2, "no cache entries were written")
        self.assertEqual(
            len(set(keys)), len(keys),
            f"two districts collided on one cache key: {keys}",
        )


class DatedOfficialReferenceSurvivesLiveFilterTests(SimpleTestCase):
    """The 24-hour live gate used to consume the rows the 7-day path needed.

    Agmarknet resumed publishing on 2026-09-08 after being frozen since 30-08,
    serving 23 commodities dated 06-09-2026 -- every row priced, two days old,
    well inside the seven-day reference window. Farmers still saw an empty
    market screen: `_format_response` ran `filter_fresh_live_rows` first and
    handed the caller the emptied list, so `build_dated_official_reference`
    had nothing left to offer.
    """

    RECORDS = [
        {"cmdt_name": "Wheat", "msp_price": "2585.00", "as_on_price": "2536.24",
         "as_on_arrival": "13730.68", "cmdt_grp_name": "Cereals",
         "reported_date": "06-09-2026", "trend": "down"},
        {"cmdt_name": "Onion", "msp_price": None, "as_on_price": "3565.33",
         "as_on_arrival": "3539.88", "cmdt_grp_name": "Vegetables",
         "reported_date": "06-09-2026", "trend": None},
    ]

    def _formatted(self):
        from advisory.services.agmarknet_direct_client import AgmarknetDirectClient
        return AgmarknetDirectClient()._format_response(
            self.RECORDS, "06-09-2026", is_live=True
        )

    def test_two_day_old_rows_are_never_presented_as_live(self):
        out = self._formatted()
        self.assertEqual(out["top_crops"], [])

    def test_the_rows_survive_for_the_dated_official_path(self):
        out = self._formatted()
        self.assertEqual(len(out["unfiltered_rows"]), 2)

    def test_a_dated_official_reference_is_built_from_them(self):
        from advisory.services.market_data_quality import build_dated_official_reference

        out = self._formatted()
        rows, _age, reported = build_dated_official_reference(
            out["unfiltered_rows"], response_date="06-09-2026"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(reported, "06-09-2026")
        for row in rows:
            self.assertEqual(row["freshness"], "dated_official")
            self.assertFalse(row["is_live"], "a dated reference must not claim to be live")
