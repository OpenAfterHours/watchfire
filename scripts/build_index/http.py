"""Cached HTTP client for legislation.gov.uk fetches.

Build-time only — runtime never imports this module. The cache lives
under ``.cache/`` at the repo root (gitignored); cache hits skip the
network entirely so reruns are fast and offline-safe.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Final

import httpx

USER_AGENT: Final = "watchfire-index-builder/0.2 (+https://github.com/OpenAfterHours/watchfire)"
RATE_LIMIT_SECONDS: Final = 0.25


def make_client(timeout: float = 30.0) -> httpx.Client:
    """Return a configured ``httpx.Client`` for legislation.gov.uk."""

    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "application/xml"},
        timeout=timeout,
        transport=httpx.HTTPTransport(retries=3),
        follow_redirects=True,
    )


def get_cached(
    client: httpx.Client,
    url: str,
    cache_path: Path,
    *,
    refresh: bool = False,
) -> bytes:
    """Fetch ``url`` with on-disk caching at ``cache_path``.

    Returns the response body bytes. If the cache file exists and
    ``refresh`` is False the cached bytes are returned immediately
    without contacting the network. After a live fetch we sleep
    :data:`RATE_LIMIT_SECONDS` to stay polite.
    """

    if cache_path.exists() and not refresh:
        return cache_path.read_bytes()
    response = client.get(url)
    response.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(response.content)
    time.sleep(RATE_LIMIT_SECONDS)
    return response.content


def default_cache_dir(repo_root: Path) -> Path:
    """Return the default cache directory for HTTP fetches."""

    return repo_root / ".cache" / "legislation"
