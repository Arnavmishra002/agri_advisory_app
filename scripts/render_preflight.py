"""Fail early on missing database configuration or DNS failure.

DNS does not distinguish a deleted database from a suspended database,
incorrect region/hostname, or a temporary resolver outage. Migrations remain
the authoritative schema and connection check after this preflight.
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
            "Set the database's internal connection URL in Render Environment.",
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
            "The database may be suspended, expired, deleted, or temporarily unreachable.",
            "Check its status and recovery deadline in Render before replacing it.",
            "Verify DATABASE_URL and that the web service uses the same region",
            "as the database when using an internal hostname. Retry after DNS recovery.",
            "Do not infer permanent data loss from this DNS failure.",
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
