"""Command-line entry point for ``watchfire``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from watchfire import __version__
from watchfire.checks import run_check
from watchfire.config import ConfigError, load_config
from watchfire.matrix import (
    render_json,
    render_markdown,
    render_text,
    run_matrix,
)

app = typer.Typer(
    name="watchfire",
    help="Static analysis for UK financial regulatory citations.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"watchfire {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
        ),
    ] = False,
) -> None:
    """Static analysis for UK financial regulatory citations."""


@app.command("check")
def check(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Source paths to scan. Overrides [tool.watchfire].source_paths."),
    ] = None,
    project: Annotated[
        Path | None,
        typer.Option(
            "--project",
            help="Directory containing pyproject.toml. Defaults to the current working directory.",
        ),
    ] = None,
) -> None:
    """Check all ``@cites`` decorators in a project against the rulebook index."""

    try:
        config = load_config(project)
    except ConfigError as exc:
        typer.echo(f"watchfire: {exc}", err=True)
        raise typer.Exit(code=2) from None

    scan_paths = paths if paths else config.absolute_source_paths()
    report = run_check(config, source_paths=scan_paths)

    if not report.has_findings:
        typer.echo(f"watchfire: checked {report.total_citations} citation(s); no issues found.")
        raise typer.Exit(code=0)

    # Group findings by severity. Unresolved is reported but does not
    # fail the check (the citation might be fine, we just couldn't see
    # it without running user code).
    failing = [r for r in report.results if r.kind != "unresolved"]
    unresolved = [r for r in report.results if r.kind == "unresolved"]

    for r in failing:
        typer.echo(f"{r.file}:{r.line}: {r.function}: {r.kind}: {r.message}", err=True)
    for r in unresolved:
        typer.echo(f"{r.file}:{r.line}: {r.function}: unresolved: {r.message}")

    if failing:
        typer.echo(
            f"watchfire: {len(failing)} failing finding(s), {len(unresolved)} unresolved, "
            f"out of {report.total_citations} resolved citation(s).",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(
        f"watchfire: {len(unresolved)} unresolved citation(s); "
        f"{report.total_citations} resolved cleanly."
    )
    raise typer.Exit(code=0)


@app.command("matrix")
def matrix(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Source paths to scan. Overrides [tool.watchfire].source_paths."),
    ] = None,
    project: Annotated[
        Path | None,
        typer.Option(
            "--project",
            help="Directory containing pyproject.toml. Defaults to the current working directory.",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: text (default), markdown, or json.",
        ),
    ] = "text",
    specificity: Annotated[
        str,
        typer.Option(
            "--specificity",
            help="article (default) rolls up sub-article detail; full keeps every distinct citation.",
        ),
    ] = "article",
    instrument: Annotated[
        str | None,
        typer.Option(
            "--instrument",
            help="Filter to entries with this instrument (e.g. CRR).",
        ),
    ] = None,
    article: Annotated[
        str | None,
        typer.Option(
            "--article",
            help="Filter to entries with this article number (e.g. 153 or 92a).",
        ),
    ] = None,
) -> None:
    """Build a traceability matrix mapping citations back to functions."""

    if output_format not in {"text", "markdown", "json"}:
        typer.echo(
            f"watchfire: --format must be text, markdown, or json (got {output_format!r})",
            err=True,
        )
        raise typer.Exit(code=2)
    if specificity not in {"article", "full"}:
        typer.echo(
            f"watchfire: --specificity must be article or full (got {specificity!r})",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        config = load_config(project)
    except ConfigError as exc:
        typer.echo(f"watchfire: {exc}", err=True)
        raise typer.Exit(code=2) from None

    scan_paths = paths if paths else config.absolute_source_paths()
    report = run_matrix(
        config,
        source_paths=scan_paths,
        specificity=specificity,  # ty: ignore[invalid-argument-type]
        instrument_filter=instrument,
        article_filter=article,
    )

    if output_format == "markdown":
        typer.echo(render_markdown(report, project_root=config.project_root))
    elif output_format == "json":
        typer.echo(render_json(report, project_root=config.project_root, config=config))
    else:
        typer.echo(render_text(report, project_root=config.project_root))
    raise typer.Exit(code=0)


def main() -> None:
    """Console-script entry point."""

    try:
        app()
    except typer.Exit as exit_:
        sys.exit(exit_.exit_code)


if __name__ == "__main__":
    main()
