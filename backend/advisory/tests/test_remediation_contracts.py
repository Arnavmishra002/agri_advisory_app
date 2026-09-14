"""Regression evidence for the September audit; no live provider calls."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.services.crop_recommendation_engine import CropRecommendationEngine
from advisory.services.language_service import normalise_language_code, get_language_info


class LocationProvenanceTests(SimpleTestCase):
    def setUp(self):
        self.engine = CropRecommendationEngine()

    def test_uncovered_district_never_borrows_field_conditions(self):
        for location in ('East Godavari', 'Kakinada', 'Rajahmundry', ''):
            with self.subTest(location=location):
                profile = self.engine._resolve_location_profile(location, 'Andhra Pradesh')
                self.assertEqual(profile['_source'], 'unknown')
                for field in ('soil', 'irrigation', 'rainfall'):
                    self.assertIsNone(profile.get(field))

    def test_exact_district_is_reference_not_farmer_fact(self):
        profile = self.engine._resolve_location_profile('Lucknow', 'Uttar Pradesh')
        self.assertEqual(profile['_source'], 'district_exact')
        self.assertEqual(profile['reference_district'], 'lucknow')
        self.assertIsNone(profile.get('irrigation'))

    def test_conflicting_state_does_not_select_wrong_district(self):
        profile = self.engine._resolve_location_profile('Lucknow', 'Kerala')
        self.assertEqual(profile['_source'], 'unknown')

    def test_missing_inputs_do_not_earn_soil_or_water_points(self):
        profile = self.engine._resolve_location_profile('East Godavari', 'Andhra Pradesh')
        scored = self.engine._score_all_crops(profile, 'kharif', {}, [], {})
        self.assertTrue(scored)
        for _, _, _, reasons, factors in scored:
            for name in ('soil', 'water', 'rainfall'):
                self.assertEqual(factors[name]['points'], 0)
                self.assertEqual(factors[name]['status'], 'unknown')
            self.assertFalse(any('Water needs met' in reason for reason in reasons))


class LanguageCompatibilityTests(SimpleTestCase):
    def test_old_bodo_preference_normalises_to_brx(self):
        for code in ('bo', 'brx', 'bodo'):
            self.assertEqual(normalise_language_code(code), 'brx')
        self.assertEqual(get_language_info('brx')['bcp47'], 'brx')


class CropChatGroundingTests(SimpleTestCase):
    def test_saved_field_inputs_are_forwarded_without_guessed_values(self):
        from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_CROP_RECOMMENDATION
        from advisory.services.location_context import LocationContext
        with patch('advisory.services.chat_intelligence_service.crop_recommendation_engine.recommend_from_context', return_value={}) as recommend:
            ChatIntelligenceService()._build_official_context(
                LocationContext(latitude=26.85, longitude=80.95, display_name='Lucknow'),
                'What should I grow?', INTENT_CROP_RECOMMENDATION, [], 'en', _weather={}, _prices={},
                farmer_profile={'soil_type': 'loamy', 'irrigation_type': 'rainfed'},
            )
        self.assertEqual(recommend.call_args.kwargs['agronomic_inputs'], {'soil_type': 'loamy', 'irrigation': 'rainfed'})

    def test_unavailable_recommendations_do_not_invent_rabi_crops(self):
        from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_CROP_RECOMMENDATION
        from advisory.services.location_context import LocationContext
        answer = ChatIntelligenceService()._smart_rule_response(
            'What should I grow?', INTENT_CROP_RECOMMENDATION, [],
            LocationContext(latitude=26.85, longitude=80.95, display_name='Lucknow'), '', 'en',
        )
        self.assertIn('soil', answer.lower())
        self.assertIn('irrigation', answer.lower())
        self.assertNotIn('MSP', answer)
        self.assertNotIn('Wheat', answer)


class MarketClockBoundaryTests(SimpleTestCase):
    @patch.dict('os.environ', {'MANDI_MAX_DATA_AGE_HOURS': '24', 'MANDI_MAX_REFERENCE_AGE_DAYS': '7'})
    def test_date_only_rows_use_india_time_and_keep_exact_boundaries(self):
        from advisory.services.market_data_quality import parse_market_datetime, build_dated_official_reference
        reported = parse_market_datetime('06-09-2026')
        self.assertEqual(reported, datetime(2026, 9, 6, 3, 30, tzinfo=timezone.utc))
        row = {'modal_price': 2500, 'reported_date': '06-09-2026', 'is_live': True}
        for delta, accepted in ((timedelta(hours=24), False), (timedelta(hours=24, seconds=1), True),
                                (timedelta(days=7), True), (timedelta(days=7, seconds=1), False),
                                (timedelta(seconds=-1), False)):
            with self.subTest(delta=delta):
                rows, _, _ = build_dated_official_reference([row], now=reported + delta)
                self.assertEqual(bool(rows), accepted)


@override_settings(DEBUG=False)
class PublicMonitoringTests(SimpleTestCase):
    def test_launch_details_require_staff_before_dependency_probes(self):
        from advisory.api.monitoring_views import launch_readiness_check
        with patch('advisory.api.monitoring_views.readiness_check') as probe:
            response = launch_readiness_check(RequestFactory().get('/api/health/launch-readiness/'))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('checks', json.loads(response.content))
        probe.assert_not_called()

    def test_nonstaff_user_cannot_read_details(self):
        from advisory.api.monitoring_views import launch_readiness_check
        request = RequestFactory().get('/api/health/launch-readiness/')
        request.user = SimpleNamespace(is_authenticated=True, is_staff=False)
        self.assertEqual(launch_readiness_check(request).status_code, 403)
