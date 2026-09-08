"""Fail a Render build fast, and legibly, when its database is gone.

Why this exists. On 2026-09-08 a deploy died like this:

    psycopg2.OperationalError: could not translate host name
      "dpg-d9o434u417fc73eg8fg0-a" to address: Name or service not known

Buried under a hundred lines of Django traceback, and only after npm ci, a
full vite build and a pip install had already run -- about three minutes of
work thrown away to learn one fact. The fact itself was simple: Render's free
PostgreSQL instances are deleted 30 days after creation, the instance behind
DATABASE_URL no longer existed, and its internal hostname had stopped
resolving.

That will happen again on every free-tier database, on a 30-day clock. So this
runs first, costs milliseconds, and says the one thing worth saying.

It deliberately does NOT let the build continue when the database is missing.
Shipping the app against a schema that was never migrated would be exactly the
confident-answer-over-missing-data failure the rest of this system refuses.
"""

from __future__ import annotations

import os
import socket
import sys
from urllib.parse import urlparse

RESET, RED, YELLOW = "\033[0m", "\033[31m", "\033[33m"


def fail(headline: str, *lines: str) -> None:
    print(f"\n{RED}preflight: {headline}{RESET}", file=sys.stderr)
    for line in lines:
        print(f"  {line}", file=sys.stderr)
    print("", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        fail(
            "DATABASE_URL is not set.",
            "Render injects it from the `databases:` block in render.yaml.",
            "Check the web service's Environment tab for the DATABASE_URL entry.",
        )

    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 5432
    if not host:
        fail("DATABASE_URL has no hostname.", f"Value parsed as: {parsed.scheme}://...")

    try:
        socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        fail(
            f"the database host {host!r} does not resolve.",
            "This is a DNS failure, not a connection failure: the instance is gone,",
            "not merely down. Render deletes free PostgreSQL instances 30 days after",
            "they are created.",
            "",
            "Fix: create a new PostgreSQL instance in the Render dashboard and point",
            "this service's DATABASE_URL at it, then redeploy. Free-tier instances",
            "have no backups, so the previous data is not recoverable.",
        )

    # Reachability is a softer signal: a database can be briefly unreachable while
    # still existing, and migrate itself will report that properly.
    try:
        with socket.create_connection((host, port), timeout=10):
            pass
    except OSError as exc:
        print(
            f"{YELLOW}preflight: {host}:{port} resolves but is not accepting "
            f"connections yet ({exc}). Continuing; migrate will report the "
            f"outcome.{RESET}",
            file=sys.stderr,
        )
        return

    print(f"preflight: database host {host}:{port} resolves and accepts connections.")


if __name__ == "__main__":
    main()
