from django.test import SimpleTestCase
from rest_framework.test import APIClient

from advisory.services.unified_realtime_service import GOVERNMENT_SCHEMES


class SchemeEligibilityTruthfulnessTests(SimpleTestCase):
    def test_pm_kusum_catalog_does_not_call_bank_finance_a_subsidy(self):
        scheme = next(item for item in GOVERNMENT_SCHEMES if item["id"] == "pm-kusum")

        self.assertNotIn("90% subsidy", scheme["benefit"])
        self.assertNotIn("90% सब्सिडी", scheme["benefit_hindi"])
        self.assertIn("bank finance", scheme["benefit"])
        self.assertIn("बैंक ऋण", scheme["benefit_hindi"])

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
