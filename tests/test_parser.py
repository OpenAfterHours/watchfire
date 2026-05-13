"""Tests for the citation parser.

The parser is the foundation of the project; the rest of watchfire assumes
its output is structurally correct and its error messages are
actionable. These tests cover every documented grammar shape, every
abbreviation variant, common whitespace mistakes, and a representative
set of malformed inputs.
"""

from __future__ import annotations

import pytest

from watchfire import Citation, CitationParseError, parse_citation

# ---------------------------------------------------------------------------
# CRR — happy path
# ---------------------------------------------------------------------------


class TestCRRArticle:
    def test_whole_article(self):
        c = parse_citation("CRR Art. 153")
        assert c.instrument == "CRR"
        assert c.article == 153
        assert c.paragraph is None
        assert c.point is None
        assert c.subpoint is None
        assert c.instrument_id is None

    def test_alternate_keyword_article(self):
        assert parse_citation("CRR Article 153").article == 153

    def test_alternate_keyword_art_no_period(self):
        assert parse_citation("CRR Art 153").article == 153

    def test_lowercase_keyword(self):
        assert parse_citation("CRR art. 153").article == 153

    def test_mixed_case_keyword(self):
        assert parse_citation("CRR ARTICLE 153").article == 153

    def test_paragraph(self):
        c = parse_citation("CRR Art. 153(1)")
        assert c.article == 153
        assert c.paragraph == 1
        assert c.point is None
        assert c.subpoint is None

    def test_point(self):
        c = parse_citation("CRR Art. 153(1)(a)")
        assert c.article == 153
        assert c.paragraph == 1
        assert c.point == "a"
        assert c.subpoint is None

    def test_subpoint(self):
        c = parse_citation("CRR Art. 153(1)(a)(ii)")
        assert c.article == 153
        assert c.paragraph == 1
        assert c.point == "a"
        assert c.subpoint == "ii"

    def test_numeric_point_definitions(self):
        # CRR Art. 4(1)(75) — definitions are numbered, so the point is
        # carried as a string even though the value is "75".
        c = parse_citation("CRR Art. 4(1)(75)")
        assert c.article == 4
        assert c.paragraph == 1
        assert c.point == "75"

    def test_no_space_between_keyword_and_number(self):
        assert parse_citation("CRR Art.153").article == 153

    def test_no_space_between_number_and_parens(self):
        c = parse_citation("CRR Art. 153(1)(a)")
        assert c.paragraph == 1 and c.point == "a"

    def test_space_between_parens(self):
        c = parse_citation("CRR Art. 153(1) (a) (ii)")
        assert c.paragraph == 1 and c.point == "a" and c.subpoint == "ii"

    def test_leading_and_trailing_whitespace(self):
        assert parse_citation("  CRR Art. 153  ").article == 153

    def test_uppercase_subpoint_roman_numeral(self):
        # Some sources cite "(II)" in upper case; preserve as written.
        c = parse_citation("CRR Art. 153(1)(a)(II)")
        assert c.subpoint == "II"


# ---------------------------------------------------------------------------
# CRR — error cases
# ---------------------------------------------------------------------------


class TestCRRErrors:
    def test_just_crr(self):
        with pytest.raises(CitationParseError, match="expected 'Art."):
            parse_citation("CRR")

    def test_crr_no_number(self):
        with pytest.raises(CitationParseError, match="article number"):
            parse_citation("CRR Art.")

    def test_crr_article_zero(self):
        with pytest.raises(CitationParseError, match="positive"):
            parse_citation("CRR Art. 0")

    def test_unmatched_open_paren(self):
        with pytest.raises(CitationParseError):
            parse_citation("CRR Art. 153(1")

    def test_unmatched_close_paren(self):
        with pytest.raises(CitationParseError):
            parse_citation("CRR Art. 153)1(")

    def test_trailing_garbage(self):
        with pytest.raises(CitationParseError):
            parse_citation("CRR Art. 153 foo")

    def test_paragraph_not_int(self):
        with pytest.raises(CitationParseError, match="paragraph must be an integer"):
            parse_citation("CRR Art. 153(a)")

    def test_too_many_parens(self):
        with pytest.raises(CitationParseError, match="too many"):
            parse_citation("CRR Art. 153(1)(a)(ii)(iii)")

    def test_empty_parens(self):
        with pytest.raises(CitationParseError):
            parse_citation("CRR Art. 153()")


