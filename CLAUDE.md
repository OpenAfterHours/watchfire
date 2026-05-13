# CLAUDE.md

Notes for Claude Code working on `regcite`. The README is for end users;
this file is for contributors (human and otherwise) and captures what
isn't obvious from reading the code.

## What this is

`regcite` is a static-analysis tool for UK financial regulatory
citations in Python code. Developers annotate functions with
`@cites("CRR Art. 153(1)(a)")`; `regcite check` walks the source tree
and verifies the citation against a bundled, versioned snapshot of the
rulebook. The first real consumer is `OpenAfterHours/rwa_calculator`.

Sibling repo `rwa_calculator` is the style and tooling reference — when
in doubt, mirror its conventions.

## Scope guardrails (v0.1)

In scope: citation grammar + parser, `@cites` decorator, AST walker,
bundled CRR index, `regcite check` CLI, `[tool.regcite]` config.

**Out of scope — do not implement until asked:**

- `regcite matrix` (traceability matrix) — v0.2
- `regcite stale` (rulebook diff vs index) — v0.2. The `version_mismatch`
  branch in `checks/check.py` is a placeholder for this; do not extend
  it without a v0.2 design.
- Automated scraping of legislation.gov.uk / PRA Rulebook — v0.3+
- Test-to-citation mapping, coverage heuristics — later

The grammar and decorator surface are the things to get right first.
Resist building infra around features that aren't shipping yet.

## Repo layout

```
src/regcite/
  __init__.py        public API: Citation, parse_citation, CitationParseError, cites
  model.py           Citation dataclass (frozen)
  parser.py          string -> Citation; raises CitationParseError
  decorator.py       @cites — attaches __regcite__, no runtime wrapping
  ast_walker.py      find_citations(paths) -> list[CitationFinding | ParseFailure | UnresolvedCitation]
  index.py           load_index() -> pl.DataFrame; covers(index, citation)
  config.py          [tool.regcite] reader, returns Config
  checks/check.py    run_check(config) — the engine behind `regcite check`
  cli.py             typer app; thin wrapper over run_check
  data/index.parquet bundled rulebook snapshot
scripts/build_index.py   one-off rebuild of data/index.parquet
tests/                   one test_*.py per module + fixtures/sample_project
```

The public API is exactly the four names re-exported from
`regcite/__init__.py`. Everything else (`ast_walker`, `index`, `config`,
`checks`, `cli`) is internal and may change.

## Key invariants — don't break these

- **`@cites` is a no-op at runtime.** It stores the parsed `Citation`
  on `func.__regcite__` and returns the function unchanged. No wrapping,
  no `functools.wraps`, no introspection hooks. If you find yourself
  about to wrap, stop.
- **The parser raises on malformed input.** A citation that doesn't
  parse is a code-review event, never a silent skip. `CitationParseError`
  messages must quote the offending input.
- **The AST walker does not import user code.** It uses `ast.parse`
  only. This means `@cites(some_variable)` is reported as
  `UnresolvedCitation`, not resolved. Don't add an "evaluate the
  expression" path — the determinism of static analysis is the point.
- **`Citation.raw` is excluded from equality and hashing.** Two
  citations that parsed from differently-spelled-but-equivalent strings
  must compare equal.
- **`unresolved` findings do not fail the check.** They print but exit 0.
  Only `parse_failure`, `unknown_instrument`, `unknown_article`, and
  `version_mismatch` are failing kinds. Don't conflate.
- **The bundled index is hand-curated for v0.1.** Don't add a runtime
  fetch path; if the index needs updating, rerun `scripts/build_index.py`
  and commit the parquet.

## Citation grammar — the shape

Every form the parser must accept is listed in the README's grammar
table and exercised in `tests/test_parser.py`. If you're touching the
parser, the tests are the authoritative spec — extend them first.

Instrument literal (`model.Instrument`): `CRR`, `PRA_RULEBOOK`, `PS`,
`SS`, `DELEGATED_REG`. Adding an instrument means: update the literal,
the parser dispatch, `Citation.canonical()`, the README grammar table,
the config `DEFAULT_INSTRUMENTS`, and the index schema docstring.

`point` is a `str | None`, not an `int`. CRR Art. 4(1)(75) uses numeric
points (`"75"`) for definitions; alphabetic and numeric points share
the same field.

## Dev workflow

`uv` for everything. Python 3.11+.

```bash
uv sync --extra dev              # install dev deps
uv run pytest tests/             # run tests
uv run pytest tests/test_parser.py -v   # one file
uv run ruff check src/ tests/    # lint
uv run ruff format src/ tests/   # format
uv run ruff format --check src/ tests/  # CI-style format check
uv run ty check src/regcite/     # typecheck
uv run regcite check             # run the CLI against the current project
```

CI runs lint, ruff format check, `ty check`, and pytest across Python
3.11 / 3.12 / 3.13 (`.github/workflows/ci.yml`). All four gate merge.

## Type checker quirks (`ty`)

`ty` is the type checker, not mypy. A few existing call sites use
`# ty: ignore[invalid-argument-type]` where a `Literal` field is
populated from a runtime-validated string (e.g. `instrument=kind` in the
parser). Mirror that pattern rather than restructuring around it — the
runtime validation already enforces the literal.

`tests/fixtures/` is excluded from `ty` (see `[tool.ty.src]` in
`pyproject.toml`) because the fixtures intentionally contain malformed
code. Don't move test fixtures elsewhere expecting them to type-check.

## Testing approach

- `tests/test_parser.py` is the most important test file. Cover every
  shape in the grammar table, plus deliberately malformed inputs that
  must raise `CitationParseError`. Whitespace variants and
  `Art`/`Art.`/`Article`/`article` casings are part of the contract.
- AST walker and check tests run against `tests/fixtures/sample_project/`
  — a tiny synthetic project with decorated functions. Add new
  walker/check scenarios as additional files in the fixture rather than
  inlining `ast.parse` strings.
- `regcite check` integration tests should assert exit codes and stderr
  content, since the CLI's contract is what CI consumers depend on.

## Rebuilding the bundled index

`scripts/build_index.py` is a one-off generator that writes
`src/regcite/data/index.parquet`. Source text comes from
`legislation.gov.uk` (CRR is at `/eur/2013/575`). Re-run only when the
snapshot date changes; commit the resulting parquet. There is no
automated scrape — that is a v0.3 problem.

Index schema is documented at the top of `src/regcite/index.py`. Adding
columns means updating the loader, the schema docstring, and any
`covers()` logic that should now consider the new field.

## Style

- No emoji anywhere — code, commits, docs, output.
- Conventional Commits style.
- Public functions get docstrings; private helpers usually don't.
- Prefer functions over classes when a function will do.
- `from __future__ import annotations` at the top of every module.
- Linter is `ruff` with the rule set in `pyproject.toml`; don't disable
  rules to silence findings — fix the code.
- Print statements are allowed only in CLI / `checks/` / `scripts/`
  (see `tool.ruff.lint.per-file-ignores`). Library code should not print.

## "Done" for v0.1

A downstream user can `uv add regcite`, add `[tool.regcite]` to their
`pyproject.toml`, decorate a function with `@cites("CRR Art. 153(1)(a)")`,
run `regcite check`, and get either a clean exit or a clear, actionable
error. That's the bar. Everything else is v0.2+.
