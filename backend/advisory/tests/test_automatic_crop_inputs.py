from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from advisory.models import FarmerProfile
from advisory.api.viewsets.crop import automatic_crop_inputs


class AutomaticCropInputsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="autofarm")
        self.ctx = SimpleNamespace(latitude=26.85, longitude=80.95)
        self.profile = FarmerProfile.objects.create(
            session_id=f"user:{self.user.pk}", latitude=26.85, longitude=80.95,
            soil_type="loamy", soil_ph=6.8, irrigation_type="drip",
        )

    def test_matching_owned_field_reused_and_explicit_values_win(self):
        inputs, sources = automatic_crop_inputs(self.user, self.ctx, {"ph": 7.1})
        self.assertEqual(inputs, {"soil_type": "loamy", "irrigation": "drip", "ph": 7.1})
        self.assertEqual(sources["soil_type"], "saved_farmer_profile")
        self.assertEqual(sources["ph"], "request")

    def test_other_location_does_not_reuse_field_measurements(self):
        self.ctx.latitude = 19.07
        self.assertEqual(automatic_crop_inputs(self.user, self.ctx, {}), ({}, {}))

    def test_other_account_and_guest_cannot_reuse_profile(self):
        other = get_user_model().objects.create_user(username="otherfarm")
        for user in (other, SimpleNamespace(is_authenticated=False)):
            self.assertEqual(automatic_crop_inputs(user, self.ctx, {}), ({}, {}))

    def test_missing_coordinates_and_unknown_details_are_not_inferred(self):
        self.profile.latitude = None
        self.profile.save()
        self.assertEqual(automatic_crop_inputs(self.user, self.ctx, {}), ({}, {}))
