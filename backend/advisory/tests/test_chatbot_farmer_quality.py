import re
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import (
    INTENT_CROP_RECOMMENDATION,
    INTENT_FERTILIZER,
    INTENT_GOVERNMENT_SCHEME,
    INTENT_IRRIGATION,
    INTENT_MARKET_PRICE,
    INTENT_PEST_DISEASE,
    INTENT_SOWING,
    INTENT_STORAGE,
    INTENT_WEATHER,
    ChatIntelligenceService,
    SensorContext,
    WeatherConstraints,
    _has_unverified_market_claim,
    farmer_location_label,
)
from advisory.services.location_context import LocationContext


class ChatbotFarmerQualityTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=28.6139,
            longitude=77.2090,
            display_name="Delhi",
            state="Delhi",
        )

    def test_multilingual_farmer_questions_classify_to_expected_service(self):
        cases = {
            "kal barish hogi kya": INTENT_WEATHER,
            "Delhi weather forecast for next week": INTENT_WEATHER,
            "gehu ka mandi bhav kya hai": INTENT_MARKET_PRICE,
            "wheat leaves have rust disease": INTENT_PEST_DISEASE,
            "mere gehu ki pattiyon par peele dhabbe hain": INTENT_PEST_DISEASE,
            "धान में खाद कब डालें": INTENT_FERTILIZER,
            "cotton ko pani kab dena hai": INTENT_IRRIGATION,
            "PM Kisan scheme eligibility": INTENT_GOVERNMENT_SCHEME,
            "meri location ke liye best crop": INTENT_CROP_RECOMMENDATION,
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                intent, _ = self.service.classify_query(query)
                self.assertEqual(intent, expected)

    def test_hinglish_tomorrow_word_is_not_misclassified_as_a_crop(self):
        intent, crops = self.service.classify_query("kal ka mausam kaisa hoga")

        self.assertEqual(intent, INTENT_WEATHER)
        self.assertEqual(crops, [])

    def test_storage_question_wins_over_generic_harvest_wording(self):
        query = "How can I store wheat safely after harvest?"
        intent, crops = self.service.classify_query(query)

        self.assertEqual(intent, INTENT_STORAGE)
        self.assertEqual([crop["id"] for crop in crops], ["wheat"])

        result = self.service.answer(query, self.ctx, language="en", fast_mode=True)

        self.assertEqual(result["intent"], INTENT_STORAGE)
        self.assertIn("store wheat safely", result["response"].lower())
        self.assertIn("12-14%", result["response"])
        self.assertNotIn("Harvest window", result["response"])
        self.assertNotIn("Current weather", result["response"])
        self.assertNotIn("3g/quintal", result["response"])

        detailed = self.service.answer(
            "I have 2 bigha of wheat and no metal bin. How should I store it after harvest?",
            self.ctx,
            language="en",
            fast_mode=True,
        )
        self.assertIn("2 bigha", detailed["response"])
        self.assertIn("do not have a metal bin", detailed["response"])

        chunks = list(self.service.answer_stream(query, self.ctx, language="en"))
        streamed = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        self.assertEqual(chunks[-1]["intent"], INTENT_STORAGE)
        self.assertIn("store wheat safely", streamed.lower())
        self.assertNotIn("Harvest window", streamed)
        self.assertNotIn("Agmarknet", chunks[-1].get("sources", []))

    def test_generic_mandi_question_does_not_invent_an_apmc_name(self):
        self.assertIsNone(
            self.service._extract_query_mandi(
                "What is wheat mandi price today?",
                self.ctx,
            )
        )
        self.assertEqual(
            self.service._extract_query_mandi(
                "Lucknow mandi mein gehu ka bhav kya hai?",
                self.ctx,
            ),
            "Lucknow Mandi",
        )

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_hindi_yellow_spot_question_uses_fast_safe_symptom_advisory(
        self, weather, qwen, phase1_post
    ):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "current": {"temperature": 27},
            "forecast_7day": [],
        }

        started = time.monotonic()
        chunks = list(self.service.answer_stream(
            "मेरे गेहूँ की पत्तियों पर पीले धब्बे हैं, मैं अभी क्या जांच करूँ?",
            self.ctx,
            language="auto",
        ))
        elapsed_ms = (time.monotonic() - started) * 1000
        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))

        self.assertEqual(chunks[-1]["intent"], INTENT_PEST_DISEASE)
        self.assertLess(elapsed_ms, 3000)
        self.assertIn("पक्की पहचान नहीं", text)
        self.assertIn("पीले धब्बे", text)
        self.assertIn("पीला रतुआ", text)
        self.assertIn("भूरा रतुआ", text)
        self.assertNotIn("करनाल बंट", text)
        self.assertIn("पत्ती के ऊपर-नीचे", text)
        self.assertNotRegex(text, r"\d+(?:\.\d+)?\s*(?:ml|g)/L")
        phase1_post.assert_not_called()
        qwen.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_hinglish_yellow_spot_question_gets_question_aware_symptom_advisory(
        self, weather, qwen, phase1_post
    ):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "current": {"temperature": 27},
            "forecast_7day": [],
        }

        chunks = list(self.service.answer_stream(
            "mere gehu ki pattiyon par peele dhabbe hain, kya check karun?",
            self.ctx,
            language="auto",
        ))
        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))

        self.assertEqual(chunks[-1]["intent"], INTENT_PEST_DISEASE)
        self.assertIn("yellow spots", text)
        self.assertIn("Possible issues", text)
        self.assertIn("Yellow Rust", text)
        self.assertNotIn("Karnal Bunt", text)
        self.assertNotIn("Crop recommendations", text)
        phase1_post.assert_not_called()
        qwen.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_hinglish_black_spot_common_word_forms_use_safe_symptom_advisory(
        self, weather, qwen, phase1_post
    ):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "current": {"temperature": 28},
            "forecast_7day": [],
        }

        started = time.monotonic()
        result = self.service.answer(
            "tamatar ke patte pe kaale daag hain, kya karun?",
            self.ctx,
            language="auto",
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        self.assertEqual(result["intent"], INTENT_PEST_DISEASE)
        self.assertLess(elapsed_ms, 3000)
        self.assertIn("black or dark spots", result["response"])
        self.assertIn("Disease classification abhi disabled hai", result["response"])
        self.assertNotIn("Fruitborer", result["response"])
        self.assertNotRegex(result["response"], r"\d+(?:\.\d+)?\s*(?:ml|g)/L")
        phase1_post.assert_not_called()
        qwen.assert_not_called()

    @patch("advisory.services.chat_intelligence_service._is_valid_gemini_key")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_sowing_question_uses_grounded_calendar_without_llm(
        self, weather, qwen, gemini_key_check
    ):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "data_source": "Open-Meteo",
            "current": {"temperature": 24},
        }

        started = time.monotonic()
        result = self.service.answer(
            "गेहूँ की बुवाई का सही समय और बीज दर बताएं",
            self.ctx,
            language="hi",
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        self.assertEqual(result["intent"], INTENT_SOWING)
        self.assertLess(elapsed_ms, 1000)
        self.assertIn("गेहूँ की बुवाई", result["response"])
        self.assertIn("बीज दर", result["response"])
        self.assertIn("100-125 kg/ha", result["response"])
        self.assertEqual(result["ai_data_quality"]["tier"], "instant_rule")
        weather.assert_not_called()
        qwen.assert_not_called()
        gemini_key_check.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_crop_profile_question_is_grounded_fast_and_skips_realtime_calls(
        self, weather, market
    ):
        started = time.monotonic()
        result = self.service.answer(
            "Rambutan ke liye climate aur mitti kaisi honi chahiye?",
            self.ctx,
            language="hinglish",
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        self.assertLess(elapsed_ms, 500)
        self.assertIn("22-32°C", result["response"])
        self.assertIn("5.0-6.5", result["response"])
        self.assertIn("Mitti:", result["response"])
        self.assertNotRegex(result["response"], r"[\u0900-\u097F]")
        self.assertEqual(result["ai_data_quality"]["tier"], "crop_profile")
        weather.assert_not_called()
        market.assert_not_called()

    def test_crop_mention_does_not_hijack_a_soil_management_question(self):
        query = (
            "How can I improve soil organic carbon after rice without burning "
            "crop residue?"
        )
        _intent, crops = self.service.classify_query(query)

        self.assertEqual([crop["id"] for crop in crops], ["rice"])
        self.assertIsNone(self.service._crop_profile_answer(query, crops, "en"))

        response = self.service._smart_rule_response(
            query=query,
            intent="soil",
            crops=crops,
            ctx=self.ctx,
            context_block="",
            lang="en",
            history=[],
            sc=SensorContext(),
            wc=WeatherConstraints(),
        )
        self.assertIn("Do not burn the residue", response)
        self.assertIn("Soil Organic Carbon", response)
        self.assertNotIn("Dominant soil type", response)

    def test_crop_info_timeout_fallback_answers_drainage_question(self):
        query = (
            "Why is drainage important for soybean during monsoon? "
            "Give three practical steps."
        )
        intent, crops = self.service.classify_query(query)

        response = self.service._smart_rule_response(
            query=query,
            intent=intent,
            crops=crops,
            ctx=self.ctx,
            context_block="",
            lang="en",
            history=[],
            sc=SensorContext(),
            wc=WeatherConstraints(),
        )

        self.assertEqual(intent, "crop_info")
        self.assertIn("soybean", response.lower())
        self.assertIn("drainage", response.lower())
        self.assertIn("waterlogging", response.lower())
        self.assertIn("1.", response)
        self.assertIn("2.", response)
        self.assertIn("3.", response)
        self.assertNotIn("Crop Recommendations", response)

    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_crop_drainage_question_uses_fast_grounded_path(self, phase1_post):
        started = time.monotonic()
        chunks = list(self.service.answer_stream(
            "Why is drainage important for soybean during monsoon? Give three practical steps.",
            self.ctx,
            language="en",
        ))
        elapsed_ms = (time.monotonic() - started) * 1000
        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))

        self.assertLess(elapsed_ms, 500)
        self.assertIn("Drainage matters for Soybean", text)
        self.assertEqual(chunks[-1]["chatbot_diagnostics"]["selected_tier"], "instant_rule")
        phase1_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_crop_profile_stream_skips_local_model_and_finishes_fast(self, phase1_post):
        started = time.monotonic()
        chunks = list(self.service.answer_stream(
            "Ashwagandha ki mitti aur season batao",
            self.ctx,
            language="hinglish",
        ))
        elapsed_ms = (time.monotonic() - started) * 1000
        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))

        self.assertLess(elapsed_ms, 500)
        self.assertIn("Mitti:", text)
        self.assertIn("Season:", text)
        self.assertEqual(chunks[-1]["ai_data_quality"]["tier"], "crop_profile")
        phase1_post.assert_not_called()

    def test_greetings_match_requested_language_and_latency_budget(self):
        started = time.monotonic()
        hindi = self.service.answer("नमस्ते", self.ctx, language="hi")
        elapsed_ms = (time.monotonic() - started) * 1000
        english = self.service.answer("hello", self.ctx, language="en")
        marathi = self.service.answer("नमस्कार", self.ctx, language="mr")

        self.assertLess(elapsed_ms, 500)
        self.assertRegex(hindi["response"], r"[\u0900-\u097F]")
        self.assertNotRegex(english["response"], r"[\u0900-\u097F]")
        self.assertIn("नमस्कार शेतकरी", marathi["response"])
        self.assertNotIn("Hello Farmer", marathi["response"])
        self.assertEqual(hindi["ai_data_quality"]["tier"], "instant_rule")

    def test_reverse_geocoded_neighborhood_keeps_district_in_farmer_label(self):
        ctx = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Hazratganj",
            district="Lucknow",
            state="Uttar Pradesh",
        )

        response = self.service.answer("hello", ctx, language="en")

        self.assertIn("Hazratganj, Lucknow district, Uttar Pradesh", response["response"])

    def test_location_label_does_not_repeat_district_suffix(self):
        ctx = LocationContext(
            latitude=19.0760,
            longitude=72.8777,
            display_name="Hallow Pul",
            district="Mumbai Suburban District",
            state="Maharashtra",
            source="gps_coordinates_only",
        )

        self.assertEqual(
            farmer_location_label(ctx),
            "Hallow Pul, Mumbai Suburban District, Maharashtra",
        )

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_location_specific_question_never_uses_default_when_unconfirmed(
        self, weather, market
    ):
        unknown = LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            source="unconfirmed",
            confidence=0.0,
        )

        result = self.service.answer(
            "kal ka mausam kaisa hoga",
            unknown,
            language="auto",
        )

        self.assertEqual(result["chatbot_diagnostics"]["selected_tier"], "location_required")
        self.assertIn("location confirm", result["response"].lower())
        weather.assert_not_called()
        market.assert_not_called()

    def test_stream_location_specific_question_stops_before_local_ai_when_unconfirmed(self):
        unknown = LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            source="unconfirmed",
            confidence=0.0,
        )

        chunks = list(self.service.answer_stream(
            "आज गेहूं का मंडी भाव क्या है",
            unknown,
            language="auto",
        ))

        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        self.assertIn("स्थान चुनें", text)
        self.assertEqual(chunks[-1]["chatbot_diagnostics"]["selected_tier"], "location_required")

    def test_general_soil_guidance_does_not_require_confirmed_location(self):
        unknown = LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            source="unconfirmed",
            confidence=0.0,
        )
        query = (
            "How can I improve soil organic carbon after rice without burning "
            "crop residue?"
        )

        result = self.service.answer(query, unknown, language="en", fast_mode=True)

        self.assertNotEqual(
            result["chatbot_diagnostics"]["selected_tier"],
            "location_required",
        )
        self.assertIn("Do not burn the residue", result["response"])
        self.assertEqual(
            result["chatbot_diagnostics"]["selected_tier"],
            "instant_rule",
        )
        self.assertNotIn("20 cm", result["response"])
        self.assertNotIn("30%", result["response"])
        self.assertFalse(any(
            "Agro-Climatic" in source or "Agmarknet" in source
            for source in result["sources"]
        ))

    def test_general_soil_stream_does_not_require_confirmed_location(self):
        unknown = LocationContext(
            latitude=None,
            longitude=None,
            display_name="",
            source="unconfirmed",
            confidence=0.0,
        )
        query = (
            "How can I improve soil organic carbon after rice without burning "
            "crop residue?"
        )

        chunks = list(self.service.answer_stream(
            query,
            unknown,
            language="en",
        ))
        response_text = "".join(chunk for chunk in chunks if isinstance(chunk, str))

        self.assertIn("Do not burn the residue", response_text)
        self.assertNotIn("20 cm", response_text)
        self.assertNotIn("30%", response_text)
        self.assertNotEqual(
            chunks[-1]["chatbot_diagnostics"]["selected_tier"],
            "location_required",
        )
        self.assertEqual(
            chunks[-1]["chatbot_diagnostics"]["selected_tier"],
            "instant_rule",
        )

    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    def test_live_mandi_question_uses_verified_data_without_llm(
        self, market, kb_answer, qwen
    ):
        market.return_value = {
            "status": "success",
            "is_live": True,
            "data_source": "data.gov.in Official API (Agmarknet OGD)",
            "reported_date": "10-07-2026",
            "top_crops": [{
                "crop_name": "Wheat",
                "crop_name_hindi": "गेहूँ",
                "crop_id": "wheat",
                "modal_price": 2510,
                "msp": 2585,
                "mandi_name": "Azadpur",
                "is_live": True,
            }],
        }

        result = self.service.answer(
            "What is wheat mandi price today?", self.ctx, language="en"
        )

        self.assertIn("2510", result["response"])
        self.assertIn("10-07-2026", result["response"])
        self.assertNotIn("Agmarknet today", result["response"])
        self.assertEqual(result["ai_data_quality"]["tier"], "verified_official_data")
        self.assertEqual(result["ai_data_quality"]["label"], "Verified official report")
        kb_answer.assert_not_called()
        qwen.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    def test_named_mandi_question_requests_exact_apmc_and_answers_in_hinglish(self, market):
        market.return_value = {
            "status": "success",
            "is_live": True,
            "coverage": "market",
            "data_source": "Agmarknet 2.0 API",
            "reported_date": "13-07-2026",
            "top_crops": [{
                "crop_name": "Wheat",
                "crop_name_hindi": "गेहूँ",
                "crop_id": "wheat",
                "modal_price": 2400,
                "msp": 2585,
                "mandi_name": "Lucknow APMC",
                "reported_date": "13-07-2026",
                "is_live": True,
            }],
        }

        result = self.service.answer(
            "Lucknow mandi mein gehu ka latest bhav kya hai?",
            self.ctx,
            language="auto",
        )

        requested_mandis = [call.kwargs.get("mandi") for call in market.call_args_list]
        self.assertIn("Lucknow Mandi", requested_mandis)
        self.assertEqual(result["language"], "hinglish")
        self.assertIn("Lucknow APMC", result["response"])
        self.assertIn("13-07-2026", result["response"])
        self.assertNotIn("state-average", result["response"])
        self.assertEqual(market.call_count, 1)
        self.assertEqual(result["crop_suggestions"][0]["modal_price"], 2400)
        self.assertEqual(result["crop_suggestions"][0]["mandi"], "Lucknow APMC")

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    def test_empty_prefetched_market_result_is_not_refetched(self, market):
        context, sources = self.service._build_official_context(
            self.ctx,
            "What is the wheat mandi price?",
            INTENT_MARKET_PRICE,
            [{"id": "wheat", "name": "Wheat"}],
            lang="en",
            _weather={},
            _prices={},
        )

        market.assert_not_called()
        self.assertNotIn("modal Rs", context)
        self.assertFalse(any("official report" in source.lower() for source in sources))

    def test_market_context_drops_unrequested_commodities(self):
        prices = {
            "is_live": True,
            "data_source": "Agmarknet official feed",
            "reported_date": "17-07-2026",
            "top_crops": [
                {
                    "crop_name": "Wheat",
                    "crop_name_hindi": "गेहूँ",
                    "modal_price": 2400,
                    "msp": 2585,
                    "mandi_name": "Lucknow APMC",
                    "reported_date": "17-07-2026",
                    "is_live": True,
                },
                {
                    "crop_name": "Maize",
                    "crop_name_hindi": "मक्का",
                    "modal_price": 1825,
                    "msp": 2410,
                    "mandi_name": "Uttar Pradesh average",
                    "reported_date": "17-07-2026",
                    "is_live": True,
                },
            ],
        }

        context, _sources = self.service._build_official_context(
            self.ctx,
            "What is the wheat mandi price?",
            INTENT_MARKET_PRICE,
            [{"id": "wheat", "name": "Wheat"}],
            lang="en",
            _weather={},
            _prices=prices,
        )

        self.assertIn("Wheat", context)
        self.assertNotIn("Maize", context)
        self.assertNotIn("Uttar Pradesh average", context)

    @patch("advisory.services.chat_intelligence_service.market_service.get_nearby_live_prices")
    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    def test_missing_exact_mandi_row_keeps_nearby_official_prices_separate(
        self, market, nearby
    ):
        market.return_value = {
            "status": "unavailable",
            "is_live": False,
            "data_source": "Agmarknet 2.0 API",
            "top_crops": [],
        }
        nearby.return_value = [{
            "crop_name": "Wheat",
            "modal_price": 2520,
            "mandi_name": "Kanpur Grain APMC",
            "reported_date": "16-07-2026",
            "distance_km": 74.2,
            "is_live": True,
        }]

        result = self.service.answer(
            "Lucknow mandi mein gehu ka latest bhav kya hai?",
            self.ctx,
            language="auto",
        )

        self.assertIn("current official price row", result["response"])
        self.assertIn("Kanpur Grain APMC", result["response"])
        self.assertIn("74.2 km", result["response"])
        self.assertIn("selected mandi ke bhav nahi", result["response"])
        self.assertNotIn("Live", " ".join(result["sources"]))
        self.assertEqual(result["ai_data_quality"]["tier"], "rule_based_fallback")
        nearby.assert_called_once()

    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_weather_question_uses_verified_data_without_llm(
        self, weather, kb_answer, qwen
    ):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "data_source": "Open-Meteo",
            "current": {
                "temperature": 31,
                "humidity": 62,
                "wind_speed": 8,
                "rainfall_mm": 0,
                "condition": "Clear",
            },
            "forecast_7day": [],
        }

        result = self.service.answer(
            "Delhi weather today", self.ctx, language="en"
        )

        self.assertIn("31", result["response"])
        self.assertEqual(result["ai_data_quality"]["tier"], "verified_realtime")
        kb_answer.assert_not_called()
        qwen.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_hinglish_tomorrow_weather_is_detected_and_answered_directly(self, weather):
        tomorrow = (datetime.now(tz=timezone.utc) + timedelta(days=1)).date().isoformat()
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "data_source": "Open-Meteo",
            "current": {
                "temperature": 31,
                "humidity": 62,
                "wind_speed": 8,
                "rainfall_mm": 0,
                "condition": "Clear",
            },
            "forecast_7day": [{
                "date": tomorrow,
                "max_temp": 29,
                "rainfall_mm": 4,
                "rain_probability": 65,
            }],
            "farming_alerts": ["Heavy rain risk — postpone spraying"],
        }

        result = self.service.answer(
            "kal ka mausam Kaisa hoga",
            self.ctx,
            language="auto",
        )

        self.assertEqual(result["language"], "hinglish")
        self.assertIn("Kal Delhi", result["response"])
        self.assertIn("65%", result["response"])
        self.assertEqual(result["response"].count("Heavy rain risk"), 1)
        self.assertEqual(result["ai_data_quality"]["tier"], "verified_realtime")

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_weather_question_directly_answers_irrigation_decision(self, weather):
        tomorrow = (datetime.now(tz=timezone.utc) + timedelta(days=1)).date().isoformat()
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "data_source": "Open-Meteo",
            "current": {
                "temperature": 32,
                "humidity": 70,
                "wind_speed": 9,
                "rainfall_mm": 0,
                "condition": "Cloudy",
            },
            "forecast_7day": [{
                "date": tomorrow,
                "max_temp": 30,
                "rainfall_mm": 5,
                "rain_probability": 88,
            }],
            "farming_alerts": [],
        }

        result = self.service.answer(
            "What will tomorrow's weather be, and should I irrigate wheat today?",
            self.ctx,
            language="en",
        )

        self.assertIn("88%", result["response"])
        self.assertIn("Postpone routine irrigation today", result["response"])
        self.assertNotIn("Weather alone is not enough", result["response"])

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_disease_fallback_never_claims_classification_or_unsourced_dose(self, weather):
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
        }

        result = self.service.answer(
            "Rice leaves have blast spots, what should I spray?",
            self.ctx,
            language="en",
            fast_mode=True,
        )

        self.assertNotRegex(result["response"], r"\b\d+(?:\.\d+)?\s*(?:ml|g)\s*/\s*l\b")
        self.assertNotIn("identifies 150+", result["response"])
        self.assertIn("advisory", result["response"].lower())
        self.assertIn("blast", result["response"].lower())
        self.assertIn("KVK", result["response"])

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    def test_disease_query_never_calls_generative_classifier(self, qwen, weather):
        weather.return_value = {
            "status": "unavailable",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
        }

        result = self.service.answer(
            "Rice leaves have blast spots, identify disease and dose",
            self.ctx,
            language="en",
        )

        qwen.assert_not_called()
        self.assertIn("not a diagnosis", result["response"])
        self.assertNotRegex(result["response"], r"\b\d+(?:\.\d+)?\s*(?:ml|g)\s*/\s*l\b")

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    def test_unattributed_generated_pesticide_dose_is_rejected(self, qwen, weather):
        weather.return_value = {
            "status": "unavailable",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
        }
        qwen.return_value = "Use product X at 2.5 g/L."

        result = self.service.answer(
            "How should I manage my crop safely?",
            self.ctx,
            language="en",
        )

        self.assertNotIn("2.5 g/L", result["response"])
        self.assertEqual(
            result["chatbot_diagnostics"]["fallback_reason"],
            "unattributed_pesticide_dose_rejected",
        )

    def test_unverified_generated_market_claim_is_rejected_without_live_feed(self):
        generated = "Dry the wheat below 14%. The current market rate is Rs 150 per kg."

        self.assertTrue(
            _has_unverified_market_claim(generated, INTENT_STORAGE, {"is_live": False})
        )
        self.assertFalse(
            _has_unverified_market_claim(
                "The verified mandi row reports Rs 2,300 per quintal.",
                INTENT_MARKET_PRICE,
                {"is_live": True},
            )
        )

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_kb_facts_are_grounding_for_fresh_question_specific_answer(
        self,
        kb_answer,
        qwen,
        weather,
    ):
        stored = "Stored wheat management note: use certified seed and monitor soil moisture."
        kb_answer.return_value = {"answer": stored, "source": "knowledge_base"}
        qwen.return_value = (
            "For your Delhi field, prioritize certified wheat seed and monitor soil moisture."
        )
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "What should I prioritize for healthy wheat crop management?",
            self.ctx,
            language="en",
        )

        self.assertNotEqual(result["response"], stored)
        self.assertIn("certified wheat seed", result["response"].lower())
        self.assertIn("soil moisture", result["response"].lower())
        self.assertEqual(qwen.call_args.kwargs["local_kb_context"], stored)

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_offline_sowing_fallback_answers_time_and_method_not_raw_kb(
        self,
        kb_answer,
        weather,
    ):
        stored = "गेहूँ की बुवाई नवंबर में करें।"
        kb_answer.return_value = {"answer": stored, "source": "knowledge_base"}
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "गेहूँ की बुवाई का सही समय और तरीका बताएं",
            self.ctx,
            language="hi",
            fast_mode=True,
        )

        self.assertNotEqual(result["response"], stored)
        self.assertIn("बीज दर", result["response"])
        self.assertIn("बुवाई गहराई", result["response"])
        self.assertIn("बुवाई का समय", result["response"])

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    def test_sowing_stream_uses_instant_grounded_path(self, weather, requests_post):
        weather.return_value = {
            "status": "success",
            "is_live": True,
            "current": {"temperature": 24, "humidity": 55, "condition": "Clear"},
            "forecast_7day": [],
            "data_source": "Open-Meteo",
        }

        chunks = list(self.service.answer_stream(
            "gehu ki buwai ka sahi samay aur tarika batao",
            self.ctx,
            language="auto",
        ))

        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        self.assertIn("Sowing", text)
        self.assertIn("100-125", text)
        self.assertEqual(chunks[-1]["chatbot_diagnostics"]["selected_tier"], "instant_rule")
        requests_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_missing_live_mandi_data_is_not_presented_as_live_price(
        self,
        kb_answer,
        weather,
        market,
    ):
        kb_answer.return_value = {"answer": None}
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "data_source": "unavailable",
        }
        market.return_value = {
            "status": "unavailable",
            "is_live": False,
            "top_crops": [],
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "What is wheat mandi price today?",
            self.ctx,
            language="en",
            fast_mode=True,
        )

        self.assertIn("No current official arrival row", result["response"])
        self.assertNotIn("2,425", result["response"])
        self.assertNotIn("2425", result["response"])
        self.assertIn(
            "Agmarknet official feed checked - no current official row",
            result["sources"],
        )
        self.assertEqual(result["ai_data_quality"]["status"], "degraded")

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_pesticide_dose_requires_an_icar_source(self, kb_answer, weather):
        kb_answer.return_value = {"answer": None}
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "wheat rust pesticide dose?",
            self.ctx,
            language="en",
            fast_mode=True,
        )

        contains_dose = bool(re.search(r"\d+(?:\.\d+)?(?:%|ml/L|kg/ha)", result["response"]))
        if contains_dose:
            self.assertTrue(
                any("icar" in source.lower() for source in result["sources"]),
                result,
            )
