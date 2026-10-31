"""Phone-number ownership: only an OTP-verified account owns a farmer's phone.

Regression tests for two account-takeover paths:
- a password account named after a farmer's number (``x9876543210``) read
  that farmer's profile;
- a password account registered under ``91XXXXXXXXXX`` before the farmer's
  first OTP login kept password access to the farmer's account.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache, caches
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from advisory.api.viewsets.auth_viewset import _normalise_phone
from advisory.models import FarmerProfile

User = get_user_model()
PHONE = "9876543210"


class PhoneOwnershipTests(TestCase):
    def setUp(self):
        cache.clear()
        caches["rate_limit"].clear()
        self.victim_profile = FarmerProfile.objects.create(
            phone_number="+919876543210",
            location_name="Private village",
            latitude=26.85,
            longitude=80.95,
        )

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _verify_otp(self, client, phone=PHONE):
        client.post("/api/users/otp/request/", {"phone_number": phone}, format="json")
        code = cache.get(f"otp:{_normalise_phone(phone)}")
        self.assertTrue(code, "no OTP was issued")
        return client.post(
            "/api/users/otp/verify/", {"phone_number": phone, "otp_code": code}, format="json"
        )

    def test_password_account_with_phone_digits_cannot_read_the_farmers_profile(self):
        squatter = User.objects.create_user(username="x9876543210", password="strong-pass-123")

        response = self._client_for(squatter).get("/api/farmer-profile/")

        self.assertEqual(response.status_code, 200, response.content[:200])
        self.assertFalse(response.data["exists"])

    def test_legacy_password_account_named_like_a_phone_owns_no_phone(self):
        squatter = User.objects.create_user(username="919876543210", password="strong-pass-123")

        response = self._client_for(squatter).get("/api/users/me/")

        self.assertEqual(response.status_code, 200, response.content[:200])
        self.assertNotEqual(response.data.get("profile", {}).get("location_name"), "Private village")

    def test_otp_account_reads_its_own_profile(self):
        owner = User.objects.create_user(username="919876543210")  # OTP accounts have no password

        response = self._client_for(owner).get("/api/farmer-profile/")

        self.assertTrue(response.data["exists"])

    def test_registration_rejects_usernames_containing_a_phone_number(self):
        for username in ("919876543210", "x9876543210", "farmer_9876543210"):
            response = APIClient().post(
                "/api/users/register/",
                {"username": username, "password": "strong-pass-123"},
                format="json",
            )
            self.assertEqual(response.status_code, 400, username)

    def test_registration_does_not_store_an_unverified_phone(self):
        response = APIClient().post(
            "/api/users/register/",
            {"username": "ramesh_farmer", "password": "strong-pass-123", "phone_number": PHONE},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="ramesh_farmer")
        own = FarmerProfile.objects.get(session_id=f"user:{user.id}")
        self.assertEqual(own.phone_number, "")
        self.assertEqual(response.data["user"]["phone"], "")

    def test_otp_login_takes_a_squatted_account_away_from_its_password(self):
        squatter = User.objects.create_user(username="919876543210", password="strong-pass-123")
        stolen_refresh = RefreshToken.for_user(squatter)

        stolen_access = str(stolen_refresh.access_token)

        verify = self._verify_otp(APIClient())

        self.assertEqual(verify.status_code, 200, verify.content[:300])
        squatter.refresh_from_db()
        self.assertFalse(squatter.has_usable_password())
        self.assertFalse(squatter.is_active)
        farmer = User.objects.get(username="919876543210")
        self.assertNotEqual(farmer.pk, squatter.pk)
        # The squatter's unexpired access token stops working immediately.
        with_old_access = APIClient()
        with_old_access.credentials(HTTP_AUTHORIZATION=f"Bearer {stolen_access}")
        self.assertEqual(with_old_access.get("/api/farmer-profile/").status_code, 401)
        password_login = APIClient().post(
            "/api/token/", {"username": "919876543210", "password": "strong-pass-123"}, format="json"
        )
        self.assertNotEqual(password_login.status_code, 200)
        refresh = APIClient().post("/api/token/refresh/", {"refresh": str(stolen_refresh)}, format="json")
        self.assertNotEqual(refresh.status_code, 200)

    def test_otp_login_strips_the_number_from_profiles_claimed_without_verification(self):
        squatter = User.objects.create_user(username="someone_else", password="strong-pass-123")
        claimed = FarmerProfile.objects.create(
            phone_number="+919876543210", session_id=f"user:{squatter.id}", location_name="Squatter farm"
        )

        verify = self._verify_otp(APIClient())

        self.assertEqual(verify.status_code, 200, verify.content[:300])
        claimed.refresh_from_db()
        self.assertEqual(claimed.phone_number, "")


class ReservedGuestSessionTests(TestCase):
    """A client-typed session id in an account namespace is never a guest session."""

    def test_no_guest_token_is_signed_for_account_or_channel_ids(self):
        from advisory.services.guest_session_service import (
            make_guest_session_token,
            verify_guest_session_token,
        )
        for session_id in ("user:2", "USER:2", "wa_919876543210"):
            self.assertEqual(make_guest_session_token(session_id), "")
            self.assertFalse(verify_guest_session_token(session_id, "anything"))
        self.assertTrue(make_guest_session_token("guest-abc"))

    def test_registration_cannot_adopt_an_account_profile_through_its_session_id(self):
        from django.core import signing
        victim = User.objects.create_user(username="ramesh_farmer", password="strong-pass-123")
        FarmerProfile.objects.create(session_id=f"user:{victim.id}", location_name="Ramesh secret farm")
        # Even a correctly signed token for the reserved id is refused.
        forged = signing.dumps({"session_id": f"user:{victim.id}"},
                               salt="krishimitra.guest-session.v1", compress=True)

        response = APIClient().post(
            "/api/users/register/",
            {"username": "attacker_one", "password": "strong-pass-123",
             "session_id": f"user:{victim.id}", "guest_session_token": forged},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data["guest_session_migrated"])
        self.assertTrue(FarmerProfile.objects.filter(
            session_id=f"user:{victim.id}", location_name="Ramesh secret farm").exists())


class DetachUnverifiedPhoneClaimsCommandTests(TestCase):
    def test_dry_run_reports_and_apply_detaches_only_unverified_claims(self):
        from io import StringIO

        from django.core.management import call_command

        password_user = User.objects.create_user(username="ramesh_farmer", password="strong-pass-123")
        otp_user = User.objects.create_user(username="919811111111")
        claimed = FarmerProfile.objects.create(session_id=f"user:{password_user.id}", phone_number="+919876543210")
        verified = FarmerProfile.objects.create(session_id=f"user:{otp_user.id}", phone_number="+919811111111")
        guest = FarmerProfile.objects.create(session_id="wa_919800000000", phone_number="+919800000000")

        out = StringIO()
        call_command("detach_unverified_phone_claims", stdout=out)
        self.assertIn("1 of 2", out.getvalue())
        claimed.refresh_from_db()
        self.assertEqual(claimed.phone_number, "+919876543210")

        call_command("detach_unverified_phone_claims", "--apply", stdout=StringIO())
        for profile in (claimed, verified, guest):
            profile.refresh_from_db()
        self.assertEqual(claimed.phone_number, "")
        self.assertEqual(verified.phone_number, "+919811111111")
        self.assertEqual(guest.phone_number, "+919800000000")


class ReservedChatSessionTests(TestCase):
    """The web chat cannot read or write a WhatsApp farmer's memory by naming their session."""

    def test_reserved_session_ids_are_dropped(self):
        from advisory.api.viewsets.chatbot import _client_session_id

        for value in ("wa_919876543210", "user:7", "  wa_9198  "):
            self.assertIsNone(_client_session_id(value))
        self.assertEqual(_client_session_id(" guest-abc "), "guest-abc")
