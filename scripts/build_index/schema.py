"""Row schema for the rulebook index parquet.

One place to define the column dtypes used both by the build script and
documented in ``src/watchfire/index.py``'s docstring. Keep these in sync.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date

import polars as pl

# Pinned snapshot date applied to every row. Bump per rebuild.
SNAPSHOT_VERSION = date(2026, 5, 14)

# Polars dtypes for the index parquet. Keep in lockstep with the schema
# block in ``src/watchfire/index.py``.
PARQUET_SCHEMA: dict[str, pl.DataType] = {
    "instrument": pl.Utf8,
    "instrument_id": pl.Utf8,
    "article": pl.Int32,
    "paragraph": pl.Int32,
    "point": pl.Utf8,
    "subpoint": pl.Utf8,
    "section": pl.Utf8,
    "title": pl.Utf8,
    "version": pl.Date,
    "content_text": pl.Utf8,
    "content_hash": pl.Utf8,
    "url": pl.Utf8,
}


@dataclass(frozen=True)
class Row:
    """One row in the rulebook index.

    For CRR / Delegated Regulation rows: ``article`` and optionally
    ``paragraph`` / ``point`` / ``subpoint`` are populated, ``section``
    is None. For PRA SS / PS / Rulebook rows: ``section`` carries the
    dotted path (e.g. ``"2.5.1"``), the article-shaped fields are None.
    """

    instrument: str
    instrument_id: str | None
    article: int | None
    paragraph: int | None
    point: str | None
    subpoint: str | None
    section: str | None
    title: str
    content_text: str
    url: str
    version: date = SNAPSHOT_VERSION

    @property
    def content_hash(self) -> str:
        return _hash(self.content_text)

    def as_dict(self) -> dict:
        out = asdict(self)
        out["content_hash"] = self.content_hash
        return out


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def to_dataframe(rows: Iterable[Row]) -> pl.DataFrame:
    """Materialise ``rows`` into a Polars DataFrame with the pinned schema."""

    return pl.DataFrame([r.as_dict() for r in rows], schema=PARQUET_SCHEMA)
