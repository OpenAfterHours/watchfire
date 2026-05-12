"""Tests for the ``@cites`` decorator."""

from __future__ import annotations

import pytest

from regcite import Citation, CitationParseError, cites, parse_citation


class TestDecoratorBasics:
    def test_attaches_citation_from_string(self):
        @cites("CRR Art. 153(1)(a)")
        def f():
            return 1

        assert isinstance(f.__regcite__, Citation)
        assert f.__regcite__ == parse_citation("CRR Art. 153(1)(a)")

    def test_attaches_pre_built_citation(self):
        c = Citation(instrument="CRR", article=153)

        @cites(c)
        def f():
            return 1

        assert f.__regcite__ is c

    def test_function_returns_unchanged(self):
        @cites("CRR Art. 153")
        def f(x, y):
            return x + y

        # No wrapping: the decorator returns the original function.
        assert f(1, 2) == 3

    def test_function_metadata_preserved(self):
        @cites("CRR Art. 153")
        def f():
            """My docstring."""

        assert f.__name__ == "f"
        assert f.__doc__ == "My docstring."

    def test_decorator_is_identity(self):
        def f():
            return 1

        decorated = cites("CRR Art. 153")(f)
        # Same object — no wrapping.
        assert decorated is f


class TestDecoratorErrors:
    def test_malformed_string_raises_at_decoration_time(self):
        with pytest.raises(CitationParseError):

            @cites("not a citation")
            def f():
                pass

    def test_wrong_type_raises_typeerror(self):
        with pytest.raises(TypeError, match="string or Citation"):

            @cites(123)  # ty: ignore[invalid-argument-type]
            def f():
                pass

    def test_none_raises(self):
        with pytest.raises(TypeError):

            @cites(None)  # ty: ignore[invalid-argument-type]
            def f():
                pass


class TestMultipleDecorations:
    def test_multiple_citations_last_wins(self):
        # Stacking @cites is supported but only the outermost survives
        # on __regcite__ — see ast_walker for what scanning reports.
        @cites("CRR Art. 153")
        @cites("CRR Art. 154")
        def f():
            pass

        # Outermost decorator applied last, so it overwrites.
        assert f.__regcite__.article == 153
