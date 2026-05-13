"""The ``watchfire check`` command.

Walks a project, parses every ``@cites`` decorator it finds, looks each
citation up in the bundled index, and bucketed-reports the result. The
CLI in :mod:`watchfire.cli` is a thin wrapper around :func:`run_check`.

Version-pin checking is reserved for v0.2; the placeholder is here so
the CLI surface and exit-code policy don't shift between releases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import polars as pl

from watchfire.ast_walker import (
    CitationFinding,
    ParseFailure,
    UnresolvedCitation,
    find_citations,
)
from watchfire.config import Config
from watchfire.index import covers, load_index

__all__ = ["CheckReport", "CheckResult", "run_check"]


@dataclass(frozen=True)
class CheckResult:
    """One reportable finding from ``watchfire check``."""

    kind: (
        str  # parse_failure | unknown_instrument | unknown_article | unresolved | version_mismatch
    )
    file: Path
    line: int
    function: str
    message: str


@dataclass(frozen=True)
class CheckReport:
    """Aggregate result of a ``watchfire check`` run."""

    results: list[CheckResult] = field(default_factory=list)
    total_citations: int = 0

    @property
    def ok(self) -> bool:
        return not any(r.kind != "unresolved" for r in self.results)

    @property
    def has_findings(self) -> bool:
        return bool(self.results)


def run_check(
    config: Config,
    *,
    index: pl.DataFrame | None = None,
    source_paths: list[Path] | None = None,
) -> CheckReport:
    """Run the check pipeline and return a :class:`CheckReport`.

    Args:
        config: Resolved project configuration.
        index: Optional pre-loaded index (saves a parquet read in
            tests). Loaded from the bundled wheel when omitted.
        source_paths: Override for the paths to walk. Defaults to
            ``config.absolute_source_paths()``.
    """

    idx = index if index is not None else load_index()
    paths = source_paths or config.absolute_source_paths()
    findings = find_citations(paths)

    results: list[CheckResult] = []
    citation_count = 0

    for finding in findings:
        if isinstance(finding, ParseFailure):
            results.append(
                CheckResult(
                    kind="parse_failure",
                    file=finding.file,
                    line=finding.line,
                    function=finding.function,
                    message=(f"unparsable citation {finding.raw!r}: {finding.error}"),
                )
            )
            continue
        if isinstance(finding, UnresolvedCitation):
            results.append(
                CheckResult(
                    kind="unresolved",
                    file=finding.file,
                    line=finding.line,
                    function=finding.function,
                    message=finding.reason,
                )
            )
            continue

        # CitationFinding from here on.
        assert isinstance(finding, CitationFinding)
        citation_count += 1
        c = finding.citation

        if c.instrument not in config.instruments:
            results.append(
                CheckResult(
                    kind="unknown_instrument",
                    file=finding.file,
                    line=finding.line,
                    function=finding.function,
                    message=(
                        f"instrument {c.instrument!r} is not in [tool.watchfire].instruments "
                        f"({list(config.instruments)})"
                    ),
                )
            )
            continue

        if not covers(idx, c):
            results.append(
                CheckResult(
                    kind="unknown_article",
                    file=finding.file,
                    line=finding.line,
                    function=finding.function,
                    message=_unknown_message(c),
                )
            )
            continue

        mismatch = _version_mismatch(c, config.rulebook_version)
        if mismatch is not None:
            results.append(
                CheckResult(
                    kind="version_mismatch",
                    file=finding.file,
                    line=finding.line,
                    function=finding.function,
                    message=mismatch,
                )
            )

    return CheckReport(results=results, total_citations=citation_count)


def _unknown_message(c) -> str:
    if c.article is not None:
        return (
            f"citation {c.canonical()!r} points to {c.instrument} Article "
            f"{c.article}, which is not in the bundled rulebook index"
        )
    if c.instrument_id is not None:
        return (
            f"citation {c.canonical()!r} references "
            f"{c.instrument}/{c.instrument_id}, which is not in the index"
        )
    return f"citation {c.canonical()!r} is not in the bundled rulebook index"


def _version_mismatch(citation, project_version: date | None) -> str | None:
    """Placeholder for v0.2 ``stale`` detection.

    For v0.1 we only check explicit per-citation version pins against
    the project-level pin. The richer comparison against
    ``index.version`` lands in v0.2.
    """

    if citation.version is None or project_version is None:
        return None
    if citation.version != project_version:
        return (
            f"citation pinned to version {citation.version.isoformat()} "
            f"but project pin is {project_version.isoformat()}"
        )
    return None
