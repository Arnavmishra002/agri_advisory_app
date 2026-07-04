from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from advisory.api.viewsets.chatbot import _load_farmer_context
from advisory.models import FarmerProfile


class ChatbotProfileSecurityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="919111111111", password="pass12345")
        self.other = User.objects.create_user(username="919222222222", password="pass12345")
        self.owner_profile = FarmerProfile.objects.create(
            phone_number="+919111111111",
            session_id="sess-owner",
            location_name="Lucknow",
            current_crop="wheat",
        )
        self.other_profile = FarmerProfile.objects.create(
            phone_number="+919222222222",
            session_id="sess-other",
            location_name="Jaipur",
            current_crop="mustard",
        )

    def test_anonymous_request_cannot_load_profile_by_phone(self):
        request = SimpleNamespace(
            data={"phone": self.other_profile.phone_number},
            user=AnonymousUser(),
        )

        context = _load_farmer_context(request, None, {})

        self.assertEqual(context, {})

    def test_authenticated_request_ignores_client_supplied_profile_identifiers(self):
        request = SimpleNamespace(
            data={"phone": self.other_profile.phone_number},
            user=self.owner,
        )

        context = _load_farmer_context(request, self.other_profile.session_id, {})

        self.assertEqual(context["location"], "Lucknow")
        self.assertEqual(context["current_crop"], "wheat")
        self.assertNotEqual(context["location"], "Jaipur")
        self.assertNotEqual(context["current_crop"], "mustard")
