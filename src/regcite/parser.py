"""Parse canonical regulatory citation strings into :class:`Citation`.

The grammar is small enough that a regex per instrument is clearer than
a full parser combinator. The dispatch is keyword-driven on the leading
token; each branch produces a structured :class:`Citation` or raises
:class:`CitationParseError` with a message that names the offending
input.
"""

from __future__ import annotations

import re

from regcite.model import Citation

__all__ = ["CitationParseError", "parse_citation"]


class CitationParseError(ValueError):
    """Raised when a citation string cannot be parsed.

    The exception message always contains the offending input, quoted,
    and a short reason. ``regcite check`` surfaces these directly so
    fixing a bad citation is a question of reading the message.
    """


# A token like "(1)", "(a)", "(ii)", "(75)". Captures the inner value.
_PAREN_TOKEN = re.compile(r"\(([^()\s]+)\)")

# A bare integer (used for paragraph parsing in SS/PS where the number
# is sometimes given without parentheses).
_INT_RE = re.compile(r"\d+")

# Section path like "3.2" or "3.2.1". Anchored.
_SECTION_RE = re.compile(r"^\d+(?:\.\d+)*$")

# PS / SS document codes: "PS9/24", "SS1/23".
_PS_ID_RE = re.compile(r"^(PS|SS)\s*(\d+\s*/\s*\d+)$", re.IGNORECASE)


def parse_citation(s: str) -> Citation:
    """Parse a canonical citation string.

    Accepts the forms documented in the project README. Whitespace is
    normalised; the keyword for ``article`` accepts ``Art``, ``Art.``,
    ``Article`` (any case). Returns a :class:`Citation`; raises
    :class:`CitationParseError` on any malformed input.
    """

    if not isinstance(s, str):
        raise CitationParseError(f"citation must be a string, got {type(s).__name__}")

    text = s.strip()
    if not text:
        raise CitationParseError("citation string is empty")

    # Look at the leading word(s) to choose a parser.
    upper = text.upper()

    if upper.startswith("CRR"):
        return _parse_article_based(text, instrument="CRR", prefix_len=3)

    if upper.startswith("DELEGATED REGULATION") or upper.startswith("DELEGATED REG"):
        return _parse_delegated(text)

    if upper.startswith("PRA RULEBOOK"):
        return _parse_pra_rulebook(text)

    # PS9/24 or SS1/23 (with optional ", paragraph X" tail).
    head, _, _ = text.partition(",")
    head_compact = re.sub(r"\s+", "", head)
    m = _PS_ID_RE.match(head_compact)
    if m:
        return _parse_pra_publication(text, m.group(1).upper(), head.strip())

    raise CitationParseError(
        f"unrecognised instrument in citation {s!r}; "
        "expected one of CRR, PRA Rulebook, PS<n>/<yy>, SS<n>/<yy>, "
        "Delegated Regulation"
    )


# ---------------------------------------------------------------------------
# Article-structured instruments: CRR and Delegated Regulations.
# ---------------------------------------------------------------------------

_ARTICLE_KEYWORD = re.compile(r"art(?:icle)?\.?", re.IGNORECASE)


def _parse_article_based(
    text: str,
    *,
    instrument: str,
    prefix_len: int,
    instrument_id: str | None = None,
) -> Citation:
    body = text[prefix_len:].lstrip(" \t,;:")
    return _parse_article_body(text, body, instrument, instrument_id)


def _parse_article_body(
    raw: str,
    body: str,
    instrument: str,
    instrument_id: str | None,
) -> Citation:
    m = _ARTICLE_KEYWORD.match(body)
    if not m:
        raise CitationParseError(f"expected 'Art.' or 'Article' after '{instrument}' in {raw!r}")
    rest = body[m.end() :].lstrip()
    num_match = re.match(r"(\d+)", rest)
    if not num_match:
        raise CitationParseError(f"expected article number after 'Art.' in {raw!r}")
    article = int(num_match.group(1))
    if article == 0:
        raise CitationParseError(f"article number must be positive in {raw!r}")

    tail = rest[num_match.end() :].strip()
    paragraph, point, subpoint = _parse_paren_tail(tail, raw)

    return Citation(
        instrument=instrument,  # ty: ignore[invalid-argument-type]
        instrument_id=instrument_id,
        article=article,
        paragraph=paragraph,
        point=point,
        subpoint=subpoint,
        raw=raw,
    )


