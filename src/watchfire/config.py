"""Read project configuration from ``[tool.watchfire]`` in ``pyproject.toml``.

The shape is intentionally tiny: a rulebook version pin, an allowlist of
instruments, and the list of source paths to scan. Defaults apply when
the table is absent.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

__all__ = ["Config", "ConfigError", "find_pyproject", "load_config"]


class ConfigError(ValueError):
    """Raised when ``[tool.watchfire]`` is malformed."""


DEFAULT_INSTRUMENTS: tuple[str, ...] = (
    "CRR",
    "PRA_RULEBOOK",
    "PS",
    "SS",
    "DELEGATED_REG",
)
DEFAULT_SOURCE_PATHS: tuple[str, ...] = ("src",)


@dataclass(frozen=True)
class Config:
    """Resolved project configuration for ``watchfire``."""

    rulebook_version: date | None = None
    instruments: tuple[str, ...] = DEFAULT_INSTRUMENTS
    source_paths: tuple[str, ...] = DEFAULT_SOURCE_PATHS
    project_root: Path = field(default_factory=Path.cwd)

    def absolute_source_paths(self) -> list[Path]:
        return [self.project_root / p for p in self.source_paths]


def find_pyproject(start: Path | None = None) -> Path | None:
    """Walk upward from ``start`` (or cwd) looking for ``pyproject.toml``."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        py = candidate / "pyproject.toml"
        if py.is_file():
            return py
    return None


def load_config(start: Path | None = None) -> Config:
    """Load ``[tool.watchfire]`` from the nearest ``pyproject.toml``.

    Returns a :class:`Config` populated with defaults if the file or
    section is absent. Raises :class:`ConfigError` if the section is
    present but malformed (wrong types, unknown keys).
    """

    py = find_pyproject(start)
    if py is None:
        return Config(project_root=(start or Path.cwd()).resolve())

    try:
        with py.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"failed to parse {py}: {exc}") from exc

    table = data.get("tool", {}).get("watchfire", {})
    if not isinstance(table, dict):
        raise ConfigError(f"[tool.watchfire] in {py} must be a table")

    known = {"rulebook_version", "instruments", "source_paths"}
    unknown = set(table) - known
    if unknown:
        raise ConfigError(
            f"unknown keys in [tool.watchfire]: {sorted(unknown)}; accepted: {sorted(known)}"
        )

    version = _parse_version(table.get("rulebook_version"))
    instruments = _parse_string_tuple(table.get("instruments"), "instruments", DEFAULT_INSTRUMENTS)
    source_paths = _parse_string_tuple(
        table.get("source_paths"), "source_paths", DEFAULT_SOURCE_PATHS
    )

    return Config(
        rulebook_version=version,
        instruments=instruments,
        source_paths=source_paths,
        project_root=py.parent,
    )


def _parse_version(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ConfigError(
                f"rulebook_version must be ISO-8601 date (YYYY-MM-DD), got {value!r}"
            ) from exc
    raise ConfigError(f"rulebook_version must be a date or string, got {type(value).__name__}")


def _parse_string_tuple(value: object, name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be a list of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{name} must be a list of strings, got {item!r}")
        out.append(item)
    return tuple(out)