# ---------------------------------------------------------------------------
# PRA Rulebook
# ---------------------------------------------------------------------------


class TestPRARulebook:
    def test_part_and_section(self):
        c = parse_citation("PRA Rulebook, Credit Risk, 3.2")
        assert c.instrument == "PRA_RULEBOOK"
        assert c.instrument_id == "Credit Risk"
        assert c.section == (3, 2)
        assert c.article is None

    def test_deeper_section(self):
        c = parse_citation("PRA Rulebook, Credit Risk, 3.2.1")
        assert c.section == (3, 2, 1)

    def test_part_only(self):
        c = parse_citation("PRA Rulebook, Credit Risk")
        assert c.instrument_id == "Credit Risk"
        assert c.section is None

    def test_single_level_section(self):
        c = parse_citation("PRA Rulebook, Credit Risk, 3")
        assert c.section == (3,)

    def test_case_insensitive_keyword(self):
        c = parse_citation("pra rulebook, Credit Risk, 3.2")
        assert c.instrument == "PRA_RULEBOOK"
        assert c.section == (3, 2)

    def test_extra_whitespace(self):
        c = parse_citation("PRA Rulebook,   Credit Risk ,  3.2")
        assert c.instrument_id == "Credit Risk"
        assert c.section == (3, 2)

    def test_missing_part_errors(self):
        with pytest.raises(CitationParseError, match="must name a part"):
            parse_citation("PRA Rulebook, 3.2")

    def test_no_body_errors(self):
        with pytest.raises(CitationParseError, match="must name a part"):
            parse_citation("PRA Rulebook")


# ---------------------------------------------------------------------------
# PRA Policy / Supervisory Statements
# ---------------------------------------------------------------------------


class TestPRAPublications:
    def test_ps_whole_document(self):
        c = parse_citation("PS9/24")
        assert c.instrument == "PS"
        assert c.instrument_id == "PS9/24"
        assert c.section is None

    def test_ss_whole_document(self):
        c = parse_citation("SS1/23")
        assert c.instrument == "SS"
        assert c.instrument_id == "SS1/23"

    def test_ss_with_paragraph(self):
        c = parse_citation("SS1/23, paragraph 2.5")
        assert c.instrument == "SS"
        assert c.instrument_id == "SS1/23"
        assert c.section == (2, 5)

    def test_ps_with_paragraph(self):
        c = parse_citation("PS9/24, paragraph 4.1")
        assert c.instrument == "PS"
        assert c.section == (4, 1)

    def test_paragraph_alias_para(self):
        c = parse_citation("SS1/23, para 2.5")
        assert c.section == (2, 5)

    def test_paragraph_single_level(self):
        c = parse_citation("SS1/23, paragraph 2")
        assert c.section == (2,)

    def test_paragraph_deep(self):
        c = parse_citation("SS1/23, paragraph 2.5.1")
        assert c.section == (2, 5, 1)

    def test_no_space_after_comma(self):
        c = parse_citation("SS1/23,paragraph 2.5")
        assert c.section == (2, 5)

    def test_internal_whitespace_in_code(self):
        c = parse_citation("PS 9/24")
        assert c.instrument_id == "PS9/24"

    def test_lowercase_code(self):
        c = parse_citation("ps9/24")
        assert c.instrument_id == "PS9/24"

    def test_unknown_tail_errors(self):
        with pytest.raises(CitationParseError, match="unrecognised tail"):
            parse_citation("SS1/23, chapter 4")

    def test_trailing_comma_errors(self):
        with pytest.raises(CitationParseError, match="trailing comma"):
            parse_citation("SS1/23,")


# ---------------------------------------------------------------------------
# Delegated Regulations
# ---------------------------------------------------------------------------


