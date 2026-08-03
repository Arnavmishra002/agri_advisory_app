from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from advisory.api.serializers import RegistrationInputSerializer
from advisory.models import FarmerProfile
from advisory.services.guest_session_service import make_guest_session_token


class RegistrationContractTests(SimpleTestCase):
    def test_registration_accepts_supported_regional_language(self):
        serializer = RegistrationInputSerializer(
            data={
                "username": "marathi_farmer",
                "password": "strong-pass-123",
                "language": "mr",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["language"], "mr")

    def test_registration_rejects_unknown_language(self):
        serializer = RegistrationInputSerializer(
            data={
                "username": "test_farmer",
                "password": "strong-pass-123",
                "language": "made-up",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("language", serializer.errors)


class GuestRegistrationMigrationTests(TestCase):
    def test_classic_registration_preserves_owned_guest_profile(self):
        FarmerProfile.objects.create(
            session_id="guest-session-42",
            location_name="Barabanki",
            state="Uttar Pradesh",
            current_crop="Wheat",
        )
        client = APIClient()

        registration = client.post(
            "/api/users/register/",
            {
                "username": "guest_farmer_42",
                "password": "strong-pass-123",
                "session_id": "guest-session-42",
                "guest_session_token": make_guest_session_token("guest-session-42"),
            },
            format="json",
        )
        self.assertEqual(registration.status_code, 201, registration.data)
        self.assertTrue(registration.data["guest_session_migrated"])

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {registration.data['access']}")
        profile = client.get("/api/users/me/")

        self.assertEqual(profile.status_code, 200, profile.data)
        self.assertEqual(profile.data["profile"]["location_name"], "Barabanki")
        self.assertEqual(profile.data["profile"]["current_crop"], "Wheat")

    def test_unsigned_session_id_cannot_claim_another_guest_profile(self):
        original = FarmerProfile.objects.create(
            session_id="another-guests-session",
            location_name="Private village",
        )
        client = APIClient()

        registration = client.post(
            "/api/users/register/",
            {
                "username": "untrusted_claim",
                "password": "strong-pass-123",
                "session_id": "another-guests-session",
            },
            format="json",
        )

        self.assertEqual(registration.status_code, 201, registration.data)
        original.refresh_from_db()
        self.assertEqual(original.session_id, "another-guests-session")
