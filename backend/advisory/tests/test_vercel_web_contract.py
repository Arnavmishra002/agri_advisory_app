import json
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.test import RequestFactory, override_settings
from django.test import SimpleTestCase


class VercelWebContractTests(SimpleTestCase):
    def test_static_web_keeps_security_headers_and_private_api_cache(self):
        config = json.loads((Path(__file__).resolve().parents[3] / "frontend/vercel.json").read_text())
        self.assertEqual(config["framework"], "vite")
        self.assertEqual(config["outputDirectory"], "dist")
        rules = {rule["source"]: {header["key"]: header["value"] for header in rule["headers"]}
                 for rule in config["headers"]}
        headers = rules["/(.*)"]
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("object-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-eval", headers["Content-Security-Policy"])
        self.assertIn("geolocation=(self)", headers["Permissions-Policy"])
        self.assertEqual(rules["/api/:path(.*)"]["Cache-Control"], "private, no-store")
        route = config["routes"][0]
        self.assertEqual(route["dest"], "https://agri-advisory-web.onrender.com/api/$1")
        self.assertEqual(route["headers"]["Cache-Control"], "private, no-store")

    def test_api_proxy_preserves_django_trailing_slashes(self):
        config = json.loads((Path(__file__).resolve().parents[3] / "frontend/vercel.json").read_text())
        route = config["routes"][0]
        self.assertEqual(route["src"], "/api/(.*)")
        for path in ("/api/health/", "/api/weather/", "/api/chatbot/", "/api/health"):
            captured = re.fullmatch(route["src"], path).group(1)
            self.assertEqual(route["dest"].replace("$1", captured),
                             "https://agri-advisory-web.onrender.com" + path)
        self.assertNotIn("/api/:path(.*)", [rule["source"] for rule in config.get("rewrites", [])])

    def test_api_proxy_sends_edge_secret_from_environment(self):
        # Django trusts one more X-Forwarded-For hop only for requests carrying
        # ORIGIN_SECRET; the value must come from Vercel's environment, never
        # from this public file.
        config = json.loads((Path(__file__).resolve().parents[3] / "frontend/vercel.json").read_text())
        transform = config["routes"][0]["transforms"][0]
        self.assertEqual(transform["type"], "request.headers")
        self.assertEqual(transform["op"], "set")
        self.assertEqual(transform["target"]["key"], "x-origin-secret")
        self.assertEqual(transform["args"], "$ORIGIN_SECRET")
        self.assertEqual(transform["env"], ["ORIGIN_SECRET"])

    @override_settings(ALLOWED_HOSTS=["agri-advisory-web.onrender.com"])
    def test_proxy_does_not_trust_client_forwarded_host(self):
        self.assertFalse(settings.USE_X_FORWARDED_HOST)
        request = RequestFactory().get("/api/health/",
            HTTP_HOST="agri-advisory-web.onrender.com",
            HTTP_X_FORWARDED_HOST="untrusted.example")
        self.assertEqual(request.get_host(), "agri-advisory-web.onrender.com")
        request.META["HTTP_HOST"] = "untrusted.example"
        with self.assertRaises(DisallowedHost):
            request.get_host()
