import time
from unittest.mock import Mock

from django.test import SimpleTestCase

from advisory.services.agmarknet_client import AgmarknetClient


class AgmarknetRateLimitTests(SimpleTestCase):
    def test_429_opens_cooldown_without_sleeping_or_retrying(self):
        client = AgmarknetClient()
        response = Mock(status_code=429, headers={"Retry-After": "60"})
        client.session.post = Mock(return_value=response)

        started = time.monotonic()
        self.assertIsNone(client._post_report({"state_id": 1}))
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.5)
        self.assertGreater(client._rate_limited_until, time.monotonic())
        self.assertIsNone(client._post_report({"state_id": 1}))
        client.session.post.assert_called_once()

    def test_retry_after_is_bounded(self):
        client = AgmarknetClient()
        response = Mock(status_code=429, headers={"Retry-After": "9999"})
        client.session.post = Mock(return_value=response)
        before = time.monotonic()

        client._post_report({})

        self.assertLessEqual(client._rate_limited_until - before, 301)
