from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.agmarknet_client import AgmarknetClient


class AgmarknetDashboardClientTests(SimpleTestCase):
    def setUp(self):
        self.client = AgmarknetClient()
        self.filters = {
            "state_data": [{"state_id": 34, "state_name": "Uttar Pradesh"}],
            "cmdt_data": [{"cmdt_id": 1, "cmdt_name": "Wheat"}],
            "market_data": [{
                "id": 1143,
                "mkt_name": "Unnao APMC",
                "state_id": 34,
                "district_id": 658,
            }],
        }

    @patch.object(AgmarknetClient, "_post_report")
    @patch.object(AgmarknetClient, "_get_filters")
    def test_current_dashboard_contract_uses_state_district_market_and_commodity_ids(
        self, get_filters, post_report
    ):
        get_filters.return_value = self.filters
        post_report.side_effect = [
            {
                "status": "success",
                "data": {"records": [{
                    "cmdt_name": "Wheat",
                    "as_on_price": "2475.00",
                    "reported_date": "11-07-2026",
                }]},
            },
            {
                "status": "success",
                "data": {"records": [{
                    "cmdt_name": "Wheat",
                    "as_on": "2490.00",
                    "msp_price": "2585.00",
                    "market_name": "Unnao APMC",
                    "district_name": "Unnao",
                    "reported_date": "11-07-2026",
                }]},
            },
        ]

        result = self.client.get_market_prices(
            "Unnao",
            mandi="Unnao Mandi",
            crop="Wheat",
            state="Uttar Pradesh",
        )

        latest_state_payload = post_report.call_args_list[0].args[0]
        self.assertEqual(latest_state_payload["dashboard"], "marketwise_price_arrival")
        self.assertEqual(latest_state_payload["state"], 34)
        self.assertNotIn("market", latest_state_payload)

        payload = post_report.call_args_list[1].args[0]
        self.assertEqual(payload["dashboard"], "cumm_data_sp")
        self.assertEqual(payload["state"], [34])
        self.assertEqual(payload["district"], [658])
        self.assertEqual(payload["market"], [1143])
        self.assertEqual(payload["commodity"], [1])
        self.assertEqual(payload["date"], "2026-07-11")
        self.assertNotIn("from_date", payload)
        self.assertNotIn("to_date", payload)
        self.assertEqual(result["coverage"], "market")
        self.assertEqual(result["top_crops"][0]["mandi_name"], "Unnao APMC")
        self.assertEqual(result["top_crops"][0]["modal_price"], 2490.0)

    def test_dashboard_average_does_not_invent_minimum_or_maximum_prices(self):
        rows = self.client._normalize_records(
            [{
                "cmdt_name": "Maize",
                "as_on_price": "1820.00",
                "msp_price": "2400.00",
                "reported_date": "11-07-2026",
            }],
            location="Unnao",
            state="Uttar Pradesh",
            mandi=None,
        )

        self.assertEqual(rows[0]["modal_price"], 1820.0)
        self.assertIsNone(rows[0]["min_price"])
        self.assertIsNone(rows[0]["max_price"])
        self.assertEqual(rows[0]["price_source"], "agmarknet_state_average")
        self.assertEqual(rows[0]["reported_date"], "11-07-2026")

    def test_generic_mandi_name_resolves_unique_official_qualified_market(self):
        filters = {
            "market_data": [{
                "id": 315,
                "mkt_name": "Kanpur(Grain) APMC",
                "state_id": 34,
                "district_id": 637,
            }],
        }

        self.assertEqual(
            self.client._resolve_market("Kanpur Mandi", 34, filters),
            (315, 637),
        )

    def test_generic_mandi_name_does_not_guess_between_official_markets(self):
        filters = {
            "market_data": [
                {
                    "id": 315,
                    "mkt_name": "Kanpur(Grain) APMC",
                    "state_id": 34,
                    "district_id": 637,
                },
                {
                    "id": 316,
                    "mkt_name": "Kanpur(Vegetable) APMC",
                    "state_id": 34,
                    "district_id": 637,
                },
            ],
        }

        self.assertIsNone(self.client._resolve_market("Kanpur Mandi", 34, filters))
