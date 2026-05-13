# watchfire

> [!IMPORTANT]
> *This package is still in development and is not production ready.*

Static analysis for UK financial regulatory citations in Python code.

`watchfire` lets you annotate Python functions with citations to UK
financial regulation — CRR, the PRA Rulebook, PRA Policy Statements,
PRA Supervisory Statements — and then check those citations against a
bundled, versioned snapshot of the rulebook. The intent is to make the
mapping from compliance code to the regulation it implements *executable*:
runs in CI, lives next to the code, and breaks the build when it drifts.

## Why this exists

Regulatory engineering teams in UK banks need an auditable trail from
every formula in their RWA / capital code back to a specific article of
the CRR or rule in the PRA Rulebook. Today that trail is produced by
hand in Word documents that drift the moment anyone changes the code.
`watchfire` puts the mapping where the code is, checks it on every commit,
and gives reviewers, auditors, and the PRA something verifiable to look
at instead of a stale spreadsheet.

The first real user is
[`OpenAfterHours/rwa_calculator`](https://github.com/OpenAfterHours/rwa_calculator)
— a UK CRR / Basel 3.1 credit-risk RWA library whose formulas need to
trace back to specific articles. If you're building something similar,
`watchfire` is for you.

## Install

```bash
uv add watchfire
# or
pip install watchfire
```

Python 3.11+.

## Quickstart

Decorate a function with the regulation it implements:

```python
from watchfire import cites


@cites("CRR Art. 153(1)(a)")
def corporate_rw(pd: float, lgd: float, maturity: float) -> float:
    """Risk-weight under the IRB approach for corporates."""
    ...
```

Add a `[tool.watchfire]` table to your `pyproject.toml`:

```toml
[tool.watchfire]
rulebook_version = "2024-07-09"
instruments = ["CRR", "PRA_RULEBOOK", "PS", "SS"]
source_paths = ["src"]
```

Run the checker:

```bash
$ uv run watchfire check
watchfire: checked 47 citation(s); no issues found.
```

If a citation fails to parse or points at something the bundled index
doesn't know about, `watchfire check` exits non-zero and prints a line
per finding with file, line number, and reason — suitable for CI:

```
src/myproj/sa.py:31: sovereign_rw: unknown_article: citation 'CRR Art. 999' points to CRR Article 999, which is not in the bundled rulebook index
watchfire: 1 failing finding(s), 0 unresolved, out of 12 resolved citation(s).
```

`@cites` is a no-op at runtime — it attaches the parsed citation to the
function as `__watchfire__` and returns the function unchanged. No
wrapping, no overhead, nothing to debug.

## Citation grammar

The parser accepts canonical UK regulatory citation strings. The shape
that comes out the other side is a frozen `Citation` dataclass; see
`watchfire.Citation` for the field list.

| Input                              | Meaning                                                  |
| ---------------------------------- | -------------------------------------------------------- |
| `CRR Art. 153`                     | Whole article                                            |
| `CRR Article 153`                  | (alternate spelling)                                     |
| `CRR Art. 153(1)`                  | Paragraph                                                |
| `CRR Art. 153(1)(a)`               | Point                                                    |
| `CRR Art. 153(1)(a)(ii)`           | Sub-point                                                |
| `CRR Art. 4(1)(75)`                | Numeric point (CRR definitions)                          |
| `PRA Rulebook, Credit Risk, 3.2`   | Rulebook section                                         |
| `PS9/24`                           | PRA Policy Statement, whole document                     |
| `SS1/23, paragraph 2.5`            | Supervisory Statement with paragraph reference           |
| `Delegated Regulation 2018/171 Art. 3` | UK on-shored EU Delegated Regulation                 |

The keyword for an article accepts `Art`, `Art.`, `Article`, or `article`
in any case. Whitespace is normalised. Anything that doesn't parse is a
`CitationParseError`, which `watchfire check` reports with the offending
input — these are code-review events, not silent skips.

## Configuration reference

```toml
[tool.watchfire]
# Snapshot of the rulebook to pin to. Decorators that omit `version=`
# inherit this pin. ISO-8601 date.
rulebook_version = "2024-07-09"

# Citation instruments allowed in this project. A citation whose
# instrument is not in this list is reported by `watchfire check`.
instruments = ["CRR", "PRA_RULEBOOK", "PS", "SS", "DELEGATED_REG"]

# Directories to walk when running `watchfire check` with no arguments.
source_paths = ["src"]
```

## Public API

```python
from watchfire import (
    Citation,            # frozen dataclass: instrument, article, paragraph, ...
    parse_citation,      # str -> Citation, raises CitationParseError
    CitationParseError,
    cites,               # the @cites decorator
)
```

Everything else (`watchfire.ast_walker`, `watchfire.index`, `watchfire.checks`,
`watchfire.cli`) is internal and may change between releases.

## Roadmap

`watchfire` v0.1 is intentionally a narrow vertical slice: get the
citation grammar right against real usage in `rwa_calculator`, ship the
decorator and CLI, then expand.

| Version | Adds                                                                          |
| ------- | ----------------------------------------------------------------------------- |
| v0.1    | Citation grammar, `@cites`, `watchfire check`, bundled CRR index               |
| v0.2    | `watchfire matrix` (traceability matrix), `watchfire stale` (rulebook diff)       |
| v0.3+   | Automated scraping of legislation.gov.uk + the PRA Rulebook                    |

If you have feedback on the citation grammar specifically, please open
an issue — the grammar is the foundation, and getting it wrong now is
much cheaper to fix than getting it wrong later.

## Licence

Apache 2.0. See `LICENSE`.
