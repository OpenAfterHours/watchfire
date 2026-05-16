"""Load the bundled rulebook index.

The index is shipped inside the wheel at ``watchfire/data/index.parquet``.
From v0.2 it covers the full UK-retained CRR (Regulation EU 575/2013)
scraped from legislation.gov.uk at build time, plus curated PRA SS / PS
and PRA Rulebook entries. The runtime never re-fetches; rebuilding goes
through ``python -m scripts.build_index`` (requires the ``build`` extra).

The schema is:

    instrument: Utf8         CRR | PRA_RULEBOOK | PS | SS | DELEGATED_REG
    instrument_id: Utf8?     "PS9/24", "Credit Risk", "2018/171", or null
    article: Utf8?           Article identifier for article-structured instruments
                             (digit strings; letter-suffixed forms like "92a" are
                             stored as-is)
    paragraph: Utf8?         Numbered paragraph within an article
    point: Utf8?             Point label ("a", "75", ...)
    subpoint: Utf8?          Sub-point ("ii", ...)
    section: Utf8?           Dotted section path for PRA SS/PS, e.g. "2.5.1"
    title: Utf8              Human-readable article title
    version: Date            Pinned snapshot date
    content_text: Utf8       Statutory text from the source document
    content_hash: Utf8       sha256 of content_text, used by `stale` in v0.2
    url: Utf8                Source URL on legislation.gov.uk
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import polars as pl

from watchfire.model import Citation

__all__ = ["INDEX_RESOURCE", "covers", "load_index", "title_for"]

INDEX_RESOURCE = ("watchfire.data", "index.parquet")


def load_index(path: str | Path | None = None) -> pl.DataFrame:
    """Return the bundled rulebook index as a Polars DataFrame.

    Args:
        path: Optional override pointing at a parquet file with the same
            schema. Useful for tests and for downstream users who want
            to extend the index.

    Returns:
        A ``polars.DataFrame``. Empty rows are never present; the index
        is small enough that loading it eagerly is fine.
    """

    if path is not None:
        return pl.read_parquet(path)
    resource = resources.files(INDEX_RESOURCE[0]).joinpath(INDEX_RESOURCE[1])
    with resources.as_file(resource) as p:
        return pl.read_parquet(p)


def covers(index: pl.DataFrame, citation: Citation) -> bool:
    """Return True if ``citation`` is covered by ``index``.

    "Covered" means the index contains at least one row for the
    citation's instrument and instrument_id, and — for article-structured
    instruments — the cited article. Sub-article granularity (paragraph,
    point) is *not* required for coverage in v0.1: a citation to
    ``CRR Art. 153(1)(a)`` is satisfied by the presence of any row
    referencing Article 153, because the article is what the index
    promises to track at this stage.
    """

    df = index.filter(pl.col("instrument") == citation.instrument)
    if citation.instrument_id is not None:
        df = df.filter(pl.col("instrument_id") == citation.instrument_id)
    if citation.article is not None and "article" in df.columns:
        df = df.filter(pl.col("article") == citation.article)
    return df.height > 0


def title_for(index: pl.DataFrame, citation: Citation) -> str | None:
    """Return the index ``title`` for the article matching ``citation``, or ``None``.

    Matches on the same instrument/instrument_id/article triple that
    :func:`covers` uses. If multiple rows match (sub-article granularity),
    the first row's title is returned — for v0.1 every row in a given
    article shares the same title. Returns ``None`` if no row matches.
    """

    df = index.filter(pl.col("instrument") == citation.instrument)
    if citation.instrument_id is not None:
        df = df.filter(pl.col("instrument_id") == citation.instrument_id)
    if citation.article is not None and "article" in df.columns:
        df = df.filter(pl.col("article") == citation.article)
    if df.height == 0 or "title" not in df.columns:
        return None
    value = df.select("title").row(0)[0]
    return value if isinstance(value, str) else None