class TestDelegatedRegulation:
    def test_whole_instrument(self):
        c = parse_citation("Delegated Regulation 2018/171")
        assert c.instrument == "DELEGATED_REG"
        assert c.instrument_id == "2018/171"
        assert c.article is None

    def test_with_article(self):
        c = parse_citation("Delegated Regulation 2018/171 Art. 3")
        assert c.instrument == "DELEGATED_REG"
        assert c.instrument_id == "2018/171"
        assert c.article == 3

    def test_short_keyword(self):
        c = parse_citation("Delegated Reg 2018/171 Art. 3")
        assert c.article == 3

    def test_with_paragraph_and_point(self):
        c = parse_citation("Delegated Regulation 2018/171 Art. 3(1)(b)")
        assert c.article == 3 and c.paragraph == 1 and c.point == "b"


# ---------------------------------------------------------------------------
# Unrecognised / wholly invalid inputs
# ---------------------------------------------------------------------------


class TestRejection:
    def test_empty_string(self):
        with pytest.raises(CitationParseError, match="empty"):
            parse_citation("")

    def test_whitespace_only(self):
        with pytest.raises(CitationParseError, match="empty"):
            parse_citation("   ")

    def test_non_string(self):
        with pytest.raises(CitationParseError, match="must be a string"):
            parse_citation(123)  # ty: ignore[invalid-argument-type]

    def test_none(self):
        with pytest.raises(CitationParseError, match="must be a string"):
            parse_citation(None)  # ty: ignore[invalid-argument-type]

    def test_unknown_instrument(self):
        with pytest.raises(CitationParseError, match="unrecognised instrument"):
            parse_citation("Foo Art. 3")

    def test_legible_but_unsupported_format(self):
        with pytest.raises(CitationParseError):
            parse_citation("153(1)(a)")


# ---------------------------------------------------------------------------
# Citation object behaviour
# ---------------------------------------------------------------------------


class TestCitationObject:
    def test_equality_ignores_raw(self):
        a = parse_citation("CRR Art. 153(1)(a)")
        b = parse_citation("CRR Article 153(1)(a)")
        assert a == b

    def test_hashable(self):
        c = parse_citation("CRR Art. 153(1)(a)")
        d = {c: "ok"}
        assert d[parse_citation("CRR Article 153(1)(a)")] == "ok"

    def test_frozen(self):
        import dataclasses

        c = parse_citation("CRR Art. 153")
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.article = 154  # ty: ignore[possibly-unbound-attribute]

    def test_canonical_roundtrip_crr(self):
        for s in [
            "CRR Art. 153",
            "CRR Art. 153(1)",
            "CRR Art. 153(1)(a)",
            "CRR Art. 153(1)(a)(ii)",
            "CRR Art. 4(1)(75)",
        ]:
            c = parse_citation(s)
            assert parse_citation(c.canonical()) == c

    def test_canonical_roundtrip_pra(self):
        for s in [
            "PRA Rulebook, Credit Risk, 3.2",
            "PRA Rulebook, Credit Risk",
            "PS9/24",
            "SS1/23, paragraph 2.5",
        ]:
            c = parse_citation(s)
            assert parse_citation(c.canonical()) == c

    def test_is_more_specific_than(self):
        broad = parse_citation("CRR Art. 153")
        narrow = parse_citation("CRR Art. 153(1)(a)")
        assert narrow.is_more_specific_than(broad)
        assert not broad.is_more_specific_than(narrow)
        assert not broad.is_more_specific_than(broad)

    def test_specificity_requires_same_target(self):
        a = parse_citation("CRR Art. 153(1)(a)")
        b = parse_citation("CRR Art. 154(1)(a)")
        assert not a.is_more_specific_than(b)


# ---------------------------------------------------------------------------
# Direct construction
# ---------------------------------------------------------------------------


class TestDirectConstruction:
    def test_can_build_citation_without_string(self):
        c = Citation(instrument="CRR", article=153, paragraph=1, point="a")
        assert c.article == 153 and c.paragraph == 1 and c.point == "a"

    def test_constructed_citation_equals_parsed(self):
        constructed = Citation(instrument="CRR", article=153, paragraph=1, point="a")
        parsed = parse_citation("CRR Art. 153(1)(a)")
        assert constructed == parsed
