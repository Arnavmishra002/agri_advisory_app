from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.market_data_quality import filter_fresh_live_rows, parse_market_datetime
from advisory.services.crop_recommendation_engine import CropRecommendationEngine


class MarketFreshnessPrecisionTests(SimpleTestCase):
    def test_explicit_timestamp_is_not_replaced_by_assumed_release_time(self):
        value = "2026-09-09T08:00:00+05:30"
        self.assertEqual(parse_market_datetime(value), datetime(2026, 9, 9, 2, 30, tzinfo=timezone.utc))

    def test_nonfinite_prices_are_not_accepted(self):
        for price in ("NaN", "Infinity", float("inf")):
            rows, _, _ = filter_fresh_live_rows(
                [{"is_live": True, "reported_date": "09-09-2026", "modal_price": price}],
                now=datetime(2026, 9, 9, 6, tzinfo=timezone.utc),
            )
            self.assertEqual(rows, [])

    def test_stale_rows_cannot_influence_recommendations_despite_live_flag(self):
        engine = CropRecommendationEngine()
        data = {"is_live": True, "top_crops": [
            {"crop_name": "Wheat", "is_live": True, "reported_date": "01-01-2020", "modal_price": 99999},
        ]}
        self.assertEqual(engine._build_market_price_map(data), {})

    def test_undated_rows_cannot_inherit_today_from_response(self):
        data = {"is_live": True, "timestamp": "2026-09-09T06:00:00Z", "top_crops": [
            {"crop_name": "Wheat", "is_live": True, "modal_price": 2500},
        ]}
        self.assertEqual(CropRecommendationEngine()._build_market_price_map(data), {})

    def test_fresh_dated_price_is_preserved_with_age(self):
        data = {"is_live": True, "data_source": "Agmarknet", "top_crops": [
            {"crop_name": "Wheat", "is_live": True, "reported_date": "2026-09-09T08:00:00+05:30", "modal_price": 2500},
        ]}
        with patch("advisory.services.market_data_quality.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 9, 9, 3, tzinfo=timezone.utc)
            result = CropRecommendationEngine()._build_market_price_map(data)
        self.assertEqual(result["wheat"]["modal_price"], 2500)
        self.assertEqual(result["wheat"]["data_age_minutes"], 30)

    def test_future_publication_time_is_not_current(self):
        rows, _, _ = filter_fresh_live_rows(
            [{"is_live": True, "reported_date": "2026-09-09T18:00:00+05:30", "modal_price": 2500}],
            now=datetime(2026, 9, 9, 6, tzinfo=timezone.utc),
        )
        self.assertEqual(rows, [])