def _parse_paren_tail(tail: str, raw: str) -> tuple[int | None, str | None, str | None]:
    """Parse the ``(1)(a)(ii)`` portion that follows an article number.

    Returns a (paragraph, point, subpoint) triple. Missing positions are
    ``None``. Any non-empty, non-parenthesised residue is an error: it
    means the citation has unexpected trailing text.
    """

    if not tail:
        return None, None, None

    tokens: list[str] = []
    pos = 0
    while pos < len(tail):
        # Skip whitespace between tokens.
        while pos < len(tail) and tail[pos].isspace():
            pos += 1
        if pos >= len(tail):
            break
        m = _PAREN_TOKEN.match(tail, pos)
        if not m:
            raise CitationParseError(
                f"unexpected text after article number in {raw!r} "
                f"(at offset {pos} of tail {tail!r})"
            )
        tokens.append(m.group(1))
        pos = m.end()

    if len(tokens) > 3:
        raise CitationParseError(
            f"too many parenthesised parts in {raw!r}; "
            f"expected at most (paragraph)(point)(subpoint)"
        )

    paragraph: int | None = None
    point: str | None = None
    subpoint: str | None = None

    if tokens:
        first = tokens[0]
        if not first.isdigit():
            raise CitationParseError(f"paragraph must be an integer in {raw!r}, got '({first})'")
        paragraph = int(first)
    if len(tokens) >= 2:
        point = tokens[1]
    if len(tokens) == 3:
        subpoint = tokens[2]

    return paragraph, point, subpoint


# ---------------------------------------------------------------------------
# Delegated Regulation: "Delegated Regulation 2018/171 Art. 3"
# ---------------------------------------------------------------------------

_DELEGATED_HEAD = re.compile(
    r"^delegated\s+reg(?:ulation)?\s+([0-9]+/[0-9]+)\s*",
    re.IGNORECASE,
)


def _parse_delegated(text: str) -> Citation:
    m = _DELEGATED_HEAD.match(text)
    if not m:
        raise CitationParseError(f"expected 'Delegated Regulation <year>/<num>' in {text!r}")
    instrument_id = m.group(1)
    body = text[m.end() :].lstrip(" \t,;:")
    if not body:
        return Citation(instrument="DELEGATED_REG", instrument_id=instrument_id, raw=text)
    return _parse_article_body(text, body, "DELEGATED_REG", instrument_id)


# ---------------------------------------------------------------------------
# PRA Rulebook: "PRA Rulebook, Credit Risk, 3.2"
# ---------------------------------------------------------------------------


def _parse_pra_rulebook(text: str) -> Citation:
    # Strip leading "PRA Rulebook" (case-insensitive, optional comma).
    body = re.sub(r"^pra\s+rulebook\s*,?\s*", "", text, flags=re.IGNORECASE)
    if not body.strip():
        raise CitationParseError(
            f"PRA Rulebook citation must name a part in {text!r}, "
            "e.g. 'PRA Rulebook, Credit Risk, 3.2'"
        )

    # Split on the final section path: trailing token that looks like
    # "N", "N.N", "N.N.N" etc.
    parts = [p.strip() for p in body.split(",") if p.strip()]
    section: tuple[int, ...] | None = None
    if parts and _SECTION_RE.match(parts[-1]):
        section = tuple(int(n) for n in parts[-1].split("."))
        parts = parts[:-1]

    if not parts:
        raise CitationParseError(
            f"PRA Rulebook citation must name a part in {text!r}, "
            "e.g. 'PRA Rulebook, Credit Risk, 3.2'"
        )

    instrument_id = ", ".join(parts)
    return Citation(
        instrument="PRA_RULEBOOK",
        instrument_id=instrument_id,
        section=section,
        raw=text,
    )


# ---------------------------------------------------------------------------
# PRA Publications: PS9/24 and SS1/23, optionally with a paragraph tail.
# ---------------------------------------------------------------------------

_PARAGRAPH_TAIL = re.compile(
    r"^(?:paragraph|para|paragraphs|¶)\s+(\d+(?:\.\d+)*)\s*$",
    re.IGNORECASE,
)


def _parse_pra_publication(text: str, kind: str, head: str) -> Citation:
    # Canonicalise the document id: "PS 9 / 24" -> "PS9/24".
    instrument_id = re.sub(r"\s+", "", head).upper()
    # Validate the canonical form before continuing.
    if not _PS_ID_RE.match(instrument_id):
        raise CitationParseError(f"expected '{kind}<n>/<yy>' in {text!r}")

    _, sep, tail = text.partition(",")
    if not sep:
        return Citation(instrument=kind, instrument_id=instrument_id, raw=text)  # ty: ignore[invalid-argument-type]

    tail = tail.strip()
    if not tail:
        raise CitationParseError(f"trailing comma with no paragraph reference in {text!r}")

    m = _PARAGRAPH_TAIL.match(tail)
    if not m:
        raise CitationParseError(
            f"unrecognised tail '{tail}' in {text!r}; expected 'paragraph N' or 'paragraph N.N'"
        )

    section = tuple(int(n) for n in m.group(1).split("."))
    return Citation(
        instrument=kind,  # ty: ignore[invalid-argument-type]
        instrument_id=instrument_id,
        section=section,
        raw=text,
    )
