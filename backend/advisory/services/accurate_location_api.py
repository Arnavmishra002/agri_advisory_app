"""DEPRECATED / REMOVED — dead module (2026 cleanup).

``AccurateLocationAPI`` had ZERO importers. Location resolution is handled by
``location_context.py`` (the real resolver used across the app). This tombstone
keeps the module import-safe while removing the dead code.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AccurateLocationAPI:  # pragma: no cover - deprecated shell
    """Removed. Use ``location_context`` for location resolution."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "AccurateLocationAPI was removed (dead code). Use location_context."
        )


def get_accurate_location(query: str) -> Dict[str, Any]:  # pragma: no cover
    raise NotImplementedError(
        "get_accurate_location was removed. Use location_context resolution."
    )


accurate_location_api = None  # was AccurateLocationAPI(); removed dead singleton
