"""Regressions for two silent-failure bugs found in the pre-launch audit.

Both shared a shape: a value that looked configured but was not, producing no
error and no log line, only wrong advice.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.api_keys import env_key, env_setting, is_configured, is_real_key
from advisory.services.crop_recommendation_engine import (
    RAINFALL_TO_WATER_LEVEL,
    crop_recommendation_engine,
)


RICE = {
    "season": "kharif",
    "water_requirement": "High",       # -> minimum irrigation level "Medium"
    "soil_preference": ["Alluvial"],
    "rainfall_mm": 1200,
    "temperature_min": 20,
    "temperature_max": 38,
}


def _water(irrigation, rainfall_band, crop=RICE, season="kharif"):
    """Score one crop and return just the water factor."""
    _score, _reasons, breakdown = crop_recommendation_engine._score_single_crop(
        "rice", dict(crop), season, "Alluvial", rainfall_band,
        irrigation, [], "Indo-Gangetic", {"risk": "Unavailable"}, 28, {},
    )
    return breakdown["water"]


class RainfallBandMappingTests(SimpleTestCase):
    """The band table used to be read through a second, string-keyed lookup.

    The inner table yielded an int while the outer one was keyed by str, so the
    lookup never matched and every band silently resolved to the default.
    """

    def test_each_band_maps_to_a_distinct_water_level(self):
        self.assertEqual(RAINFALL_TO_WATER_LEVEL["Very Low"], 0)
        self.assertEqual(RAINFALL_TO_WATER_LEVEL["Medium"], 1)
        self.assertEqual(RAINFALL_TO_WATER_LEVEL["Very High"], 2)

    def test_bands_are_not_all_collapsed_to_one_value(self):
        self.assertGreater(len(set(RAINFALL_TO_WATER_LEVEL.values())), 1)


class StatedIrrigationAffectsScoringTests(SimpleTestCase):
    """A farmer's stated irrigation has to change the answer they get."""

    def test_rainfed_farmer_in_a_dry_district_is_warned_off_a_thirsty_crop(self):
        dry_rainfed = _water("Low", "Low")
        self.assertEqual(dry_rainfed["status"], "poor")
        self.assertLess(dry_rainfed["points"], 0)

    def test_irrigated_farmer_in_the_same_dry_district_is_not(self):
        self.assertEqual(_water("High", "Low")["status"], "ideal")

    def test_irrigation_level_changes_the_water_score(self):
        """The bug this covers: every irrigation level scored identically."""
        scores = {lvl: _water(lvl, "Low")["points"] for lvl in ("Low", "Medium", "High")}
        self.assertGreater(len(set(scores.values())), 1, scores)

    def test_monsoon_rain_supplements_but_never_replaces_irrigation(self):
        """Rain may lift the effective level by one step, not to fully irrigated."""
        rainfed_wet = _water("Low", "Very High")
        self.assertEqual(rainfed_wet["status"], "ideal")
        self.assertIn("rainfall", rainfed_wet["detail"])

    def test_rain_does_not_count_for_a_crop_grown_outside_the_monsoon(self):
        wheat = dict(RICE, season="rabi", water_requirement="Very High")
        rabi_rainfed = _water("Low", "Very High", crop=wheat, season="rabi")
        self.assertEqual(rabi_rainfed["status"], "poor")


class PlaceholderApiKeyTests(SimpleTestCase):
    """`.env.example` placeholders are non-empty, so bare truthiness accepts them."""

    def test_shipped_placeholders_are_not_treated_as_keys(self):
        for sample in (
            "your_groq_api_key_here",
            "your_gemini_api_key_here",
            "your_data_gov_in_api_key_here",
            "your_openweather_api_key_here",
            "change_me",
            "<paste key>",
            "",
        ):
            self.assertFalse(is_real_key(sample), sample)

    def test_real_keys_are_accepted_even_when_they_contain_common_words(self):
        # A random provider key can contain "test" or "demo" by chance; an
        # earlier substring rule would have silently disabled it.
        # Deliberately not shaped like any real provider key: GitHub push
        # protection flags credential-shaped test data, and it is right to.
        # What matters here is that "test" and "demo" appear as substrings.
        for sample in (
            "notarealkey-Test-0123456789abcdefghij",
            "notarealkey-demo-0123456789abcdefghij",
            "notarealkey-0123456789abcdef0123",
        ):
            self.assertTrue(is_real_key(sample), sample)

    @patch.dict("os.environ", {"GROQ_API_KEY": "your_groq_api_key_here"})
    def test_env_key_returns_empty_for_a_placeholder(self):
        self.assertEqual(env_key("GROQ_API_KEY"), "")

    @patch.dict("os.environ", {"GROQ_API_KEY": "notarealkey-0123456789abcdefghij"})
    def test_env_key_returns_a_real_key(self):
        self.assertEqual(env_key("GROQ_API_KEY"), "notarealkey-0123456789abcdefghij")

    def test_non_credential_settings_are_not_held_to_the_key_length_floor(self):
        # A Twilio sender number is short and legitimate.
        self.assertTrue(is_configured("+911234567890"))
        self.assertFalse(is_real_key("+911234567890"))

    @patch.dict("os.environ", {"TWILIO_FROM_NUMBER": "+911234567890"})
    def test_env_setting_accepts_a_sender_number(self):
        self.assertEqual(env_setting("TWILIO_FROM_NUMBER"), "+911234567890")
