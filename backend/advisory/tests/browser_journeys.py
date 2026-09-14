"""Explicit real-backend browser gate: run after frontend dependency install.

The SMS boundary is patched only inside this test process. No runtime setting,
OTP HTTP endpoint, production fixture or real message is introduced.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import LiveServerTestCase, override_settings

from advisory.models import FarmerProfile


@override_settings(ALLOWED_HOSTS=['localhost', '127.0.0.1', 'testserver'])
class FarmerBrowserJourneyTests(LiveServerTestCase):
    def test_otp_profile_refresh_logout_and_reuse(self):
        cache.clear()
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(prefix='km-test-sms-') as directory:
            capture = Path(directory) / 'otp.txt'

            def accept_sms(phone, code):
                self.assertEqual(phone, '+919000000099')
                capture.write_text(code)
                return True

            env = {**os.environ, 'VITE_API_BASE_URL': self.live_server_url,
                   'KM_TEST_OTP_CAPTURE': str(capture), 'KM_TEST_API_URL': self.live_server_url}
            with patch('advisory.api.viewsets.auth_viewset._send_otp_sms', side_effect=accept_sms):
                result = subprocess.run(
                    ['node', 'scripts/real-backend-journey.mjs'], cwd=root / 'frontend',
                    env=env, capture_output=True, text=True, timeout=180,
                )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(get_user_model().objects.filter(username__contains='9000000099').exists())
            profile = FarmerProfile.objects.get(phone_number='+919000000099')
            self.assertEqual(profile.current_crop, 'wheat')

