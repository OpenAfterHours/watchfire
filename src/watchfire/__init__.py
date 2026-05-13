"""watchfire — static analysis for UK financial regulatory citations.

Public API:
    Citation              Structured regulatory citation.
    parse_citation        Parse a canonical citation string into a Citation.
    CitationParseError    Raised when a citation string is unparsable.
    cites                 Decorator that attaches a Citation to a function.

Everything else in this package is internal and may change between
releases. In particular, `watchfire.ast_walker`, `watchfire.index`,
`watchfire.config`, `watchfire.checks`, and `watchfire.cli` are implementation
details of the `watchfire` command-line tool.
"""

from watchfire.decorator import cites
from watchfire.model import Citation
from watchfire.parser import CitationParseError, parse_citation

__version__ = "0.1.0"

__all__ = [
    "Citation",
    "CitationParseError",
    "cites",
    "parse_citation",
]
