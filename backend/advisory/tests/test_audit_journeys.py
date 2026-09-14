"""AUDIT PROBE — end-to-end user journeys and input handling.

September 2026 audit. Each test asserts a behaviour a farmer depends on, and
checks resulting state rather than only the HTTP status. No network, no
production data.
"""
from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()
PHONE = "9000000011"


class OtpLoginJourneyTests(TestCase):
    """Request OTP -> verify -> receive JWT -> use it. Whole journey."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def _request_otp(self, phone=PHONE):
        return self.client.post("/api/users/otp/request/",
                                {"phone_number": phone}, format="json")

    @staticmethod
    def _issued_code(phone=PHONE):
        """Read the code the server just issued, straight from the cache.

        The public API cannot hand a test the code: `dev_otp` is returned only
        when settings.DEBUG is true, and Django's test runner forces DEBUG to
        False. Without this back door no test can drive a successful login at
        all -- which is why the journey had no end-to-end coverage.
        """
        from advisory.api.viewsets.auth_viewset import _normalise_phone
        return cache.get(f"otp:{_normalise_phone(phone)}")

    def test_otp_request_succeeds_and_reports_sms_delivery_state(self):
        r = self._request_otp()
        self.assertEqual(r.status_code, 200, r.content[:300])
        body = r.json()
        self.assertTrue(body.get("success"))
        self.assertIn("sms_sent", body,
                      "callers cannot tell whether the code was actually sent")

    def test_full_login_journey_creates_a_user_and_issues_usable_tokens(self):
        self._request_otp()
        otp = self._issued_code()
        self.assertTrue(otp, "no OTP was cached by the request endpoint")

        v = self.client.post("/api/users/otp/verify/",
                             {"phone_number": PHONE, "otp_code": otp}, format="json")
        self.assertEqual(v.status_code, 200, v.content[:300])
        tokens = v.json()
        self.assertIn("access", json.dumps(tokens), "no access token returned")

        # State check: the user actually exists now.
        self.assertTrue(
            User.objects.filter(username__contains=PHONE).exists(),
            "verify returned success but created no user",
        )

    def test_an_otp_cannot_be_used_twice(self):
        self._request_otp()
        otp = self._issued_code()
        first = self.client.post("/api/users/otp/verify/",
                                 {"phone_number": PHONE, "otp_code": otp}, format="json")
        self.assertEqual(first.status_code, 200, first.content[:200])
        second = self.client.post("/api/users/otp/verify/",
                                  {"phone_number": PHONE, "otp_code": otp}, format="json")
        self.assertNotEqual(
            second.status_code, 200,
            "a consumed OTP was accepted a second time",
        )

    def test_wrong_codes_are_locked_out_before_brute_force_succeeds(self):
        self._request_otp()
        statuses = []
        for _ in range(6):
            r = self.client.post("/api/users/otp/verify/",
                                 {"phone_number": PHONE, "otp_code": "000000"}, format="json")
            statuses.append(r.status_code)
        self.assertIn(429, statuses, f"no lockout after 6 wrong codes: {statuses}")

    def test_otp_requests_are_rate_limited_per_phone(self):
        statuses = [self._request_otp().status_code for _ in range(5)]
        self.assertIn(429, statuses, f"no request limit hit in 5 tries: {statuses}")


class ChatInputHandlingTests(TestCase):
    """The chat endpoint is public; its input handling is the attack surface."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def _post(self, payload):
        return self.client.post("/api/chatbot/query/", payload, format="json")

    def test_oversized_query_is_rejected_not_processed(self):
        r = self._post({"query": "क" * 5000, "language": "hi"})
        self.assertEqual(r.status_code, 400,
                         f"5000-char query returned HTTP {r.status_code}")

    def test_empty_and_whitespace_queries_are_rejected(self):
        for q in ("", "   ", "\n\t "):
            r = self._post({"query": q, "language": "hi"})
            self.assertEqual(r.status_code, 400,
                             f"query={q!r} returned HTTP {r.status_code}")

    def test_unknown_language_code_is_rejected(self):
        r = self._post({"query": "test", "language": "xx"})
        self.assertEqual(r.status_code, 400,
                         "an unsupported language code was accepted")

    def test_reflected_markup_is_served_as_inert_json(self):
        """The query is echoed verbatim. That is safe only while the response
        stays application/json with nosniff, and no client renders it as HTML.
        This test pins those two conditions rather than the echo itself."""
        r = self._post({"query": "<script>alert(1)</script>", "language": "hi"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/json", r.headers.get("Content-Type", ""))
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff",
                         "reflected input without nosniff invites sniffing attacks")

    def test_unknown_fields_are_rejected_by_the_strict_serializer(self):
        r = self._post({"query": "test", "language": "hi", "is_admin": True})
        self.assertEqual(r.status_code, 400,
                         "an unexpected field was silently accepted")


class MarketHonestyTests(TestCase):
    """With every upstream unreachable, the app must show nothing, not guesses."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_market_prices_never_invent_a_number_when_upstreams_fail(self):
        r = self.client.get("/api/market-prices/",
                            {"latitude": 26.8467, "longitude": 80.9462,
                             "location_confirmed": "true", "location_source": "gps"})
        self.assertIn(r.status_code, (200, 404, 503), r.content[:200])
        if r.status_code != 200:
            return
        body = r.json()
        rows = body.get("prices") or body.get("results") or body.get("data") or []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and row.get("modal_price"):
                self.assertIn(
                    row.get("freshness"), ("live", "dated_official", "cached"),
                    f"a price was returned with no freshness label: {row}",
                )
