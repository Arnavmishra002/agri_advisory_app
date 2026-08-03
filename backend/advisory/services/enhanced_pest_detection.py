"""DEPRECATED / REMOVED — dead module (2026 cleanup).

``EnhancedPestDetectionService`` called several non-existent "government" API
endpoints (e.g. icar.org.in/api/*, ppqs.gov.in/api/*, api.plantix.net/*) that are
not real public APIs, blocking the request thread on doomed calls before falling
back to a hardcoded database. It is no longer wired into any viewset (pest guidance
is served by ``ultra_dynamic_government_api`` / ``krishi_raksha_pest_service``).

This tombstone keeps ``pest_detection_service`` importable but inert so nothing
silently reintroduces the fictional-endpoint calls.
"""

import logging

logger = logging.getLogger(__name__)


class EnhancedPestDetectionService:  # pragma: no cover - deprecated shell
    """Removed. Use krishi_raksha_pest_service / ultra_dynamic_government_api."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "EnhancedPestDetectionService was removed (called fictional endpoints)."
        )


pest_detection_service = None  # was EnhancedPestDetectionService(); removed
