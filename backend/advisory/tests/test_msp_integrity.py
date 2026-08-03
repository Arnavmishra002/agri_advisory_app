from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from advisory.models import Crop
from advisory.services.agmarknet_direct_client import AgmarknetDirectClient
from advisory.services.comprehensive_crop_database import ALL_CROP_DATA
from advisory.services.msp_data import (
    MSP_CURRENT,
    MSP_MARKETING_SEASON,
    MSP_OFFICIAL_2026_27,
)


class MspProfileIntegrityTests(SimpleTestCase):
    def test_only_official_crops_have_msp_in_crop_profiles(self):
        profiles_with_msp = {
            crop_id
            for crop_id, profile in ALL_CROP_DATA.items()
            if profile.get("msp_per_quintal")
        }
        expected = set(MSP_OFFICIAL_2026_27).intersection(ALL_CROP_DATA)

        self.assertEqual(profiles_with_msp, expected)
        self.assertEqual(ALL_CROP_DATA["wheat"]["msp_per_quintal"], 2585)
        self.assertEqual(ALL_CROP_DATA["rice"]["msp_per_quintal"], 2441)
        self.assertEqual(ALL_CROP_DATA["rajma"]["msp_per_quintal"], 0)
        self.assertEqual(ALL_CROP_DATA["matar"]["msp_per_quintal"], 0)
        self.assertEqual(ALL_CROP_DATA["sugarcane"]["msp_per_quintal"], 0)

    def test_official_profiles_include_season_and_source(self):
        wheat = ALL_CROP_DATA["wheat"]

        self.assertEqual(wheat["msp_season"], MSP_MARKETING_SEASON)
        self.assertTrue(wheat["msp_source"].startswith("https://www.pib.gov.in/"))
        self.assertEqual(wheat["government_support"], "Central MSP")

    def test_common_aliases_resolve_to_same_current_price(self):
        self.assertEqual(MSP_CURRENT["arhar"], MSP_CURRENT["tur"])
        self.assertEqual(MSP_CURRENT["lentil"], MSP_CURRENT["masoor"])
        self.assertEqual(MSP_CURRENT["paddy"], MSP_CURRENT["rice"])

    def test_agmarknet_embedded_old_msp_never_overrides_current_table(self):
        response = AgmarknetDirectClient()._format_response(
            [
                {
                    "cmdt_name": "Maize",
                    "as_on_price": "1820",
                    "msp_price": "2400",
                    "reported_date": "16-07-2026",
                },
                {
                    "cmdt_name": "Onion",
                    "as_on_price": "1700",
                    "msp_price": "9999",
                    "reported_date": "16-07-2026",
                },
            ],
            "16-07-2026",
            is_live=False,
        )

        maize, onion = response["top_crops"]
        self.assertEqual(maize["msp"], 2410)
        self.assertIsNone(onion["msp"])


class SeedMspCommandTests(TestCase):
    @staticmethod
    def _create_crop(name, msp=0, season=""):
        return Crop.objects.create(
            name=name,
            description="test",
            ideal_soil_type="Loamy",
            min_temperature_c=10,
            max_temperature_c=40,
            min_rainfall_mm_per_month=20,
            max_rainfall_mm_per_month=200,
            duration_days=120,
            msp_per_quintal=msp,
            msp_season=season,
        )

    def test_dry_run_never_writes(self):
        self._create_crop("rajma", msp=5400, season="2024-25")
        before = list(Crop.objects.values_list("name", "msp_per_quintal", "msp_season"))

        call_command("seed_msp", "--dry-run", stdout=StringIO())

        after = list(Crop.objects.values_list("name", "msp_per_quintal", "msp_season"))
        self.assertEqual(after, before)

    def test_real_seed_updates_current_and_clears_obsolete_prices(self):
        self._create_crop("wheat", msp=2425, season="2024-25")
        self._create_crop("rajma", msp=5400, season="2024-25")

        call_command("seed_msp", stdout=StringIO())

        wheat = Crop.objects.get(name="wheat")
        rajma = Crop.objects.get(name="rajma")
        self.assertEqual(wheat.msp_per_quintal, 2585)
        self.assertEqual(wheat.msp_season, MSP_MARKETING_SEASON)
        self.assertEqual(rajma.msp_per_quintal, 0)
        self.assertEqual(rajma.msp_season, "")
