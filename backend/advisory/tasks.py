"""Background tasks (Celery). Enable when Redis/worker is configured."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def refresh_location_cache():
    """Placeholder for periodic cache refresh."""
    logger.info("refresh_location_cache: no-op (configure Celery to enable)")
    return {"status": "skipped"}
