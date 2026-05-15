"""The ``@cites`` decorator.

A no-op at runtime: attaches the parsed :class:`Citation` to the wrapped
function as a ``tuple[Citation, ...]`` on ``__watchfire__`` and returns
the original function unchanged. Static analysis (the AST walker,
``watchfire check``) is what actually does something with the citation.

Multiple ``@cites`` decorators stack: the same rule often lives in two
instruments (e.g. a CRR article and the corresponding PRA Policy
Statement), and authors can record both. The outermost decorator is the
primary citation and appears first in ``__watchfire__``; subsequent
decorators (inner) follow in source order.

The string form is parsed eagerly so a malformed citation fails at
import time, not at audit time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, overload

from watchfire.model import Citation
from watchfire.parser import parse_citation

__all__ = ["cites"]

F = TypeVar("F", bound=Callable[..., object])


@overload
def cites(citation: str) -> Callable[[F], F]: ...
@overload
def cites(citation: Citation) -> Callable[[F], F]: ...


def cites(citation: str | Citation) -> Callable[[F], F]:
    """Attach a regulatory citation to the decorated function.

    The citation is stored on the function as ``__watchfire__``, which
    is always a ``tuple[Citation, ...]`` of length one or more. The
    function is otherwise returned unchanged: there is no runtime
    overhead and no wrapping.

    Stacking ``@cites`` decorators is supported and is the canonical way
    to record that a function implements a rule that lives in more than
    one instrument. The outermost decorator is the primary citation and
    appears at ``__watchfire__[0]``; inner decorators follow in source
    order.

    Args:
        citation: Either a canonical citation string (parsed eagerly)
            or a pre-built :class:`Citation`.

    Raises:
        CitationParseError: If ``citation`` is a string that cannot be
            parsed. Raised at decoration time, not at call time.
        TypeError: If ``citation`` is neither a string nor a
            :class:`Citation`.
    """

    if isinstance(citation, str):
        parsed: Citation = parse_citation(citation)
    elif isinstance(citation, Citation):
        parsed = citation
    else:
        raise TypeError(f"@cites requires a string or Citation, got {type(citation).__name__}")

    def decorate(func: F) -> F:
        existing: tuple[Citation, ...] = getattr(func, "__watchfire__", ())
        func.__watchfire__ = (parsed, *existing)
        return func

    return decorate
