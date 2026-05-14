"""Write the sidecar manifest describing a built parquet."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import polars as pl


def write_manifest(
    *,
    parquet_path: Path,
    manifest_path: Path,
    df: pl.DataFrame,
    snapshot_date: date,
    source_toc_url: str,
) -> None:
    """Write a JSON manifest alongside the index parquet.

    Captures snapshot date, row counts, per-instrument counts, CRR
    article count, source TOC URL, and the git SHA of the build. Gives
    downstream debuggers something to grep when a parquet looks stale.
    """

    per_instrument = df.group_by("instrument").agg(pl.len().alias("rows")).sort("instrument")
    crr_article_count = (
        df.filter(pl.col("instrument") == "CRR").select("article").drop_nulls().n_unique()
    )
    manifest = {
        "snapshot_date": snapshot_date.isoformat(),
        "total_rows": df.height,
        "rows_per_instrument": {
            row["instrument"]: row["rows"] for row in per_instrument.iter_rows(named=True)
        },
        "crr_articles": int(crr_article_count),
        "source_toc_url": source_toc_url,
        "git_sha": _git_sha(parquet_path.parent),
        "parquet_path": parquet_path.name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _git_sha(cwd: Path) -> str | None:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
        )
        return sha.decode("ascii").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
