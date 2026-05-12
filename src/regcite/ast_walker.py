"""Find ``@cites`` decorators in a Python source tree by static analysis.

This module deliberately does not import user code: it uses :mod:`ast`
to parse each file. Importing would run module-level code, pull in
dependencies that might not be installed in the analysis environment,
and break determinism. The cost is that we only see citations whose
argument is a *literal* — a string or a ``Citation(...)`` constructor
call with constant arguments. Anything dynamic (variables, function
calls returning a Citation) is reported as an :class:`UnresolvedCitation`
finding.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from regcite.model import Citation
from regcite.parser import CitationParseError, parse_citation

__all__ = [
    "CitationFinding",
    "ParseFailure",
    "UnresolvedCitation",
    "find_citations",
]


@dataclass(frozen=True)
class CitationFinding:
    """A successfully parsed citation discovered in source."""

    file: Path
    line: int
    function: str
    citation: Citation


@dataclass(frozen=True)
class ParseFailure:
    """A ``@cites(...)`` decorator whose argument failed to parse."""

    file: Path
    line: int
    function: str
    raw: str
    error: str


@dataclass(frozen=True)
class UnresolvedCitation:
    """A ``@cites(...)`` decorator whose argument is non-literal.

    Reported separately from parse failures because the citation might
    well be correct; we just can't see it without running the code.
    """

    file: Path
    line: int
    function: str
    reason: str


Finding = CitationFinding | ParseFailure | UnresolvedCitation


def find_citations(
    paths: Iterable[Path | str],
    *,
    follow_symlinks: bool = False,
) -> list[Finding]:
    """Walk ``paths`` and return every ``@cites`` decorator found.

    Args:
        paths: Files or directories to scan. Directories are walked
            recursively for ``*.py`` files.
        follow_symlinks: If ``False`` (default), symlinked directories
            are skipped to avoid infinite walks.

    Returns:
        A list of findings in encounter order (depth-first by path,
        line order within each file).
    """

    findings: list[Finding] = []
    for path in _collect_python_files(paths, follow_symlinks=follow_symlinks):
        findings.extend(_scan_file(path))
    return findings


def _collect_python_files(paths: Iterable[Path | str], *, follow_symlinks: bool) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_file():
            if p.suffix == ".py":
                yield p
            continue
        # Sorted walk for deterministic finding order.
        for sub in sorted(p.rglob("*.py")):
            if not follow_symlinks and sub.is_symlink():
                continue
            yield sub


def _scan_file(path: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for deco in node.decorator_list:
            finding = _interpret_decorator(deco, node, path)
            if finding is not None:
                findings.append(finding)
    return findings


def _interpret_decorator(
    deco: ast.expr, func: ast.FunctionDef | ast.AsyncFunctionDef, path: Path
) -> Finding | None:
    """Decide whether ``deco`` is a ``@cites(...)`` call and parse it."""

    if not isinstance(deco, ast.Call):
        return None
    if not _is_cites_name(deco.func):
        return None

    if len(deco.args) != 1 or deco.keywords:
        return UnresolvedCitation(
            file=path,
            line=deco.lineno,
            function=func.name,
            reason="@cites expects exactly one positional argument",
        )

    arg = deco.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        try:
            citation = parse_citation(arg.value)
        except CitationParseError as exc:
            return ParseFailure(
                file=path,
                line=deco.lineno,
                function=func.name,
                raw=arg.value,
                error=str(exc),
            )
        return CitationFinding(file=path, line=deco.lineno, function=func.name, citation=citation)

    if isinstance(arg, ast.Call) and _is_citation_constructor(arg.func):
        try:
            citation = _citation_from_ast_call(arg)
        except _UnresolvedError as exc:
            return UnresolvedCitation(
                file=path, line=deco.lineno, function=func.name, reason=str(exc)
            )
        return CitationFinding(file=path, line=deco.lineno, function=func.name, citation=citation)

    return UnresolvedCitation(
        file=path,
        line=deco.lineno,
        function=func.name,
        reason=(
            "@cites argument is not a literal string or Citation(...) "
            "constructor call; regcite cannot resolve it statically"
        ),
    )


def _is_cites_name(node: ast.expr) -> bool:
    # Match ``@cites(...)`` or ``@regcite.cites(...)``.
    if isinstance(node, ast.Name):
        return node.id == "cites"
    if isinstance(node, ast.Attribute):
        return node.attr == "cites"
    return False


def _is_citation_constructor(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Citation"
    if isinstance(node, ast.Attribute):
        return node.attr == "Citation"
    return False


class _UnresolvedError(Exception):
    """Internal: AST node is too dynamic to interpret statically."""


def _citation_from_ast_call(call: ast.Call) -> Citation:
    if call.args:
        raise _UnresolvedError("Citation(...) must be called with keyword arguments only")
    kwargs: dict[str, object] = {}
    for kw in call.keywords:
        if kw.arg is None:
            raise _UnresolvedError("Citation(...) with **kwargs is unresolved")
        kwargs[kw.arg] = _literal_value(kw.value)
    return Citation(**kwargs)  # ty: ignore[invalid-argument-type]


def _literal_value(node: ast.expr) -> object:
    """Return the Python value of ``node`` if it is a constant literal."""

    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_literal_value(e) for e in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _literal_value(node.operand)
        if isinstance(inner, int | float):
            return -inner
    raise _UnresolvedError(f"non-literal argument to Citation(...) at line {node.lineno}")
