"""Tests for ``regcite check`` — the check logic and the CLI command."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from regcite.checks import run_check
from regcite.cli import app
from regcite.config import Config

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sample_project"


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
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='myproj'\n\n"
        "[tool.regcite]\n"
        "rulebook_version = '2024-07-09'\n"
        "instruments = ['CRR', 'PRA_RULEBOOK', 'PS', 'SS']\n"
        "source_paths = ['src']\n"
    )
    return tmp_path


@pytest.fixture
def dirty_project(tmp_path):
    """A project that includes dynamic.py — has both a parse failure and an unresolved citation."""
    pkg = tmp_path / "src" / "myproj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    shutil.copy(FIXTURE_ROOT / "sa.py", pkg / "sa.py")
    shutil.copy(FIXTURE_ROOT / "dynamic.py", pkg / "dynamic.py")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='myproj'\n\n[tool.regcite]\nsource_paths = ['src']\n"
    )
    return tmp_path


@pytest.fixture
def unknown_article_project(tmp_path):
    """Project with a syntactically valid but out-of-index citation."""
    pkg = tmp_path / "src" / "myproj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "exotic.py").write_text(
        "from regcite import cites\n\n@cites('CRR Art. 999')\ndef f():\n    pass\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='myproj'\n\n[tool.regcite]\nsource_paths = ['src']\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Programmatic API
# ---------------------------------------------------------------------------


class TestRunCheck:
    def test_clean_project_has_no_failing_results(self, clean_project):
        cfg = Config(
            instruments=("CRR", "PRA_RULEBOOK", "PS", "SS"),
            source_paths=("src",),
            project_root=clean_project,
        )
        report = run_check(cfg)
        assert report.ok
        assert report.total_citations == 7  # 3 from sa.py + 4 from irb.py

    def test_dirty_project_reports_parse_failure(self, dirty_project):
        cfg = Config(source_paths=("src",), project_root=dirty_project)
        report = run_check(cfg)
        kinds = {r.kind for r in report.results}
        assert "parse_failure" in kinds
        assert not report.ok

    def test_dirty_project_reports_unresolved(self, dirty_project):
        cfg = Config(source_paths=("src",), project_root=dirty_project)
        report = run_check(cfg)
        kinds = {r.kind for r in report.results}
        assert "unresolved" in kinds

    def test_unknown_article_reported(self, unknown_article_project):
        cfg = Config(source_paths=("src",), project_root=unknown_article_project)
        report = run_check(cfg)
        kinds = [r.kind for r in report.results]
        assert "unknown_article" in kinds
        assert not report.ok

    def test_instrument_allowlist(self, clean_project):
        # Restricting instruments rejects the SS1/23 citation in irb.py.
        cfg = Config(
            instruments=("CRR",),
            source_paths=("src",),
            project_root=clean_project,
        )
        report = run_check(cfg)
        kinds = [r.kind for r in report.results]
        assert "unknown_instrument" in kinds


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCli:
    def test_clean_project_exit_zero(self, runner, clean_project):
        result = runner.invoke(app, ["check", "--project", str(clean_project)])
        assert result.exit_code == 0, result.stderr
        assert "no issues found" in result.stdout

    def test_dirty_project_exit_one(self, runner, dirty_project):
        result = runner.invoke(app, ["check", "--project", str(dirty_project)])
        assert result.exit_code == 1
        assert "parse_failure" in result.stderr

    def test_unknown_article_exit_one(self, runner, unknown_article_project):
        result = runner.invoke(app, ["check", "--project", str(unknown_article_project)])
        assert result.exit_code == 1
        assert "Article 999" in result.stderr

    def test_version_flag(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "regcite " in result.stdout

    def test_explicit_paths_argument(self, runner, clean_project):
        result = runner.invoke(
            app,
            ["check", str(clean_project / "src"), "--project", str(clean_project)],
        )
        assert result.exit_code == 0
