from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from advisory.models import FarmerProfile


class FarmerProfileSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.owner = User.objects.create_user(username="919111111111", password="pass12345")
        self.other = User.objects.create_user(username="919222222222", password="pass12345")
        self.owner_profile = FarmerProfile.objects.create(
            phone_number="+919111111111",
            session_id="sess-owner",
            location_name="Lucknow",
            state="Uttar Pradesh",
            district="Lucknow",
            latitude=26.8467,
            longitude=80.9462,
            current_crop="wheat",
        )
        self.other_profile = FarmerProfile.objects.create(
            phone_number="+919222222222",
            session_id="sess-other",
            location_name="Jaipur",
            state="Rajasthan",
            district="Jaipur",
            latitude=26.9124,
            longitude=75.7873,
            current_crop="mustard",
        )

    def test_unauthenticated_query_param_access_is_rejected(self):
        response = self.client.get(
            "/api/farmer-profile/",
            {"phone": self.other_profile.phone_number},
        )

        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_user_cannot_fetch_or_mutate_another_profile_by_param(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            "/api/farmer-profile/",
            {"phone": self.other_profile.phone_number, "session_id": self.other_profile.session_id},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["profile"]
        self.assertEqual(data["location_name"], "Lucknow")
        self.assertNotEqual(data["location_name"], "Jaipur")
        self.assertNotIn("phone_number", data)
        self.assertNotIn("session_id", data)

        update = self.client.post(
            "/api/farmer-profile/",
            {
                "phone": self.other_profile.phone_number,
                "session_id": self.other_profile.session_id,
                "location_name": "Attacker Update",
                "current_crop": "rice",
            },
            format="json",
        )

        self.assertEqual(update.status_code, 200)
        self.owner_profile.refresh_from_db()
        self.other_profile.refresh_from_db()
        self.assertEqual(self.owner_profile.location_name, "Attacker Update")
        self.assertEqual(self.owner_profile.current_crop, "rice")
        self.assertEqual(self.other_profile.location_name, "Jaipur")
        self.assertEqual(self.other_profile.current_crop, "mustard")
