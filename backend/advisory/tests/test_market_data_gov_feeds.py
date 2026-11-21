"""data.gov.in mandi feeds and the Agmarknet CAPTCHA refusal (21 Nov 2026).

Agmarknet began answering automated price requests with HTTP 400 and a
CAPTCHA demand, so on a deploy without DATA_GOV_IN_API_KEY the market screen
showed no prices at all. These tests pin how the data.gov.in feeds are queried
and how the refusal is handled.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from advisory.services import agmarknet_direct_client as direct_module
from advisory.services.agmarknet_client import AgmarknetClient
from advisory.services.agmarknet_direct_client import AgmarknetDirectClient
from advisory.services.data_gov_mandi_client import (
    DataGovMandiClient,
    ogd_state_spellings,
)
from advisory.services.market_data_quality import build_dated_official_reference
from advisory.services.unified_realtime_service import MarketPricesService

FAKE_KEY = "k" * 40
# 06:00 UTC is 11:30 IST on 21 Nov 2026, after the daily 09:00 IST release.
NOW = datetime(2026, 11, 21, 6, tzinfo=timezone.utc)


def _row(state, commodity="Wheat", price=2590, day="21/11/2026", market="Babrala APMC"):
    return {
        "state": state, "district": "Badaun", "market": market,
        "commodity": commodity, "variety": "Other", "grade": "FAQ",
        "arrival_date": day, "min_price": price - 50, "max_price": price + 50,
        "modal_price": price,
    }


def _history_row(state, commodity="Onion", price=3000, day="20/11/2026"):
    return {
        "State": state, "District": "Aligarh", "Market": "Aligarh APMC",
        "Commodity": commodity, "Variety": "Red", "Grade": "FAQ",
        "Arrival_Date": day, "Min_Price": price - 100, "Max_Price": price + 100,
        "Modal_Price": price,
    }


def _ok(records):
    resp = Mock(status_code=200)
    resp.json.return_value = {"records": records}
    return resp


class _FixedClock:
    """Pin "now" for the freshness checks and the history date walk."""

    def __enter__(self):
        self._patches = [
            patch("advisory.services.market_data_quality.datetime", wraps=datetime),
            patch("advisory.services.data_gov_mandi_client.datetime", wraps=datetime),
        ]
        for p in self._patches:
            mocked = p.start()
            mocked.now.return_value = NOW
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()


class DailyFeedStateMatchTests(SimpleTestCase):
    def test_daily_feed_uses_exact_state_filter_and_drops_other_states(self):
        client = DataGovMandiClient()
        calls = []

        def fake_get(url, params=None, timeout=None):
            calls.append(params)
            # What the full-text filter returned: other "Pradesh" states mixed in.
            return _ok([
                _row("Madhya Pradesh", "Soyabean", 4800),
                _row("Uttar Pradesh", "Wheat", 2590),
                _row("Andhra Pradesh", "Paddy", 2300),
            ])

        client._session.get = fake_get
        with _FixedClock():
            result = client._fetch_data_gov(FAKE_KEY, state="Uttar Pradesh")

        self.assertEqual(calls[0]["filters[state.keyword]"], "Uttar Pradesh")
        self.assertNotIn("filters[state]", calls[0])
        self.assertEqual([c["state"] for c in result["top_crops"]], ["Uttar Pradesh"])

    def test_each_crop_shows_the_middle_mandi_not_the_dearest(self):
        with _FixedClock():
            result = DataGovMandiClient()._format_datagov_response([
                _row("Uttar Pradesh", "Wheat", 2400, market="A APMC"),
                _row("Uttar Pradesh", "Wheat", 2600, market="B APMC"),
                _row("Uttar Pradesh", "Wheat", 3900, market="C APMC"),
            ], state="Uttar Pradesh")

        wheat = result["top_crops"][0]
        self.assertEqual((wheat["modal_price"], wheat["mandi_name"]), (2600, "B APMC"))
        self.assertEqual(wheat["mandis_reporting"], 3)

    def test_state_spellings_follow_the_feed(self):
        self.assertEqual(ogd_state_spellings("Chhattisgarh")[0], "Chattisgarh")
        self.assertEqual(ogd_state_spellings("Delhi"), ("NCT of Delhi",))
        self.assertEqual(ogd_state_spellings("Puducherry")[0], "Pondicherry")
        self.assertEqual(ogd_state_spellings(" Uttar  Pradesh "), ("Uttar Pradesh",))
        self.assertEqual(ogd_state_spellings(""), ())


class HistoryFeedTests(SimpleTestCase):
    def _client(self, daily, history):
        client = DataGovMandiClient()
        calls = []

        def fake_get(url, params=None, timeout=None):
            calls.append((url, dict(params)))
            if "35985678" in url:
                return history(params)
            return daily(params)

        client._session.get = fake_get
        return client, calls

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": FAKE_KEY})
    def test_history_supplies_latest_day_when_today_has_no_rows(self):
        client, calls = self._client(
            daily=lambda p: _ok([]),
            history=lambda p: _ok([_history_row("Uttar Pradesh", day=p["filters[Arrival_Date]"])])
            if p["filters[Arrival_Date]"] == "20/11/2026" else _ok([]),
        )
        with _FixedClock(), patch(
            "advisory.services.market_data_quality.max_market_age_hours", return_value=48.0
        ):
            result = client.get_national_prices(state="Uttar Pradesh", force_refresh=True)

        history_calls = [p for u, p in calls if "35985678" in u]
        self.assertEqual(history_calls[0]["filters[Arrival_Date]"], "20/11/2026")
        self.assertEqual(history_calls[0]["filters[State]"], "Uttar Pradesh")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["top_crops"][0]["reported_date"], "20/11/2026")
        self.assertIn("history", result["data_source"])

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": FAKE_KEY})
    def test_older_history_rows_come_back_as_a_dated_reference_not_live(self):
        client, _ = self._client(
            daily=lambda p: _ok([]),
            history=lambda p: _ok([_history_row("Uttar Pradesh", day=p["filters[Arrival_Date]"])]),
        )
        with _FixedClock(), patch(
            "advisory.services.agmarknet_scraper.agmarknet_scraper.fetch_records", return_value=[]
        ):
            result = client.get_national_prices(state="Uttar Pradesh", force_refresh=True)
            dated, _, reported = build_dated_official_reference(result["unfiltered_rows"])

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["top_crops"], [])
        self.assertEqual(reported, "20/11/2026")
        self.assertTrue(dated and all(r["is_live"] is False for r in dated))

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": FAKE_KEY})
    def test_a_failed_history_request_ends_the_search(self):
        client, calls = self._client(
            daily=lambda p: _ok([]),
            history=lambda p: Mock(status_code=503),
        )
        with _FixedClock():
            self.assertIsNone(client._fetch_data_gov_history(FAKE_KEY, state="Uttar Pradesh"))
        self.assertEqual(len([u for u, _ in calls if "35985678" in u]), 1)

    def test_history_rows_from_another_state_are_dropped(self):
        client, _ = self._client(
            daily=lambda p: _ok([]),
            history=lambda p: _ok([_history_row("Madhya Pradesh")]),
        )
        with _FixedClock():
            self.assertIsNone(client._fetch_data_gov_history(FAKE_KEY, state="Uttar Pradesh"))

    def test_request_failures_never_log_the_key(self):
        client = DataGovMandiClient()
        url_with_key = f"https://api.data.gov.in/resource/x?api-key={FAKE_KEY}"

        def boom(url, params=None, timeout=None):
            raise requests.exceptions.ConnectionError(f"Max retries exceeded with url: {url_with_key}")

        client._session.get = boom
        with self.assertLogs("advisory.services.data_gov_mandi_client", level="WARNING") as logs:
            self.assertIsNone(client._get_records("https://api.data.gov.in/resource/x", {"api-key": FAKE_KEY}, "daily feed"))
        self.assertNotIn(FAKE_KEY, "\n".join(logs.output))


class MarketServiceDatedReferenceTests(SimpleTestCase):
    @patch("advisory.services.agmarknet_filters.agmarknet_filters.resolve_location", return_value={})
    @patch("advisory.services.agmarknet_direct_client.agmarknet_direct_client.get_local_prices", return_value=None)
    @patch("advisory.services.agmarknet_client.agmarknet_client.get_market_prices", return_value=None)
    @patch("advisory.services.data_gov_mandi_client.data_gov_mandi_client.get_national_prices")
    def test_market_screen_gets_yesterdays_official_rows_with_their_date(self, national, *_):
        with _FixedClock():
            rows = DataGovMandiClient()._format_datagov_response(
                [_history_row("Uttar Pradesh")], state="Uttar Pradesh", is_live=True,
            )
            national.return_value = {
                "status": "unavailable", "is_live": False, "top_crops": [],
                "data_source": "data.gov.in Official API (Agmarknet daily price history)",
                "reported_date": rows["reported_date"],
                "unfiltered_rows": rows["unfiltered_rows"],
            }
            result = MarketPricesService().get_prices(
                "Lucknow", state="Uttar Pradesh", district="Lucknow"
            )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["top_crops"], [])
        self.assertTrue(result.get("has_dated_official_reference"))
        self.assertEqual(result["latest_official_reported_date"], "20/11/2026")
        self.assertIn("history", result["latest_official_source"])


class _CaptchaReset(SimpleTestCase):
    def setUp(self):
        direct_module._captcha_seen_at = None

    def tearDown(self):
        direct_module._captcha_seen_at = None


def _captcha_response():
    resp = Mock(status_code=400)
    resp.text = '{"status":false,"message":"Captcha key and captcha value are required."}'
    resp.json.return_value = {"status": False, "message": "Captcha key and captcha value are required."}
    return resp


class AgmarknetCaptchaTests(_CaptchaReset):
    def test_direct_client_stops_calling_after_a_captcha_refusal(self):
        client = AgmarknetDirectClient()
        post = Mock(return_value=_captcha_response())
        client.session.post = post

        self.assertIsNone(client._fetch_live())
        self.assertIsNone(client._fetch_live())

        self.assertEqual(post.call_count, 1)
        self.assertTrue(direct_module.captcha_wall_active())

    def test_dashboard_client_stops_calling_after_a_captcha_refusal(self):
        client = AgmarknetClient()
        post = Mock(return_value=_captcha_response())
        client.session.post = post

        self.assertIsNone(client._post_report({"dashboard": "x"}))
        self.assertIsNone(client._post_report({"dashboard": "x"}))

        self.assertEqual(post.call_count, 1)

    def test_an_ordinary_bad_request_is_not_taken_for_a_captcha(self):
        resp = Mock(status_code=400)
        resp.text = '{"status":false,"message":"Invalid date"}'
        self.assertFalse(direct_module.is_captcha_wall(resp))

    @patch.dict("os.environ", {"DATA_GOV_IN_API_KEY": ""})
    def test_operator_note_names_the_missing_key_when_agmarknet_wants_a_captcha(self):
        direct_module.note_captcha_wall()
        response = MarketPricesService()._unavailable_market_response(
            "Lucknow", None, None, state="Uttar Pradesh"
        )
        note = response["operator_note"]
        self.assertIn("CAPTCHA", note)
        self.assertIn("DATA_GOV_IN_API_KEY", note)
        # The farmer-facing message never names environment variables.
        self.assertNotIn("DATA_GOV_IN_API_KEY", response["message"])


class UnifiedDataGovStateFilterTests(SimpleTestCase):
    def test_full_text_state_matches_from_other_states_are_dropped(self):
        service = MarketPricesService()
        with patch.object(service, "_data_gov_request", side_effect=[
            [_row("Madhya Pradesh", "Soyabean", 4800), _row("Uttar Pradesh", "Wheat", 2590)],
        ]):
            result = service._fetch_data_gov(
                "Lucknow", None, None, "agmarknet_mandi", FAKE_KEY, state="Uttar Pradesh"
            )

        self.assertEqual({c["state"] for c in result["top_crops"]}, {"Uttar Pradesh"})
