from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_CROP_INFO, INTENT_WEATHER


class CropQuestionIntentTests(SimpleTestCase):
    def test_explanations_about_drainage_are_not_weather_forecasts(self):
        service = ChatIntelligenceService()
        for query in (
            "Explain why wheat needs drainage after heavy rain. Please answer in three short points.",
            "Why does waterlogging harm wheat after rain?",
            "Gehu mein barish ke baad drainage kyun zaroori hai?",
            "गेहूं में बारिश के बाद जल निकासी क्यों जरूरी है?",
        ):
            with self.subTest(query=query):
                self.assertEqual(service.classify_query(query)[0], INTENT_CROP_INFO)

    def test_forecast_and_current_weather_questions_remain_weather(self):
        service = ChatIntelligenceService()
        for query in ("Will heavy rain affect wheat tomorrow?", "kal ka mausam kaisa hoga", "आज बारिश होगी क्या?"):
            with self.subTest(query=query):
                self.assertEqual(service.classify_query(query)[0], INTENT_WEATHER)
