"""Dynamic and malformed citations — used to exercise reporting paths."""

from watchfire import Citation, cites

article_number = 153


@cites("CRR Art. " + str(article_number))
def dynamic_string(x):
    """Argument is a non-literal expression — should be UnresolvedCitation."""
    return x


@cites("CRR Article zero")
def malformed_string():
    """Argument parses but cannot be interpreted — should be ParseFailure."""
    return None


@cites(Citation(instrument="CRR", article=92))
def constructed_literal():
    """Citation constructor with literal kwargs — should resolve."""
    return None


def not_decorated():
    """Plain function — not reported."""
    return None
