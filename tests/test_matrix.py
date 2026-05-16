"""Tests for ``watchfire matrix`` — the engine, renderers, and CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from watchfire.cli import app
from watchfire.config import Config
from watchfire.matrix import (
    MatrixCitationSite,
    MatrixEntry,
    MatrixReport,
    _point_sort,
    _sort_key,
    render_json,
    render_markdown,
    render_text,
    run_matrix,
)
from watchfire.model import Citation

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sample_project"

_PYPROJECT_DEFAULT = (
    "[project]\nname='myproj'\n\n"
    "[tool.watchfire]\n"
    "rulebook_version = '2024-07-09'\n"
    "instruments = ['CRR', 'PRA_RULEBOOK', 'PS', 'SS']\n"
    "source_paths = ['src']\n"
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_project(tmp_path):
    """A project containing only the well-formed sa.py and irb.py."""
    pkg = tmp_path / "src" / "myproj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    shutil.copy(FIXTURE_ROOT / "sa.py", pkg / "sa.py")
    shutil.copy(FIXTURE_ROOT / "irb.py", pkg / "irb.py")
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT_DEFAULT)
    return tmp_path


@pytest.fixture
def dirty_project(tmp_path):
    """A project including dynamic.py — has a parse failure and an unresolved citation."""
    pkg = tmp_path / "src" / "myproj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    shutil.copy(FIXTURE_ROOT / "sa.py", pkg / "sa.py")
    shutil.copy(FIXTURE_ROOT / "dynamic.py", pkg / "dynamic.py")
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT_DEFAULT)
    return tmp_path


@pytest.fixture
def two_points_project(tmp_path):
    """Two functions citing the same article at different sub-points."""
    pkg = tmp_path / "src" / "myproj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "calc.py").write_text(
        "from watchfire import cites\n\n"
        "@cites('CRR Art. 113(1)')\n"
        "def first(): pass\n\n"
        "@cites('CRR Art. 113(2)')\n"
        "def second(): pass\n"
    )
    (tmp_path / "pyproject.toml").write_text(_PYPROJECT_DEFAULT)
    return tmp_path


# ---------------------------------------------------------------------------
# Programmatic API
# ---------------------------------------------------------------------------


class TestRunMatrix:
    def test_empty_project_returns_empty_report(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT_DEFAULT)
        cfg = Config(source_paths=("src",), project_root=tmp_path)
        report = run_matrix(cfg)
        assert report.entries == ()
        assert report.total_citations == 0
        assert report.total_functions == 0
        assert report.parse_failures == 0
        assert report.unresolved == 0

    def test_clean_project_article_rollup(self, clean_project):
        cfg = Config(source_paths=("src",), project_root=clean_project)
        report = run_matrix(cfg)
        # 7 citations across 7 distinct articles (each citation is to a
        # different article); rollup mode produces one entry per article.
        assert len(report.entries) == 7
        assert report.total_citations == 7

        art_153 = next(e for e in report.entries if e.key.article == "153")
        assert len(art_153.sites) == 1
        # The rollup key drops paragraph/point; the *site* retains them.
        assert art_153.key.paragraph is None
        assert art_153.key.point is None
        assert art_153.sites[0].citation.canonical() == "CRR Art. 153(1)(a)"

    def test_specificity_full_does_not_collapse(self, two_points_project):
        cfg = Config(source_paths=("src",), project_root=two_points_project)
        report = run_matrix(cfg, specificity="full")
        # Two distinct entries: Art. 113(1) and Art. 113(2).
        assert len(report.entries) == 2
        canon = sorted(e.key.canonical() for e in report.entries)
        assert canon == ["CRR Art. 113(1)", "CRR Art. 113(2)"]

    def test_multi_function_per_article_rollup(self, two_points_project):
        cfg = Config(source_paths=("src",), project_root=two_points_project)
        report = run_matrix(cfg, specificity="article")
        # Both sub-points roll up into a single Art. 113 entry.
        assert len(report.entries) == 1
        entry = report.entries[0]
        assert entry.key.article == "113"
        assert len(entry.sites) == 2

    def test_instrument_ordering_crr_before_ss(self, clean_project):
        cfg = Config(source_paths=("src",), project_root=clean_project)
        report = run_matrix(cfg)
        instruments = [e.key.instrument for e in report.entries]
        # CRR entries appear before the SS1/23 entry.
        last_crr = max(i for i, inst in enumerate(instruments) if inst == "CRR")
        first_ss = next(i for i, inst in enumerate(instruments) if inst == "SS")
        assert last_crr < first_ss

    def test_dirty_project_counts_failures_does_not_fail(self, dirty_project):
        cfg = Config(source_paths=("src",), project_root=dirty_project)
        report = run_matrix(cfg)
        assert report.parse_failures >= 1
        assert report.unresolved >= 1
        # The constructed_literal in dynamic.py yields CRR Art. 92.
        canonicals = {e.key.canonical() for e in report.entries}
        assert "CRR Art. 92" in canonicals

    def test_title_populated_from_index(self):
        # Inject a deterministic index so this test never depends on the
        # bundled parquet's contents.
        idx = pl.DataFrame(
            {
                "instrument": ["CRR", "CRR"],
                "instrument_id": [None, None],
                "article": ["113", "153"],
                "title": ["Standardised approach risk weights", "IRB risk weights"],
            },
            schema={
                "instrument": pl.Utf8,
                "instrument_id": pl.Utf8,
                "article": pl.Utf8,
                "title": pl.Utf8,
            },
        )
        # Build a config and project without going through the fixtures.
        from watchfire.index import title_for

        assert title_for(idx, Citation(instrument="CRR", article="113")) == (
            "Standardised approach risk weights"
        )
        assert title_for(idx, Citation(instrument="CRR", article="999")) is None

    def test_filter_by_instrument_and_article(self, clean_project):
        cfg = Config(source_paths=("src",), project_root=clean_project)
        report = run_matrix(cfg, instrument_filter="CRR", article_filter="153")
        assert len(report.entries) == 1
        assert report.entries[0].key.article == "153"
        # The unfiltered totals still reflect every discovered citation;
        # only the rendered entries list is narrowed by filters.
        assert report.total_citations == 7


# ---------------------------------------------------------------------------
# Renderers (unit-level)
# ---------------------------------------------------------------------------


def _sample_report() -> MatrixReport:
    site = MatrixCitationSite(
        file=Path("/proj/src/myproj/sa.py"),
        line=6,
        function="calculate_sa_rwa",
        citation=Citation(instrument="CRR", article="113", raw="CRR Art. 113"),
    )
    entry = MatrixEntry(
        key=Citation(instrument="CRR", article="113"),
        title="Standardised approach risk weights",
        sites=(site,),
    )
    return MatrixReport(
        entries=(entry,),
        parse_failures=0,
        unresolved=0,
        total_functions=1,
        total_citations=1,
    )


class TestRenderers:
    def test_render_text_contains_canonical_and_function(self):
        out = render_text(_sample_report(), project_root=Path("/proj"))
        assert "CRR Art. 113" in out
        assert "calculate_sa_rwa" in out
        assert "src/myproj/sa.py:6" in out  # POSIX-relative

    def test_render_text_not_in_index_placeholder(self):
        report = MatrixReport(
            entries=(
                MatrixEntry(
                    key=Citation(instrument="CRR", article="999"),
                    title=None,
                    sites=(
                        MatrixCitationSite(
                            file=Path("/proj/src/x.py"),
                            line=1,
                            function="f",
                            citation=Citation(instrument="CRR", article="999"),
                        ),
                    ),
                ),
            ),
            parse_failures=0,
            unresolved=0,
            total_functions=1,
            total_citations=1,
        )
        out = render_text(report, project_root=Path("/proj"))
        assert "(not in index)" in out

    def test_render_markdown_table_header(self):
        out = render_markdown(_sample_report(), project_root=Path("/proj"))
        assert out.startswith("| Citation | Title | File | Line | Function |")
        assert "| CRR Art. 113 |" in out
        assert "src/myproj/sa.py" in out

    def test_render_json_schema(self):
        cfg = Config(project_root=Path("/proj"))
        doc = json.loads(render_json(_sample_report(), project_root=Path("/proj"), config=cfg))
        assert doc["version"] == 1
        assert doc["total_entries"] == 1
        assert doc["entries"][0]["key"] == "CRR Art. 113"
        assert doc["entries"][0]["sites"][0]["function"] == "calculate_sa_rwa"

    def test_render_text_footer_when_failures_present(self):
        report = MatrixReport(
            entries=(),
            parse_failures=2,
            unresolved=1,
            total_functions=0,
            total_citations=0,
        )
        out = render_text(report, project_root=Path("/proj"))
        assert "parse-failure" in out
        assert "unresolved" in out


# ---------------------------------------------------------------------------
# Sort key
# ---------------------------------------------------------------------------


class TestSortKey:
    def test_instrument_buckets_in_canonical_order(self):
        crr = Citation(instrument="CRR", article="1")
        ss = Citation(instrument="SS", instrument_id="SS1/23", section=("1",))
        assert _sort_key(crr) < _sort_key(ss)

    def test_articles_sort_numerically_not_lexically(self):
        # "4" < "11" < "111": lexicographic would put "11" < "4".
        a4 = Citation(instrument="CRR", article="4")
        a11 = Citation(instrument="CRR", article="11")
        a111 = Citation(instrument="CRR", article="111")
        keys = sorted([a111, a4, a11], key=_sort_key)
        assert [c.article for c in keys] == ["4", "11", "111"]

    def test_alphanumeric_articles_sort_naturally(self):
        # "92" < "92a" < "92b" < "93" — letter-suffixed articles sort
        # immediately after their bare digit form.
        a92 = Citation(instrument="CRR", article="92")
        a92a = Citation(instrument="CRR", article="92a")
        a92b = Citation(instrument="CRR", article="92b")
        a93 = Citation(instrument="CRR", article="93")
        keys = sorted([a93, a92b, a92a, a92], key=_sort_key)
        assert [c.article for c in keys] == ["92", "92a", "92b", "93"]

    @pytest.mark.parametrize(
        ("point", "bucket"),
        [(None, 0), ("a", 1), ("b", 1), ("75", 2)],
    )
    def test_point_buckets(self, point, bucket):
        assert _point_sort(point)[0] == bucket

    def test_alpha_before_numeric_points(self):
        # Within the same article/paragraph, "a" should sort before "75".
        alpha = Citation(instrument="CRR", article="4", paragraph="1", point="a")
        numeric = Citation(instrument="CRR", article="4", paragraph="1", point="75")
        assert _sort_key(alpha) < _sort_key(numeric)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def test_text_format_clean_project_exit_zero(self, runner, clean_project):
        result = runner.invoke(app, ["matrix", "--project", str(clean_project)])
        assert result.exit_code == 0, result.stderr
        assert "CRR Art. 113" in result.stdout
        assert "calculate_sa_rwa" in result.stdout

    def test_markdown_format(self, runner, clean_project):
        result = runner.invoke(
            app, ["matrix", "--project", str(clean_project), "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert result.stdout.startswith("| Citation |")

    def test_json_format_parses(self, runner, clean_project):
        result = runner.invoke(app, ["matrix", "--project", str(clean_project), "--format", "json"])
        assert result.exit_code == 0
        doc = json.loads(result.stdout)
        assert doc["version"] == 1
        assert isinstance(doc["entries"], list)
        assert doc["rulebook_version"] == "2024-07-09"

    def test_dirty_project_still_exit_zero(self, runner, dirty_project):
        result = runner.invoke(app, ["matrix", "--project", str(dirty_project)])
        assert result.exit_code == 0
        assert "parse-failure" in result.stdout

    def test_filter_no_matches_exit_zero(self, runner, clean_project):
        result = runner.invoke(
            app,
            [
                "matrix",
                "--project",
                str(clean_project),
                "--instrument",
                "CRR",
                "--article",
                "999",
            ],
        )
        assert result.exit_code == 0
        assert "no entries match" in result.stdout

    def test_invalid_format_exit_two(self, runner, clean_project):
        result = runner.invoke(app, ["matrix", "--project", str(clean_project), "--format", "yaml"])
        assert result.exit_code == 2
        assert "--format must be" in result.stderr

    def test_invalid_specificity_exit_two(self, runner, clean_project):
        result = runner.invoke(
            app, ["matrix", "--project", str(clean_project), "--specificity", "weird"]
        )
        assert result.exit_code == 2
        assert "--specificity must be" in result.stderr
