"""The ``watchfire matrix`` command — citation-to-function traceability.

The reverse of ``watchfire check``: rather than asking "do all citations
resolve?", the matrix groups every discovered citation by its article
and lists the functions that cite it. The output is an audit deliverable
— compliance reviewers attach it to a PR; CI consumers commit it as a
markdown or JSON artifact.

The engine returns a :class:`MatrixReport`; all I/O lives in
:mod:`watchfire.cli`. Render helpers in this module return strings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

from watchfire.ast_walker import (
    CitationFinding,
    ParseFailure,
    UnresolvedCitation,
    find_citations,
)
from watchfire.config import Config
from watchfire.index import load_index, title_for
from watchfire.model import Citation

__all__ = [
    "MatrixCitationSite",
    "MatrixEntry",
    "MatrixReport",
    "Specificity",
    "render_json",
    "render_markdown",
    "render_text",
    "run_matrix",
]

Specificity = Literal["article", "full"]

# Instrument ordering for the default sort: mirrors the order in
# watchfire.model.Instrument (CRR before delegated regs, supervisory
# material last). Compliance reviewers read top-down by hierarchy.
_INSTRUMENT_ORDER: dict[str, int] = {
    "CRR": 0,
    "DELEGATED_REG": 1,
    "PRA_RULEBOOK": 2,
    "PS": 3,
    "SS": 4,
}

_NOT_IN_INDEX = "(not in index)"


@dataclass(frozen=True)
class MatrixCitationSite:
    """One function-level citation discovered in source."""

    file: Path
    line: int
    function: str
    citation: Citation


@dataclass(frozen=True)
class MatrixEntry:
    """All sites that cite the same rollup key.

    For ``specificity="article"`` (default) the key drops sub-article
    detail; sites preserve full specificity on their ``citation`` field.
    """

    key: Citation
    title: str | None
    sites: tuple[MatrixCitationSite, ...]


@dataclass(frozen=True)
class MatrixReport:
    """Aggregate result of a ``watchfire matrix`` run."""

    entries: tuple[MatrixEntry, ...]
    parse_failures: int
    unresolved: int
    total_functions: int
    total_citations: int


def run_matrix(
    config: Config,
    *,
    index: pl.DataFrame | None = None,
    source_paths: list[Path] | None = None,
    specificity: Specificity = "article",
    instrument_filter: str | None = None,
    article_filter: int | None = None,
) -> MatrixReport:
    """Build a :class:`MatrixReport` for the configured project.

    Args:
        config: Resolved project configuration.
        index: Optional pre-loaded index (saves a parquet read in tests).
            Loaded from the bundled wheel when omitted.
        source_paths: Override for the paths to walk. Defaults to
            ``config.absolute_source_paths()``.
        specificity: ``"article"`` (default) rolls up sub-article detail
            into a single entry per article; ``"full"`` keeps each
            distinct citation as its own entry.
        instrument_filter: If set, only entries with this instrument
            are returned.
        article_filter: If set, only entries with this article number
            are returned.
    """

    idx = index if index is not None else load_index()
    paths = source_paths or config.absolute_source_paths()
    findings = find_citations(paths)

    buckets: dict[Citation, list[MatrixCitationSite]] = {}
    distinct_functions: set[tuple[Path, str]] = set()
    parse_failures = 0
    unresolved = 0
    total_citations = 0

    for finding in findings:
        if isinstance(finding, ParseFailure):
            parse_failures += 1
            continue
        if isinstance(finding, UnresolvedCitation):
            unresolved += 1
            continue
        assert isinstance(finding, CitationFinding)
        total_citations += 1
        distinct_functions.add((finding.file, finding.function))

        site = MatrixCitationSite(
            file=finding.file,
            line=finding.line,
            function=finding.function,
            citation=finding.citation,
        )
        key = finding.citation if specificity == "full" else _rollup_key(finding.citation)
        buckets.setdefault(key, []).append(site)

    entries: list[MatrixEntry] = []
    for key in sorted(buckets, key=_sort_key):
        if instrument_filter is not None and key.instrument != instrument_filter:
            continue
        if article_filter is not None and key.article != article_filter:
            continue
        sites = tuple(sorted(buckets[key], key=lambda s: (str(s.file), s.line)))
        entries.append(
            MatrixEntry(
                key=key,
                title=title_for(idx, key),
                sites=sites,
            )
        )

    return MatrixReport(
        entries=tuple(entries),
        parse_failures=parse_failures,
        unresolved=unresolved,
        total_functions=len(distinct_functions),
        total_citations=total_citations,
    )


def _rollup_key(c: Citation) -> Citation:
    """Drop sub-article detail; keep instrument/article/section identity.

    For CRR / DELEGATED_REG this collapses ``Art. 153(1)(a)`` and
    ``Art. 153(2)`` to the same key. For PRA_RULEBOOK / PS / SS — which
    have no article concept — the full ``section`` tuple is retained
    because that *is* the identifier (SS1/23 §2.5 and §2.7 are
    different topics).
    """

    return Citation(
        instrument=c.instrument,
        instrument_id=c.instrument_id,
        article=c.article,
        section=c.section,
    )


def _sort_key(c: Citation) -> tuple:
    """Sort key: instrument bucket, then natural numeric order within."""

    return (
        _INSTRUMENT_ORDER.get(c.instrument, len(_INSTRUMENT_ORDER)),
        c.instrument_id or "",
        c.article is not None,
        c.article or 0,
        c.section is not None,
        c.section or (),
        c.paragraph is not None,
        c.paragraph or 0,
        _point_sort(c.point),
        c.subpoint is not None,
        c.subpoint or "",
        c.subparagraph is not None,
        c.subparagraph or 0,
    )


def _point_sort(p: str | None) -> tuple[int, str, int]:
    """Order points: None first, then alphabetic (a, b, ...), then numeric.

    ``point`` is ``str`` because CRR Art. 4(1) mixes alphabetic
    sub-points with numeric definition points like 75. The bucket
    ordering keeps the conventional reading order.
    """

    if p is None:
        return (0, "", 0)
    try:
        return (2, "", int(p))
    except ValueError:
        return (1, p, 0)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_text(report: MatrixReport, *, project_root: Path) -> str:
    """Render a :class:`MatrixReport` as a fixed-column text block."""

    if not report.entries:
        return _summary_line(report) + "\n" + _footer_note(report)

    lines: list[str] = []
    prev_instrument: str | None = None
    for entry in report.entries:
        if prev_instrument is not None and entry.key.instrument != prev_instrument:
            lines.append("")
        prev_instrument = entry.key.instrument

        title = entry.title or _NOT_IN_INDEX
        site_word = "site" if len(entry.sites) == 1 else "sites"
        lines.append(f"{entry.key.canonical():40s} {title:50s} {len(entry.sites)} {site_word}")
        for site in entry.sites:
            rel = _format_path(site.file, project_root)
            specifier = (
                site.citation.canonical()
                if site.citation.canonical() != entry.key.canonical()
                else ""
            )
            lines.append(f"  {rel}:{site.line}  {site.function:30s} {specifier}".rstrip())

    lines.append("")
    lines.append(_summary_line(report))
    note = _footer_note(report)
    if note:
        lines.append(note)
    return "\n".join(lines)


def render_markdown(report: MatrixReport, *, project_root: Path) -> str:
    """Render a :class:`MatrixReport` as a GitHub-flavoured markdown table."""

    lines = [
        "| Citation | Title | File | Line | Function |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in report.entries:
        title = entry.title or _NOT_IN_INDEX
        for site in entry.sites:
            rel = _format_path(site.file, project_root)
            lines.append(
                f"| {site.citation.canonical()} | {title} | {rel} | {site.line} | {site.function} |"
            )

    lines.append("")
    lines.append(_summary_line(report))
    note = _footer_note(report)
    if note:
        lines.append(note)
    return "\n".join(lines)


def render_json(report: MatrixReport, *, project_root: Path, config: Config) -> str:
    """Render a :class:`MatrixReport` as a stable JSON document."""

    document = {
        "version": 1,
        "rulebook_version": (
            config.rulebook_version.isoformat() if config.rulebook_version else None
        ),
        "total_entries": len(report.entries),
        "total_citations": report.total_citations,
        "total_functions": report.total_functions,
        "parse_failures": report.parse_failures,
        "unresolved": report.unresolved,
        "entries": [
            {
                "key": entry.key.canonical(),
                "title": entry.title,
                "sites": [
                    {
                        "file": _format_path(site.file, project_root),
                        "line": site.line,
                        "function": site.function,
                        "citation": site.citation.canonical(),
                    }
                    for site in entry.sites
                ],
            }
            for entry in report.entries
        ],
    }
    return json.dumps(document, indent=2)


def _summary_line(report: MatrixReport) -> str:
    entry_word = "entry" if len(report.entries) == 1 else "entries"
    site_word = "site" if report.total_citations == 1 else "sites"
    fn_word = "function" if report.total_functions == 1 else "functions"
    if not report.entries:
        return "watchfire matrix: no entries match"
    return (
        f"watchfire matrix: {len(report.entries)} {entry_word}, "
        f"{report.total_citations} citation {site_word} across "
        f"{report.total_functions} {fn_word}."
    )


def _footer_note(report: MatrixReport) -> str:
    if not report.parse_failures and not report.unresolved:
        return ""
    bits = []
    if report.parse_failures:
        bits.append(f"{report.parse_failures} parse-failure(s)")
    if report.unresolved:
        bits.append(f"{report.unresolved} unresolved citation(s)")
    return f"(plus {' and '.join(bits)} — run 'watchfire check' for details)"


def _format_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()
