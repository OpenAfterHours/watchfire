"""Tests for ``[tool.regcite]`` config parsing."""

from __future__ import annotations

from datetime import date

import pytest

from regcite.config import (
    DEFAULT_INSTRUMENTS,
    DEFAULT_SOURCE_PATHS,
    Config,
    ConfigError,
    find_pyproject,
    load_config,
)


@pytest.fixture
def project(tmp_path):
    def make(body: str):
        (tmp_path / "pyproject.toml").write_text(body)
        return tmp_path

    return make


class TestFindPyproject:
    def test_finds_in_current_dir(self, project):
        root = project("[project]\nname = 'x'\n")
        assert find_pyproject(root) == root / "pyproject.toml"

    def test_walks_up(self, project, tmp_path):
        root = project("[project]\nname = 'x'\n")
        nested = root / "src" / "x"
        nested.mkdir(parents=True)
        assert find_pyproject(nested) == root / "pyproject.toml"

    def test_returns_none_when_absent(self, tmp_path):
        assert find_pyproject(tmp_path) is None


class TestLoadConfig:
    def test_no_pyproject_returns_defaults(self, tmp_path):
        cfg = load_config(tmp_path)
        assert cfg.rulebook_version is None
        assert cfg.instruments == DEFAULT_INSTRUMENTS
        assert cfg.source_paths == DEFAULT_SOURCE_PATHS

    def test_no_tool_section_returns_defaults(self, project):
        root = project("[project]\nname = 'x'\n")
        cfg = load_config(root)
        assert cfg.instruments == DEFAULT_INSTRUMENTS

    def test_full_config_parsed(self, project):
        root = project(
            "[project]\nname = 'x'\n\n"
            "[tool.regcite]\n"
            "rulebook_version = '2024-07-09'\n"
            "instruments = ['CRR', 'PRA_RULEBOOK']\n"
            "source_paths = ['src', 'pkg']\n"
        )
        cfg = load_config(root)
        assert cfg.rulebook_version == date(2024, 7, 9)
        assert cfg.instruments == ("CRR", "PRA_RULEBOOK")
        assert cfg.source_paths == ("src", "pkg")
        assert cfg.project_root == root

    def test_inline_date(self, project):
        # TOML supports native dates without quotes.
        root = project("[tool.regcite]\nrulebook_version = 2024-07-09\n")
        cfg = load_config(root)
        assert cfg.rulebook_version == date(2024, 7, 9)

    def test_unknown_key_errors(self, project):
        root = project("[tool.regcite]\nfoo = 'bar'\n")
        with pytest.raises(ConfigError, match="unknown keys"):
            load_config(root)

    def test_bad_version_errors(self, project):
        root = project("[tool.regcite]\nrulebook_version = 'yesterday'\n")
        with pytest.raises(ConfigError, match="ISO-8601"):
            load_config(root)

    def test_instruments_must_be_list(self, project):
        root = project("[tool.regcite]\ninstruments = 'CRR'\n")
        with pytest.raises(ConfigError, match="instruments must be a list"):
            load_config(root)

    def test_absolute_source_paths(self, project):
        root = project("[tool.regcite]\nsource_paths = ['src', 'tests']\n")
        cfg = load_config(root)
        absolute = cfg.absolute_source_paths()
        assert absolute == [root / "src", root / "tests"]


class TestConfigDataclass:
    def test_immutable(self):
        import dataclasses

        cfg = Config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.rulebook_version = date(2024, 1, 1)  # ty: ignore[possibly-unbound-attribute]
