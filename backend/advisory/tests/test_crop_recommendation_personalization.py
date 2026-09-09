from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.crop import CropAdvisoryViewSet
from advisory.api.viewsets.government import RealTimeGovernmentDataViewSet
from advisory.services.comprehensive_crop_database import (
    ALL_CROP_DATA,
    comprehensive_crop_database,
    validate_crop_profiles,
)
from advisory.services.crop_catalog import crop_catalog
from advisory.services.crop_registry import crop_registry
from advisory.services.crop_recommendation_engine import crop_recommendation_engine


class CropDatabaseCoverageTests(SimpleTestCase):
    def test_database_has_broad_canonical_indian_crop_coverage(self):
        self.assertGreaterEqual(len(ALL_CROP_DATA), 200)

        categories = {profile["category"] for profile in ALL_CROP_DATA.values()}
        self.assertTrue(
            {
                "Cereal",
                "Pulse",
                "Oilseed",
                "Vegetable",
                "Fruit",
                "Spice",
                "Fodder",
                "Medicinal",
                "Flower",
                "Plantation",
                "Aquatic",
            }.issubset(categories)
        )

        required = {
            "name_hindi",
            "season",
            "category",
            "soil_preference",
            "water_requirement",
            "temperature_min",
            "temperature_max",
            "rainfall_mm",
            "duration_days",
            "input_cost_per_hectare",
            "profit_per_hectare",
            "market_demand",
            "ph_min",
            "ph_max",
        }
        for crop_id, profile in ALL_CROP_DATA.items():
            with self.subTest(crop=crop_id):
                self.assertTrue(required.issubset(profile))
                self.assertLess(profile["temperature_min"], profile["temperature_max"])
                self.assertLess(profile["ph_min"], profile["ph_max"])
                self.assertGreater(profile["duration_days"], 0)

    def test_search_catalog_contains_only_canonical_recommendation_ids(self):
        catalog_ids = {crop["id"] for crop in crop_catalog._crops}
        self.assertEqual(catalog_ids - set(ALL_CROP_DATA), set())
        self.assertEqual(len(catalog_ids), len(crop_catalog._crops))

        for query, expected_id in {
            "arhar": "tur",
            "lentil": "masoor",
            "arecanut": "areca_nut",
            "french bean": "french_bean",
            "cucumber": "cucumber",
            "pear": "pear",
        }.items():
            with self.subTest(query=query):
                self.assertEqual(crop_catalog.normalize(query)["id"], expected_id)

    def test_all_profiles_satisfy_farmer_ready_contract(self):
        self.assertEqual(len(ALL_CROP_DATA), 202)
        self.assertEqual(validate_crop_profiles(), [])
        self.assertEqual(comprehensive_crop_database.count(), 202)
        for crop_id, profile in ALL_CROP_DATA.items():
            with self.subTest(crop=crop_id):
                self.assertTrue(profile["aliases"])
                self.assertEqual(profile["market_mapping"]["price_policy"], "fresh_official_row_only")
                self.assertFalse(profile["district_suitability"]["static_district_claims"])

    def test_canonical_registry_exposes_every_recommendation_profile(self):
        self.assertEqual(set(crop_registry.all_ids()), set(ALL_CROP_DATA))
        self.assertEqual(crop_registry.normalize("rambutan")["id"], "rambutan")
        self.assertEqual(crop_registry.normalize("रामबूटान")["id"], "rambutan")

    def test_profile_facade_returns_canonical_crop(self):
        profile = comprehensive_crop_database.get_crop_info("wheat")
        self.assertEqual(profile["name_hindi"], "गेहूँ")


