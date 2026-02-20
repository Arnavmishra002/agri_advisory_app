"""
pytest configuration — automatically bootstraps Django before any test runs.
This prevents django.core.exceptions.ImproperlyConfigured across all test files.
"""
import os
import sys
import django

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set required environment variables before Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("SECRET_KEY", "test-secret-key-krishimitra-ci")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_db.sqlite3")
os.environ.setdefault(
    "DATA_GOV_IN_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44c4a1747200ff293b68cc36"
)
os.environ.setdefault("GOOGLE_AI_API_KEY", "")

def pytest_configure(config):
    """Called by pytest before collection — sets up Django."""
    try:
        django.setup()
    except RuntimeError:
        pass  # Already set up (e.g. running multiple test files)
