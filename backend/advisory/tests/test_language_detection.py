from django.test import SimpleTestCase

from advisory.services.language_service import detect_query_language


class QueryLanguageDetectionTests(SimpleTestCase):
    def test_detects_hinglish_weather_question(self):
        self.assertEqual(
            detect_query_language("kal ka mausam Kaisa hoga", fallback="hi"),
            "hinglish",
        )

    def test_detects_major_indian_scripts(self):
        cases = {
            "আগামীকাল বৃষ্টি হবে?": "bn",
            "రేపు వర్షం పడుతుందా?": "te",
            "நாளை மழை பெய்யுமா?": "ta",
            "કાલે વરસાદ પડશે?": "gu",
            "ನಾಳೆ ಮಳೆ ಬರುತ್ತದೆಯೇ?": "kn",
            "നാളെ മഴ പെയ്യുമോ?": "ml",
            "ਕੱਲ੍ਹ ਮੀਂਹ ਪਵੇਗਾ?": "pa",
            "هل ستمطر غدا": "ur",
            "ᱜᱟᱯᱟ ᱫᱟᱜ ᱵᱟᱹᱨᱤᱥ ᱟ": "sat",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(detect_query_language(query), expected)

    def test_uses_selected_devanagari_language_as_fallback(self):
        self.assertEqual(detect_query_language("उद्या पाऊस पडेल का?", fallback="mr"), "mr")
