"""Rate-limit identity comes from proxy-appended X-Forwarded-For entries only.

With one trusted proxy the old code skipped the entry the proxy appended and
used the one the client wrote, so "X-Forwarded-For: 127.0.0.1" made a request
whitelisted (no stream limit at all), and ordinary clients all shared the
proxy's own address.
"""
from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.rate_limiters import client_ip_from_request, is_local_request


class ClientIpResolutionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, xff=None, remote="10.0.0.5", edge_secret=None):
        extra = {"REMOTE_ADDR": remote}
        if xff is not None:
            extra["HTTP_X_FORWARDED_FOR"] = xff
        if edge_secret is not None:
            extra["HTTP_X_ORIGIN_SECRET"] = edge_secret
        return self.factory.get("/api/chatbot/", **extra)

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=1)
    def test_one_proxy_uses_the_entry_it_appended(self):
        self.assertEqual(client_ip_from_request(self._request("203.0.113.9")), "203.0.113.9")
        # A client-written prefix is ignored.
        self.assertEqual(client_ip_from_request(self._request("127.0.0.1, 203.0.113.9")), "203.0.113.9")
        self.assertEqual(client_ip_from_request(self._request("1.2.3.4, 5.6.7.8, 203.0.113.9")), "203.0.113.9")

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=2)
    def test_two_proxies_use_the_second_entry_from_the_right(self):
        self.assertEqual(client_ip_from_request(self._request("127.0.0.1, 203.0.113.9, 198.51.100.7")),
                         "203.0.113.9")

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=1)
    def test_missing_or_invalid_header_falls_back_to_the_socket(self):
        self.assertEqual(client_ip_from_request(self._request()), "10.0.0.5")
        self.assertEqual(client_ip_from_request(self._request("not-an-ip")), "10.0.0.5")

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=0)
    def test_no_trusted_proxy_ignores_the_header(self):
        self.assertEqual(client_ip_from_request(self._request("203.0.113.9", remote="198.51.100.1")),
                         "198.51.100.1")

    @override_settings(RATE_LIMIT_WHITELIST=["127.0.0.1"])
    def test_whitelist_needs_a_genuinely_local_socket(self):
        self.assertTrue(is_local_request(self._request(remote="127.0.0.1")))
        self.assertFalse(is_local_request(self._request("127.0.0.1", remote="10.0.0.5")))
        self.assertFalse(is_local_request(self._request("127.0.0.1", remote="127.0.0.1")))

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=1, ORIGIN_SECRET="edge-test-secret-0123456789")
    def test_web_edge_hop_is_trusted_only_with_the_secret(self):
        # Through Vercel: Vercel writes the visitor, the API host appends Vercel.
        self.assertEqual(
            client_ip_from_request(self._request("49.36.10.1, 76.76.21.9", edge_secret="edge-test-secret-0123456789")),
            "49.36.10.1")
        self.assertEqual(
            client_ip_from_request(self._request("103.21.5.7, 76.76.21.9", edge_secret="edge-test-secret-0123456789")),
            "103.21.5.7")
        # A direct caller without the secret cannot claim the extra hop.
        self.assertEqual(client_ip_from_request(self._request("127.0.0.1, 203.0.113.9")), "203.0.113.9")
        self.assertEqual(
            client_ip_from_request(self._request("127.0.0.1, 203.0.113.9", edge_secret="guess")),
            "203.0.113.9")
        # An unexpanded Vercel variable (ORIGIN_SECRET missing there) is not the secret.
        self.assertEqual(
            client_ip_from_request(self._request("49.36.10.1, 76.76.21.9", edge_secret="$ORIGIN_SECRET")),
            "76.76.21.9")

    @override_settings(RATE_LIMIT_TRUSTED_PROXIES=1, ORIGIN_SECRET="")
    def test_no_configured_secret_never_trusts_the_extra_hop(self):
        self.assertEqual(client_ip_from_request(self._request("127.0.0.1, 203.0.113.9", edge_secret="")),
                         "203.0.113.9")
