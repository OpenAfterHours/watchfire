"""regcite — static analysis for UK financial regulatory citations.

Public API:
    Citation              Structured regulatory citation.
    parse_citation        Parse a canonical citation string into a Citation.
    CitationParseError    Raised when a citation string is unparsable.
    cites                 Decorator that attaches a Citation to a function.

Everything else in this package is internal and may change between
releases. In particular, `regcite.ast_walker`, `regcite.index`,
`regcite.config`, `regcite.checks`, and `regcite.cli` are implementation
details of the `regcite` command-line tool.
"""

from regcite.decorator import cites
from regcite.model import Citation
from regcite.parser import CitationParseError, parse_citation

__version__ = "0.1.0"

__all__ = [
    "Citation",
    "CitationParseError",
    "cites",
    "parse_citation",
]
