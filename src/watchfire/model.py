"""Structured representation of a regulatory citation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

_LOCATING_FIELDS = (
    "article",
    "section",
    "paragraph",
    "point",
    "subpoint",
    "subparagraph",
)

Instrument = Literal[
    "CRR",  # UK on-shored Capital Requirements Regulation (EU 575/2013)
    "PRA_RULEBOOK",  # PRA Rulebook
    "PS",  # PRA Policy Statement (e.g. PS9/24)
    "SS",  # PRA Supervisory Statement (e.g. SS1/23)
    "DELEGATED_REG",  # EU Delegated Regulation, UK on-shored
]


@dataclass(frozen=True)
class Citation:
    """A structured citation to a regulatory instrument.

    Use :func:`watchfire.parse_citation` to construct one from a string;
    construct directly only when the structured form is more convenient
    than the canonical text.

    Attributes:
        instrument: The regulatory instrument class.
        instrument_id: Identifier within the instrument class. ``"PS9/24"``
            for a Policy Statement, ``"Credit Risk"`` for a PRA Rulebook
            part. ``None`` for CRR (there is only one).
        article: Article identifier for article-structured instruments
            (CRR, Delegated Regulations). A string so that inserted
            articles with letter suffixes (e.g. ``"92a"``) are
            representable; pure-numeric values are stored as digit
            strings (``"153"``).
        section: Hierarchical section path, used by the PRA Rulebook and
            by Supervisory/Policy Statements. ``("2", "5")`` corresponds
            to ``"2.5"``; PS/SS segments may carry a letter suffix
            (``"123B"``).
        paragraph: Numbered paragraph within an article (the first level
            of parenthesised numbering in CRR). String-valued for the
            same reason as ``article``: rare alphanumeric forms like
            ``"1a"`` are valid.
        point: Sub-paragraph reference. Most commonly an alphabetic
            letter (``"a"``), but CRR Article 4(1)(75) uses numeric
            points for definitions, so this is a string.
        subpoint: Lower-level reference, typically a roman numeral
            (``"ii"``).
        subparagraph: Index into an unnumbered subparagraph (CRR uses
            phrases like "the second subparagraph of paragraph 1").
        version: Pinned version of the instrument the citation was
            written against. If ``None`` the citation inherits the
            project pin from ``[tool.watchfire]``.
    """

    instrument: Instrument
    instrument_id: str | None = None
    article: str | None = None
    section: tuple[str, ...] | None = None
    paragraph: str | None = None
    point: str | None = None
    subpoint: str | None = None
    subparagraph: int | None = None
    version: date | None = None

    # Stored solely so error messages and round-tripping can refer back
    # to what the user wrote. Excluded from equality and hashing so two
    # citations that parsed from differently-spelled-but-equivalent
    # strings compare equal.
    raw: str | None = field(default=None, compare=False, hash=False, repr=False)

    def canonical(self) -> str:
        """Return a canonical string form of this citation.

        Round-tripping ``parse_citation(c.canonical()) == c`` is
        guaranteed for citations produced by :func:`parse_citation`.
        """

        if self.instrument == "CRR":
            return _format_article("CRR", self)
        if self.instrument == "DELEGATED_REG":
            head = (
                f"Delegated Regulation {self.instrument_id}"
                if self.instrument_id
                else "Delegated Regulation"
            )
            return _format_article(head, self)
        if self.instrument == "PRA_RULEBOOK":
            parts = ["PRA Rulebook"]
            if self.instrument_id:
                parts.append(self.instrument_id)
            if self.section:
                parts.append(".".join(str(n) for n in self.section))
            return ", ".join(parts)
        if self.instrument in ("PS", "SS"):
            base = self.instrument_id or self.instrument
            if self.section:
                return f"{base}, paragraph " + ".".join(str(n) for n in self.section)
            return base
        # Unreachable while Instrument literal is exhaustive.
        return self.raw or ""

    def is_more_specific_than(self, other: Citation) -> bool:
        """True if this citation refines ``other`` (same target, deeper).

        Useful for ``watchfire check`` when matching a citation against the
        index: a citation to a paragraph implies coverage of the article.
        """

        if self.instrument != other.instrument:
            return False
        if self.instrument_id != other.instrument_id:
            return False
        # For each locating field other specifies, self must match. Self
        # must also specify at least one field that other leaves None.
        own_extra = False
        for name in _LOCATING_FIELDS:
            theirs = getattr(other, name)
            mine = getattr(self, name)
            if theirs is not None:
                if mine != theirs:
                    return False
            elif mine is not None:
                own_extra = True
        return own_extra


def _format_article(prefix: str, c: Citation) -> str:
    if c.article is None:
        return prefix
    out = f"{prefix} Art. {c.article}"
    if c.paragraph is not None:
        out += f"({c.paragraph})"
    if c.point is not None:
        out += f"({c.point})"
    if c.subpoint is not None:
        out += f"({c.subpoint})"
    return out
