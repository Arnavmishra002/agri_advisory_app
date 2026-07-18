from django.test import SimpleTestCase
from rest_framework.test import APIClient


class SchemeEligibilityTruthfulnessTests(SimpleTestCase):
    def test_endpoint_does_not_claim_every_farmer_is_eligible(self):
        response = APIClient().post(
            "/api/schemes/eligibility/",
            {"farmer_profile": {"state": "Uttar Pradesh", "crop": "wheat"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["eligibility_confirmed"])
        self.assertEqual(response.data["candidate_schemes"], response.data["eligible_schemes"])
        self.assertTrue(response.data["candidate_schemes"])
        self.assertTrue(all(scheme["eligible"] is None for scheme in response.data["candidate_schemes"]))
        self.assertTrue(
            all(
                scheme["eligibility_status"] == "needs_official_verification"
                for scheme in response.data["candidate_schemes"]
            )
        )
