from django.test import SimpleTestCase

from advisory.api.serializers import RegistrationInputSerializer


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
