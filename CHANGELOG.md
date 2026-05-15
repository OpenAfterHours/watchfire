# Changelog

All notable changes to `watchfire` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `watchfire matrix` CLI command: builds a traceability matrix mapping
  citations back to the functions that cite them. Supports `--format
  {text,markdown,json}`, `--specificity {article,full}`, and
  `--instrument` / `--article` filters. Exits 0 unconditionally — the
  matrix is an audit artifact, not a gate.
- `watchfire.index.title_for(index, citation)`: looks up the
  human-readable article title in the bundled index. Reused by
  `watchfire matrix` to label each entry.
- Stacked `@cites` decorators are supported, for rules that live in
  more than one instrument (e.g. a CRR article and the corresponding
  PRA Policy Statement). The outermost decorator is the primary
  citation; `watchfire check` reports one finding per decorator.

### Changed

- **Breaking:** `func.__watchfire__` is now always a
  `tuple[Citation, ...]` (length 1+, outermost decorator first), where
  it was previously a bare `Citation`. Code that read the attribute
  directly must iterate or index it; the AST walker and `watchfire
  check` are unaffected.

## [0.1.0] — 2026-05-12

Initial release. Establishes the citation grammar, the `@cites` decorator,
and the `watchfire check` CLI against a bundled, hand-curated index of UK
on-shored CRR articles.

### Added

- `Citation` dataclass covering CRR, PRA Rulebook, PRA Policy Statements,
  PRA Supervisory Statements, and EU Delegated Regulations.
- `parse_citation` / `CitationParseError` for turning canonical citation
  strings into structured citations.
- `@cites(...)` decorator that attaches a parsed citation to a function
  as `__watchfire__`.
- AST walker that scans a source tree for `@cites(...)` decorators
  without importing user code.
- Bundled rulebook index (`src/watchfire/data/index.parquet`) covering CRR
  Articles 4, 92, 107, 111, 113, 114, 142, 143, 153, 154, and 166.
- `watchfire check` CLI command that reports unparsable citations and
  citations pointing at instruments or articles missing from the index.
- `[tool.watchfire]` configuration in `pyproject.toml`.
