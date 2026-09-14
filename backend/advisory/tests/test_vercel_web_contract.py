import json
from pathlib import Path

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
        self.assertEqual(rules["/api/:path*"]["Cache-Control"], "private, no-store")
        self.assertEqual(config["rewrites"][0]["destination"], "https://agri-advisory-web.onrender.com/api/:path*")
