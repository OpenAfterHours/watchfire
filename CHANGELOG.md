# Changelog

All notable changes to `watchfire` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
