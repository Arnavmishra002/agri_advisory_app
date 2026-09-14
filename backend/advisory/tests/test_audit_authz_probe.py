"""AUDIT PROBE — authorization and data-exposure boundaries.

Created during the September 2026 audit. Isolated: read-only probes against the
test database, no production data, no network. Each test states the expected
behaviour it is asserting so a failure is a finding, not a mystery.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()

UNAUTH_MUST_REJECT = (
    "/api/farmer-profile/me/",
    "/api/farmer-profile/context/",
    "/api/users/me/",
)


class UnauthenticatedAccessTests(TestCase):
    """Endpoints holding personal data must reject anonymous callers."""

    def setUp(self):
        self.client = APIClient()

    def test_private_endpoints_reject_anonymous_callers(self):
        offenders = []
        for path in UNAUTH_MUST_REJECT:
            r = self.client.get(path)
            if r.status_code not in (401, 403):
                offenders.append((path, r.status_code, r.content[:200]))
        self.assertEqual(offenders, [], f"anonymous access allowed: {offenders}")


class CrossAccountAccessTests(TestCase):
    """One farmer must never read or modify another farmer's profile."""

    def setUp(self):
        self.alice = User.objects.create_user(username="+919000000001", password="audit-pw-alice-1")
        self.bob = User.objects.create_user(username="+919000000002", password="audit-pw-bob-2")
        self.client = APIClient()

    def _as(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_farmer_profile_me_returns_only_the_callers_own_record(self):
        a = self._as(self.alice).get("/api/farmer-profile/me/")
        b = self._as(self.bob).get("/api/farmer-profile/me/")
        self.assertIn(a.status_code, (200, 404), a.content[:200])
        self.assertIn(b.status_code, (200, 404), b.content[:200])
        if a.status_code == 200 and b.status_code == 200:
            self.assertNotEqual(
                a.json(), b.json(),
                "two different users received an identical profile payload",
            )

    def test_profile_list_is_scoped_to_the_caller(self):
        r = self._as(self.alice).get("/api/farmer-profile/")
        if r.status_code != 200:
            self.skipTest(f"list not available: HTTP {r.status_code}")
        body = r.json()
        rows = body.get("results", body) if isinstance(body, dict) else body
        if not isinstance(rows, list):
            return
        for row in rows:
            owner = row.get("user") or row.get("user_id") or row.get("username")
            if owner in (self.bob.id, self.bob.username):
                self.fail(f"alice can see bob's profile row: {row}")


class RateLimitResetExposureTests(TestCase):
    """/api/rate-limits/reset/ is registered AllowAny.

    If an anonymous caller can clear a limiter bucket, every limit the app
    relies on (OTP request, OTP verify, chat) becomes advisory only.
    """

    def test_anonymous_rate_limit_reset_is_not_permitted(self):
        c = APIClient()
        r = c.post("/api/rate-limits/reset/", {}, format="json")
        self.assertIn(
            r.status_code, (401, 403, 404, 405),
            f"anonymous limiter reset returned HTTP {r.status_code}: {r.content[:300]}",
        )


class MonitoringExposureTests(TestCase):
    """Monitoring endpoints are AllowAny; they must not leak internals."""

    # Only values, never variable names. An earlier version of this probe
    # matched the string "DATABASE_URL" and fired on the remediation hint
    # "Set DATABASE_URL to the managed PostgreSQL connection string." — a
    # name in advice is not a leak. Retracted rather than reported.
    LEAK_MARKERS = (
        "postgres://", "postgresql://", "redis://",
        "Traceback (most recent call last)", "/home/", "/sessions/",
    )

    def test_monitoring_endpoints_do_not_leak_secrets_or_paths(self):
        c = APIClient()
        offenders = []
        for path in ("/api/monitoring/health/", "/api/monitoring/metrics/",
                     "/api/monitoring/system_health/",
                     "/api/health/readiness/", "/api/health/launch-readiness/"):
            r = c.get(path)
            text = r.content.decode("utf-8", "replace")
            for marker in self.LEAK_MARKERS:
                if marker in text:
                    offenders.append((path, marker))
        self.assertEqual(offenders, [], f"internal detail exposed: {offenders}")
