"""Senior-QA sweep over the current code, run through Django's test client."""
import json
from unittest.mock import patch
from django.test import TestCase, Client


class QASweep(TestCase):
    def setUp(self):
        self.c = Client()
        self.results = []

    # ── farmer services answer or refuse, never fabricate ────────────────
    def test_every_farmer_service_answers_or_refuses(self):
        for name, url in [
            ("weather",  "/api/weather/current/?lat=28.61&lon=77.20"),
            ("market",   "/api/market-prices/?lat=28.61&lon=77.20"),
            ("schemes",  "/api/schemes/"),
            ("crops",    "/api/crops/?lat=28.61&lon=77.20"),
        ]:
            r = self.c.get(url)
            self.assertIn(r.status_code, (200, 400), f"{name} -> {r.status_code}")

    def test_no_endpoint_leaks_a_traceback(self):
        for url in ["/api/weather/current/?lat=abc&lon=xyz",
                    "/api/market-prices/?lat=&lon=",
                    "/api/crops/",
                    "/api/does-not-exist/"]:
            r = self.c.get(url)
            body = r.content.decode("utf-8", "replace")
            for leak in ("Traceback", "File \"/", "django.db", "SECRET_KEY"):
                self.assertNotIn(leak, body, f"{url} leaked {leak!r}")

    def test_private_endpoints_are_gated(self):
        for url in ["/api/users/me/"]:
            r = self.c.get(url)
            self.assertIn(r.status_code, (401, 403), f"{url} -> {r.status_code}")

    # ── headers that hold in every environment ───────────────────────────
    def test_responses_are_not_sniffable(self):
        """Asserted here because it holds regardless of DEBUG.

        The production-only headers -- DENY, the enforcing CSP,
        Permissions-Policy -- are computed inside `if not DEBUG:` and cannot be
        checked against ambient settings: CI runs every job with DEBUG="True",
        so an earlier version of this asserted DENY and failed there while
        passing locally. ProductionSecurityHeaderTests loads settings with
        DEBUG=False in a subprocess and covers those properly.
        """
        r = self.c.get("/api/schemes/")
        self.assertEqual(r.get("X-Content-Type-Options"), "nosniff")
        self.assertIn(r.get("X-Frame-Options"), ("DENY", "SAMEORIGIN"))

    def test_reflected_input_is_json_not_html(self):
        r = self.c.get("/api/locations/search/?q=<script>alert(1)</script>")
        if r.status_code == 200:
            self.assertTrue(r["Content-Type"].startswith("application/json"))
            self.assertEqual(r.get("X-Content-Type-Options"), "nosniff")
