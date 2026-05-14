"""Command-line entry point for the index builder."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from scripts.build_index.crr import TOC_URL, iter_crr_rows
from scripts.build_index.http import default_cache_dir
from scripts.build_index.manifest import write_manifest
from scripts.build_index.pra import iter_pra_rows
from scripts.build_index.schema import SNAPSHOT_VERSION, to_dataframe

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "src" / "watchfire" / "data" / "index.parquet"
MANIFEST_OUTPUT = REPO_ROOT / "src" / "watchfire" / "data" / "index.manifest.json"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.build_index",
        description="Rebuild the bundled watchfire rulebook index parquet.",
    )
    parser.add_argument(
        "--only",
        choices=["crr", "pra"],
        help="Build only one instrument family (default: all).",
    )
    parser.add_argument(
        "--snapshot-date",
        type=_parse_date,
        default=SNAPSHOT_VERSION,
        help="Override the version date stamped on every row (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=default_cache_dir(REPO_ROOT),
        help="HTTP cache directory (default: .cache/legislation under the repo root).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass the HTTP cache and refetch every URL.",
    )
    args = parser.parse_args(argv)

    rows: list = []
    if args.only != "pra":
        rows.extend(iter_crr_rows(args.cache_dir, refresh=args.refresh))
    if args.only != "crr":
        rows.extend(iter_pra_rows())

    # Stamp every row with the requested snapshot date.
    if args.snapshot_date != SNAPSHOT_VERSION:
        rows = [_with_version(r, args.snapshot_date) for r in rows]

    df = to_dataframe(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT)
    write_manifest(
        parquet_path=OUTPUT,
        manifest_path=MANIFEST_OUTPUT,
        df=df,
        snapshot_date=args.snapshot_date,
        source_toc_url=TOC_URL,
    )
    print(f"wrote {OUTPUT} ({df.height} rows)")
    print(f"wrote {MANIFEST_OUTPUT}")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _with_version(row, snapshot_date: date):  # noqa: ANN001 - Row dataclass
    from dataclasses import replace

    return replace(row, version=snapshot_date)


if __name__ == "__main__":
    main()
