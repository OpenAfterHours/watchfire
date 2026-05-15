"""Tests for the ``@cites`` decorator."""

from __future__ import annotations

import pytest

from watchfire import Citation, CitationParseError, cites, parse_citation


class TestDecoratorBasics:
    def test_attaches_citation_from_string(self):
        @cites("CRR Art. 153(1)(a)")
        def f():
            return 1

        assert f.__watchfire__ == (parse_citation("CRR Art. 153(1)(a)"),)

    def test_attaches_pre_built_citation(self):
        c = Citation(instrument="CRR", article="153")

        @cites(c)
        def f():
            return 1

        assert f.__watchfire__ == (c,)
        assert f.__watchfire__[0] is c

    def test_single_decorator_yields_one_element_tuple(self):
        @cites("CRR Art. 92")
        def f():
            return 1

        assert isinstance(f.__watchfire__, tuple)
        assert len(f.__watchfire__) == 1

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
    def test_stacked_decorators_preserve_both_in_source_order(self):
        # The outermost decorator is the primary citation and appears
        # first in __watchfire__; inner decorators follow in source order.
        @cites("CRR Art. 153")
        @cites("CRR Art. 154")
        def f():
            pass

        assert len(f.__watchfire__) == 2
        assert f.__watchfire__[0].article == "153"
        assert f.__watchfire__[1].article == "154"

    def test_three_stacked_decorators_preserve_order(self):
        @cites("CRR Art. 92")
        @cites("CRR Art. 153")
        @cites("CRR Art. 154")
        def f():
            pass

        assert tuple(c.article for c in f.__watchfire__) == ("92", "153", "154")

    def test_stacking_does_not_mutate_shared_citation(self):
        # Decorating two different functions with the same @cites
        # instance must not entangle their tuples.
        deco = cites("CRR Art. 92")

        @deco
        def f():
            pass

        @deco
        def g():
            pass

        assert f.__watchfire__ == (parse_citation("CRR Art. 92"),)
        assert g.__watchfire__ == (parse_citation("CRR Art. 92"),)
