from unittest.mock import patch

from django.core.cache import cache
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from advisory.api.viewsets.auth_viewset import (
    _normalise_phone,
    _send_otp_sms,
)


class AuthOtpSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.phone_raw = "9876543210"
        self.phone = _normalise_phone(self.phone_raw)

    @override_settings(DEBUG=False)
    @patch.dict("os.environ", {
        "TWILIO_ACCOUNT_SID": "",
        "TWILIO_AUTH_TOKEN": "",
        "TWILIO_FROM_NUMBER": "",
    })
    def test_otp_is_not_logged_when_sms_fallback_runs_outside_debug(self):
        with patch("advisory.api.viewsets.auth_viewset.logger.info") as info_log:
            sent = _send_otp_sms(self.phone, "123456")

        self.assertFalse(sent)
        logged = " ".join(
            " ".join(str(part) for part in call.args)
            for call in info_log.call_args_list
        )
        self.assertNotIn("123456", logged)

    def test_otp_verify_rate_limits_repeated_wrong_codes(self):
        cache.set(f"otp:{self.phone}", "123456", timeout=600)

        for _ in range(5):
            response = self.client.post(
                "/api/users/otp/verify/",
                {"phone_number": self.phone_raw, "otp_code": "000000"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error_code"], "INVALID_OTP")

        blocked = self.client.post(
            "/api/users/otp/verify/",
            {"phone_number": self.phone_raw, "otp_code": "000000"},
            format="json",
        )

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error_code"], "OTP_VERIFY_RATE_LIMITED")

    def test_otp_limiters_use_configured_settings(self):
        from advisory.api.viewsets.auth_viewset import otp_rate_limiter, otp_verify_rate_limiter

        self.assertEqual(otp_rate_limiter.capacity, settings.OTP_REQUEST_CAPACITY)
        self.assertEqual(otp_rate_limiter.window_seconds, settings.OTP_REQUEST_WINDOW_SECONDS)
        self.assertEqual(otp_verify_rate_limiter.capacity, settings.OTP_VERIFY_CAPACITY)
        self.assertEqual(otp_verify_rate_limiter.window_seconds, settings.OTP_VERIFY_WINDOW_SECONDS)
