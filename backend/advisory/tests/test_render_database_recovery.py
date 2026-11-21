"""Recovery must not overwrite the replacement database or claim data loss."""

import contextlib
import importlib.util
import io
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "render_preflight", ROOT / "scripts/render_preflight.py"
)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class RenderDatabaseRecoveryTests(unittest.TestCase):
    def test_database_binding_comes_from_the_blueprint_database(self):
        # The manual replacement (agri-advisory-db-v2) is gone; the web service
        # is wired to the Blueprint database, so no credential lives in Git.
        config = yaml.safe_load((ROOT / "render.yaml").read_text())
        web = next(s for s in config["services"] if s["name"] == "agri-advisory-web")
        database = next(v for v in web["envVars"] if v["key"] == "DATABASE_URL")
        self.assertEqual(database["fromDatabase"], {"name": "agri-advisory-db", "property": "connectionString"})
        self.assertIn("agri-advisory-db", {d["name"] for d in config["databases"]})

    def test_dns_failure_does_not_claim_permanent_data_loss(self):
        stderr = io.StringIO()
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://u:secret@db.invalid/app"}), \
                patch.object(preflight.socket, "getaddrinfo", side_effect=socket.gaierror()), \
                contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            preflight.main()
        message = stderr.getvalue()
        self.assertIn("suspended", message)
        self.assertNotIn("not recoverable", message)
        self.assertNotIn("instance is gone", message)
        self.assertNotIn("secret", message)
