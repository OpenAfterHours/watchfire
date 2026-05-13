"""Tests for the bundled rulebook index."""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from watchfire import Citation, parse_citation
from watchfire.index import covers, load_index

EXPECTED_ARTICLES = {4, 92, 107, 111, 113, 114, 142, 143, 153, 154, 166}


@pytest.fixture(scope="module")
def index() -> pl.DataFrame:
    return load_index()


class TestSchema:
    def test_required_columns_present(self, index):
        expected = {
            "instrument",
            "instrument_id",
            "article",
            "paragraph",
            "point",
            "subpoint",
            "title",
            "version",
            "content_text",
            "content_hash",
            "url",
        }
        assert expected.issubset(set(index.columns))

    def test_non_empty(self, index):
        assert index.height > 0

    def test_version_pinned(self, index):
        versions = index.select("version").unique().to_series().to_list()
        assert versions == [date(2024, 7, 9)]

    def test_content_hash_is_sha256(self, index):
        import hashlib

        for row in index.iter_rows(named=True):
            assert (
                row["content_hash"]
                == hashlib.sha256(row["content_text"].encode("utf-8")).hexdigest()
            )


class TestArticleCoverage:
    def test_every_required_article_present(self, index):
        present = set(
            index.filter(pl.col("instrument") == "CRR")
            .select("article")
            .unique()
            .to_series()
            .to_list()
        )
        missing = EXPECTED_ARTICLES - present
        assert not missing, f"index is missing CRR articles: {sorted(missing)}"

    def test_article_4_definitions_indexed(self, index):
        # rwa_calculator depends on (1)(75), (1)(78), (1)(79) — make
        # sure the specific definition paragraphs are present.
        defs = index.filter(
            (pl.col("instrument") == "CRR") & (pl.col("article") == 4) & (pl.col("paragraph") == 1)
        )
        points = set(defs.select("point").to_series().to_list())
        assert {"75", "78", "79"}.issubset(points)


class TestCovers:
    def test_covers_known_article(self, index):
        assert covers(index, parse_citation("CRR Art. 153"))

    def test_covers_paragraph_via_article(self, index):
        # The index records the article; a citation to a paragraph
        # within that article is considered covered for v0.1.
        assert covers(index, parse_citation("CRR Art. 153(1)(a)"))

    def test_does_not_cover_unknown_article(self, index):
        assert not covers(index, Citation(instrument="CRR", article=999))

    def test_does_not_cover_unknown_instrument(self, index):
        assert not covers(index, Citation(instrument="SS", instrument_id="SS99/99"))


class TestOverride:
    def test_can_load_custom_index_from_path(self, tmp_path, index):
        out = tmp_path / "custom.parquet"
        index.write_parquet(out)
        loaded = load_index(out)
        assert loaded.height == index.height
