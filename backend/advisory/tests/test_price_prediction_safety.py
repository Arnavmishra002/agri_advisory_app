"""Guards against fabricated price/yield predictions reaching farmers.

These tests originally exercised ``ComprehensiveCropRecommendations`` and
asserted that its forecast helpers returned "unvalidated" placeholders rather
than invented numbers.  That module has since been removed outright: it was a
~2,300-line parallel engine with no importers that generated random suitability
scores and "Simulated" market rows.  Deleting it is a stronger guarantee than
the assertions that used to police it, so the tests now verify the guarantee
that actually holds today.

Two things are checked:

1. The removed module still fails loudly, so an accidental future import cannot
   quietly resurrect random-data code.
2. The live engine that replaced it never presents a market price it could not
   verify, and exposes MSP as a cited reference rather than as a forecast.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.comprehensive_crop_recommendations import (
    ComprehensiveCropRecommendations,
)
from advisory.services.crop_recommendation_engine import CropRecommendationEngine


class RemovedLegacyEngineTests(SimpleTestCase):
    """The dead random-data engine must stay dead and say so."""

    def test_legacy_engine_cannot_be_instantiated(self):
        with self.assertRaises(NotImplementedError) as ctx:
            ComprehensiveCropRecommendations()

        message = str(ctx.exception)
        self.assertIn("removed", message.lower())
        # The error has to name the replacement, otherwise a future caller has
        # no way to know where the real implementation lives.
        self.assertIn("CropRecommendationEngine", message)


class LivePricePredictionSafetyTests(SimpleTestCase):
    """The replacement engine must not invent prices, yields or forecasts."""

    def setUp(self):
        self.engine = CropRecommendationEngine()

    def _recommend(self):
        # Pin weather so the test is hermetic and does not depend on a live
        # provider being reachable from CI.
        weather = {
            "status": "success",
            "is_live": True,
            "data_source": "Open-Meteo",
            "current": {"temperature": 27, "humidity": 60},
            "forecast_7day": [],
        }
        with patch(
            "advisory.services.unified_realtime_service.weather_service.get_weather",
            return_value=weather,
        ):
            return self.engine.recommend(
                "Lucknow", 26.8467, 80.9462, state="Uttar Pradesh"
            )

    def test_unverified_market_price_is_never_presented_as_a_number(self):
        response = self._recommend()
        recommendations = response["recommendations"]
        self.assertTrue(recommendations)

        for crop in recommendations:
            status = crop["market_price_status"]
            if status != "live":
                # No live quote means no number at all, and the reason has to
                # be stated rather than left blank.
                self.assertIsNone(
                    crop["market_price"],
                    f"{crop['crop_name']} exposed a price while status={status}",
                )
                self.assertTrue(str(crop["market_price_source"]).strip())
                self.assertFalse(crop["market_is_live"])

    def test_msp_is_a_cited_reference_not_a_forecast(self):
        response = self._recommend()

        for crop in response["recommendations"]:
            msp = crop["msp_per_quintal"]
            if msp:
                # An MSP figure is only allowed alongside the season it belongs
                # to and a citable source, so a farmer can check it.
                self.assertTrue(str(crop["msp_season"]).strip())
                self.assertTrue(str(crop["msp_source"]).strip())

    def test_economics_are_labelled_as_estimates_not_predictions(self):
        response = self._recommend()

        # Whatever the label, it must declare the figure's standing rather than
        # imply a forecast. "price_required" appears when no verified price is
        # available, "indicative_estimate" when MSP backs the estimate.
        honest_labels = {"indicative_estimate", "price_required", "unavailable"}
        for crop in response["recommendations"]:
            self.assertIn(crop["economics_status"], honest_labels)
            self.assertNotIn("predict", str(crop["economics_status"]).lower())
            self.assertTrue(str(crop["economics_basis"]).strip())

    def test_prediction_data_is_a_score_breakdown_not_a_price_forecast(self):
        response = self._recommend()
        crop = response["recommendations"][0]
        prediction = crop["prediction_data"]

        # "prediction_data" must describe how the suitability score was reached,
        # not forecast a future price. Every factor carries its own points and
        # ceiling so the total can be audited by hand.
        self.assertIn("score_breakdown", prediction)
        self.assertTrue(prediction["method"])
        # Each entry is either a scored factor (points out of max_points) or the
        # roll-up totals. Both forms must be numeric and auditable by hand.
        for name, factor in prediction["score_breakdown"].items():
            if "raw_points" in factor:
                self.assertIn("possible_points", factor)
                self.assertIn("normalized_score", factor)
            else:
                self.assertIn("points", factor, f"factor {name} has no points")
                self.assertIn("max_points", factor, f"factor {name} has no ceiling")

        forecast_like = {"next_3_months", "next_6_months", "next_year"}
        self.assertFalse(
            forecast_like & set(prediction),
            "score breakdown must not carry price-forecast horizons",
        )
