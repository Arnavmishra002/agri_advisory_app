"""The CD pipeline must report what it actually shipped.

KrishiMitra CD run #93 finished green and its summary printed "Render: success".
Nothing had been deployed. ``RENDER_DEPLOY_HOOK_URL`` was unset, so the deploy
step took its skip branch and exited 0, the health check skipped too, and the
summary reported the *job result* -- which was, accurately and uselessly,
success. Anyone reading that summary would conclude the commit was live.

That is the same failure shape as the CSP tests that called ``skipTest`` on CI:
a green signal that means "nothing ran", presented as "everything passed". The
tests here execute the workflow's own shell against the unconfigured
environment and assert the operator is told, in words, that no service was
updated.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "deploy.yml"
)


def _load():
    with WORKFLOW.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _steps(job):
    return {step.get("id"): step["run"] for step in job["steps"] if "run" in step}


def _run(script, env, substitutions=None):
    """Execute a workflow step's shell the way the runner does."""
    for placeholder, value in (substitutions or {}).items():
        script = script.replace(placeholder, value)
    handle, output_path = tempfile.mkstemp()
    os.close(handle)
    try:
        child_env = dict(os.environ)
        child_env.update(env)
        child_env["GITHUB_OUTPUT"] = output_path
        completed = subprocess.run(
            ["bash", "-e", "-c", script],
            env=child_env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        with open(output_path, encoding="utf-8") as written:
            return completed.returncode, completed.stdout, written.read()
    finally:
        os.unlink(output_path)


class DeployStepsRecordWhatHappenedTests(unittest.TestCase):
    """The deploy job must publish its real outcome, not just its exit code."""

    def setUp(self):
        self.jobs = _load()["jobs"]
        self.render = self.jobs["deploy-render"]
        self.steps = _steps(self.render)

    def test_deploy_job_exposes_deploy_and_health_outcomes(self):
        outputs = self.render.get("outputs") or {}
        self.assertIn("deploy", outputs)
        self.assertIn("health", outputs)

    def test_unconfigured_deploy_reports_not_deployed(self):
        code, stdout, github_output = _run(
            self.steps["trigger"],
            {"RENDER_DEPLOY_HOOK_URL": "", "RENDER_SERVICE_URL": ""},
            {"${{ github.sha }}": "0" * 40},
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("deploy=NOT DEPLOYED", github_output)
        self.assertIn("RENDER_DEPLOY_HOOK_URL", github_output)

    def test_health_check_reports_that_it_never_ran(self):
        code, stdout, github_output = _run(
            self.steps["health"],
            {"RENDER_DEPLOY_HOOK_URL": "", "RENDER_SERVICE_URL": ""},
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("health=", github_output)
        self.assertIn("no deploy was triggered", github_output)

    def test_health_check_flags_a_deploy_it_could_not_verify(self):
        """Hook set, service URL missing: the deploy fired and went unverified."""
        code, stdout, github_output = _run(
            self.steps["health"],
            {
                "RENDER_DEPLOY_HOOK_URL": "https://example.invalid/hook",
                "RENDER_SERVICE_URL": "",
            },
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("health=NOT VERIFIED", github_output)


class DeploySummaryTellsTheTruthTests(unittest.TestCase):
    """The summary an operator reads must distinguish shipped from skipped."""

    ALL_GREEN = {
        "${{ needs.guard.result }}": "success",
        "${{ needs.pre-deploy-check.result }}": "success",
        "${{ needs.publish-docker.result }}": "success",
        "${{ needs.deploy-render.result }}": "success",
        "${{ github.ref_name }}": "main",
        "${{ github.sha }}": "0" * 40,
    }

    def setUp(self):
        self.script = _load()["jobs"]["deploy-summary"]["steps"][0]["run"]

    def test_summary_consumes_the_real_outcome_not_only_job_results(self):
        env = _load()["jobs"]["deploy-summary"]["steps"][0].get("env") or {}
        joined = " ".join(str(value) for value in env.values())
        self.assertIn("needs.deploy-render.outputs.deploy", joined)
        self.assertIn("needs.deploy-render.outputs.health", joined)

    def test_green_run_that_shipped_nothing_says_so(self):
        code, stdout, _ = _run(
            self.script,
            {
                "RENDER_DEPLOY": "NOT DEPLOYED (RENDER_DEPLOY_HOOK_URL secret is not set)",
                "RENDER_HEALTH": "not checked (no deploy was triggered)",
                "DOCKER_MODE": "built only (no registry credentials)",
            },
            self.ALL_GREEN,
        )
        self.assertEqual(code, 0, stdout)
        self.assertIn("shipped nothing to Render", stdout)
        self.assertIn("RENDER_DEPLOY_HOOK_URL", stdout)
        self.assertNotRegex(stdout, r"^Render:\s+success$")

    def test_real_deploy_is_not_labelled_with_the_warning(self):
        code, stdout, _ = _run(
            self.script,
            {
                "RENDER_DEPLOY": "deploy hook accepted (HTTP 200)",
                "RENDER_HEALTH": "verified live at https://example.invalid/api/health/",
                "DOCKER_MODE": "pushed to Docker Hub",
            },
            self.ALL_GREEN,
        )
        self.assertEqual(code, 0, stdout)
        self.assertNotIn("shipped nothing", stdout)
        self.assertIn("deploy hook accepted", stdout)

    def test_failed_deploy_still_fails_the_summary(self):
        substitutions = dict(self.ALL_GREEN)
        substitutions["${{ needs.deploy-render.result }}"] = "failure"
        code, stdout, _ = _run(
            self.script,
            {"RENDER_DEPLOY": "", "RENDER_HEALTH": "", "DOCKER_MODE": "pushed to Docker Hub"},
            substitutions,
        )
        self.assertEqual(code, 1, stdout)
        self.assertIn("Deployment failed.", stdout)

    def test_docker_build_only_is_not_reported_as_a_publish(self):
        mode = _load()["jobs"]["publish-docker"]["outputs"]["mode"]
        self.assertIn("push_image", mode)
        self.assertIn("built only", mode)
