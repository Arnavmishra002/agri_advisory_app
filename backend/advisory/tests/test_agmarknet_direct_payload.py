from unittest.mock import Mock

from django.test import SimpleTestCase

from advisory.services.agmarknet_direct_client import AgmarknetDirectClient


class AgmarknetDirectPayloadTests(SimpleTestCase):
    def test_national_dashboard_uses_official_all_selector_contract(self):
        client = AgmarknetDirectClient()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "success",
            "data": {
                "records": [{
                    "cmdt_name": "Wheat",
                    "as_on_price": "2577.54",
                    "reported_date": "27-07-2026",
                }]
            },
        }
        client.session.post = Mock(return_value=response)

        records = client._fetch_live()

        self.assertEqual(len(records), 1)
        payload = client.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["dashboard"], "marketwise_price_arrival")
        self.assertEqual(payload["group"], [100000])
        self.assertEqual(payload["commodity"], [100001])
        self.assertEqual(payload["state"], 100006)
        self.assertEqual(payload["district"], [100007])
        self.assertEqual(payload["market"], [100009])
        self.assertEqual(payload["variety"], 100021)
        self.assertEqual(payload["grades"], [4])
        self.assertEqual(payload["format"], "json")
        self.assertEqual(payload["limit"], 100)
