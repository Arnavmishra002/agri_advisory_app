"""DEPRECATED / REMOVED — dead module (2026 cleanup).

``ComprehensiveCropRecommendations`` was a ~2,300-line parallel crop-recommendation
engine with ZERO importers anywhere in the codebase. It duplicated the crop database
(stale MSPs, mojibake) and produced random suitability scores / "Simulated" market
rows — exactly the fabricated-data pattern this project forbids.

The live crop-recommendation feature is served by ``crop_recommendation_engine.py``
(real data, honest "indicative_estimate" labelling). This tombstone remains only so
an accidental future import fails loudly instead of resurrecting dead random-data code.
"""

import logging

logger = logging.getLogger(__name__)


class ComprehensiveCropRecommendations:  # pragma: no cover - deprecated shell
    """Removed. Use ``crop_recommendation_engine.CropRecommendationEngine`` instead."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ComprehensiveCropRecommendations was removed (dead code with random "
            "data). Use crop_recommendation_engine.CropRecommendationEngine."
        )