class CropRecommendationPersonalizationTests(SimpleTestCase):
    def test_positive_factor_scores_do_not_imply_complete_farmer_data(self):
        engine = crop_recommendation_engine
        scored = [(95, "wheat", ALL_CROP_DATA["wheat"], ["Season match"], {
            "season": {"status": "ideal"}, "soil": {"status": "ideal"},
        })]
        crop = engine._format_recommendations(scored, "en", {}, {}, {})[0]
        self.assertEqual(crop["prediction_data"]["data_completeness"], 0)
        self.assertEqual(crop["prediction_data"]["score_factor_coverage"], 1)
        self.assertIn("ph", crop["confidence_inputs_missing"])
        self.assertIn("budget_per_hectare", crop["confidence_inputs_missing"])
        self.assertEqual(crop["confidence_kind"], "heuristic_not_calibrated_probability")

    def test_regional_defaults_are_not_reported_as_farmer_measurements(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend("Delhi", 28.6139, 77.2090, state="Delhi", language="en")
        self.assertEqual(result["input_provenance"]["soil_type"], "regional_assumption")
        self.assertEqual(result["input_provenance"]["irrigation"], "regional_assumption")

    def test_complete_inputs_include_measured_zero_and_have_higher_confidence(self):
        engine = crop_recommendation_engine
        scored = [(80, "wheat", ALL_CROP_DATA["wheat"], [], {"season": {"status": "ideal"}})]
        inputs = {"soil_type": "loamy", "irrigation": "drip", "previous_crop": "rice",
                  "ph": 6.5, "budget_per_hectare": 50000, "nitrogen_kg_ha": 0,
                  "phosphorus_kg_ha": 20, "potassium_kg_ha": 100}
        complete = engine._format_recommendations(
            scored, "en", {"wheat": {"is_live": True}}, {}, inputs, weather_is_live=True,
        )[0]
        missing = engine._format_recommendations(scored, "en", {}, {}, {})[0]
        self.assertEqual(complete["prediction_data"]["data_completeness"], 1)
        self.assertEqual(complete["confidence_inputs_missing"], [])
        self.assertGreater(complete["confidence"], missing["confidence"])

    def setUp(self):
        self.engine = crop_recommendation_engine
        self.realtime = (
            {
                "status": "success",
                "is_live": True,
                "data_source": "Open-Meteo",
                "current": {"temperature": 24, "humidity": 60},
                "forecast_7day": [
                    {"rainfall_mm": 8, "max_temp": 28} for _ in range(7)
                ],
            },
            {
                "status": "unavailable",
                "is_live": False,
                "data_source": "unavailable",
                "top_crops": [],
            },
            {"weather": "live", "market": "unavailable"},
        )

    def test_farmer_parameters_are_used_and_explained(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend(
                "Delhi",
                28.6139,
                77.2090,
                state="Delhi",
                language="en",
                agronomic_inputs={
                    "season": "rabi",
                    "soil_type": "loamy",
                    "irrigation": "drip",
                    "ph": 6.7,
                    "ec_ds_m": 1.2,
                    "moisture_pct": 42,
                    "organic_carbon": 0.7,
                    "nitrogen_kg_ha": 180,
                    "phosphorus_kg_ha": 35,
                    "potassium_kg_ha": 220,
                    "budget_per_hectare": 60000,
                    "farm_size_ha": 1.5,
                    "previous_crop": "rice",
                    "risk_tolerance": "low",
                    "preferred_categories": ["Vegetable", "Pulse"],
                },
            )

        self.assertEqual(result["season_key"], "rabi")
        self.assertEqual(result["soil_type"], "Loamy")
        self.assertEqual(result["database_size"], len(ALL_CROP_DATA))
        self.assertEqual(result["analysis_method"], "multi_factor_scoring_v5")
        self.assertEqual(result["input_parameters"]["ph"], 6.7)
        self.assertIn("Soil pH: 6.7", result["factors_analyzed"])

        top = result["recommendations"][0]
        self.assertIn("score_breakdown", top["prediction_data"])
        self.assertIn("soil_ph", top["prediction_data"]["score_breakdown"])
        self.assertIn("data_completeness", top["prediction_data"])
        self.assertEqual(top["economics_status"], "indicative_estimate")

    def test_low_budget_keeps_top_results_within_farmer_budget(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend(
                "Delhi",
                28.6139,
                77.2090,
                state="Delhi",
                language="en",
                agronomic_inputs={
                    "season": "rabi",
                    "budget_per_hectare": 30000,
                    "risk_tolerance": "low",
                },
            )

        self.assertTrue(result["recommendations"])
        self.assertTrue(
            all(crop["input_cost_per_hectare"] <= 30000 for crop in result["top_4_recommendations"])
        )

    def test_preferred_category_is_a_farmer_selected_filter(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend(
                "Varanasi",
                25.3176,
                82.9739,
                state="Uttar Pradesh",
                language="en",
                agronomic_inputs={
                    "season": "rabi",
                    "preferred_categories": ["Pulse"],
                },
            )

        self.assertTrue(result["recommendations"])
        self.assertEqual(
            {crop["category"] for crop in result["recommendations"]},
            {"Pulse"},
        )

    def test_target_crop_search_scores_only_requested_crop(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend(
                "Varanasi",
                25.3176,
                82.9739,
                state="Uttar Pradesh",
                language="en",
                agronomic_inputs={
                    "season": "kharif",
                    "target_crop": "ashwagandha",
                },
            )

        self.assertEqual(len(result["recommendations"]), 1)
        self.assertEqual(result["recommendations"][0]["crop_name"], "Ashwagandha")

    def test_temperature_warning_is_not_hidden_by_positive_season_reason(self):
        hot_realtime = (
            {
                "status": "success",
                "is_live": True,
                "data_source": "Open-Meteo",
                "current": {"temperature": 27.4, "humidity": 70},
                "forecast_7day": [{"rainfall_mm": 2, "max_temp": 30}] * 7,
            },
            self.realtime[1],
            {"weather": "live", "market": "unavailable"},
        )
        with patch.object(self.engine, "_fetch_realtime_context", return_value=hot_realtime):
            result = self.engine.recommend(
                "Varanasi",
                25.3176,
                82.9739,
                state="Uttar Pradesh",
                language="hi",
                agronomic_inputs={"season": "rabi", "target_crop": "rajma"},
            )

        crop = result["recommendations"][0]
        self.assertTrue(crop["reason"].startswith("Too hot"))
        self.assertIn("27.4°C", crop["reason_hindi"])
        self.assertIsNone(crop["profit_per_hectare"])
        self.assertEqual(crop["economics_status"], "price_required")
        self.assertEqual(crop["economics_basis"], "verified_price_required")

    def test_current_msp_is_declared_as_economics_basis(self):
        with patch.object(self.engine, "_fetch_realtime_context", return_value=self.realtime):
            result = self.engine.recommend(
                "Delhi",
                28.6139,
                77.2090,
                state="Delhi",
                language="en",
                agronomic_inputs={"season": "rabi", "target_crop": "wheat"},
            )

        crop = result["recommendations"][0]
        self.assertEqual(crop["msp_per_quintal"], 2585)
        self.assertEqual(crop["economics_basis"], "current_msp_reference")
        self.assertEqual(crop["profit_per_hectare"], (45 * 2585) - 25000)

    def test_api_passes_strict_farmer_inputs_to_engine(self):
        request = APIRequestFactory().get(
            "/api/advisories/",
            {
                "location": "Delhi",
                "season": "rabi",
                "soil_type": "loamy",
                "irrigation": "drip",
                "ph": "6.8",
                "budget_per_hectare": "45000",
                "preferred_categories": "vegetable,pulse",
            },
        )
        expected = {"recommendations": [], "top_4_recommendations": []}
        with patch.object(
            crop_recommendation_engine,
            "recommend_from_context",
            return_value=expected,
        ) as recommend:
            response = CropAdvisoryViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        inputs = recommend.call_args.kwargs["agronomic_inputs"]
        self.assertEqual(inputs["season"], "rabi")
        self.assertEqual(inputs["soil_type"], "loamy")
        self.assertEqual(inputs["ph"], 6.8)
        self.assertEqual(inputs["preferred_categories"], ["Vegetable", "Pulse"])

    def test_api_maps_crop_search_to_internal_target_crop(self):
        request = APIRequestFactory().get(
            "/api/advisories/",
            {"location": "Varanasi", "crop": "अश्वगंधा"},
        )
        with patch.object(
            crop_recommendation_engine,
            "recommend_from_context",
            return_value={"recommendations": [], "top_4_recommendations": []},
        ) as recommend:
            response = CropAdvisoryViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommend.call_args.kwargs["agronomic_inputs"]["target_crop"],
            "ashwagandha",
        )

    def test_api_rejects_invalid_agronomic_values(self):
        request = APIRequestFactory().get(
            "/api/advisories/",
            {"location": "Delhi", "season": "monsoon", "ph": "18"},
        )
        response = CropAdvisoryViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)

    def test_realtime_government_api_passes_same_farmer_inputs(self):
        request = APIRequestFactory().get(
            "/api/realtime-gov/crop_recommendations/",
            {
                "location": "Lucknow",
                "season": "kharif",
                "soil_type": "alluvial",
                "irrigation": "rainfed",
                "ph": "7.1",
                "previous_crop": "wheat",
            },
        )
        expected = {"recommendations": [], "top_4_recommendations": []}
        with patch.object(
            crop_recommendation_engine,
            "recommend_from_context",
            return_value=expected,
        ) as recommend:
            response = RealTimeGovernmentDataViewSet.as_view(
                {"get": "crop_recommendations"}
            )(request)

        self.assertEqual(response.status_code, 200)
        inputs = recommend.call_args.kwargs["agronomic_inputs"]
        self.assertEqual(inputs["season"], "kharif")
        self.assertEqual(inputs["soil_type"], "alluvial")
        self.assertEqual(inputs["irrigation"], "rainfed")
        self.assertEqual(inputs["ph"], 7.1)
        self.assertEqual(inputs["previous_crop"], "wheat")
