"""PRA Supervisory / Policy Statement entries for the index.

The Bank of England publishes SS / PS as PDFs and blocks automated
fetching. The strategy:

- A curated seed list of (instrument_id, title, url, optional local source).
- For each entry, emit a document-level row (``section=None``).
- If a local source file (PDF or pre-extracted text) is present at
  ``scripts/build_index/pra_pdfs/<file>``, additionally emit
  paragraph-level rows by matching dotted section numbers.

``pra_pdfs/`` is gitignored — contributors who want paragraph-level
granularity drop the source file in and rerun the build.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from scripts.build_index.schema import Row

PRA_PDF_DIR = Path(__file__).resolve().parent / "pra_pdfs"


@dataclass(frozen=True)
class PraSource:
    instrument: Literal["SS", "PS", "PRA_RULEBOOK"]
    instrument_id: str
    title: str
    summary: str
    url: str
    local_pdf: str | None = None  # filename within PRA_PDF_DIR, if any
    local_txt: str | None = None  # pre-extracted text, filename within PRA_PDF_DIR
    # Selects the paragraph-extraction strategy. ``"dotted"`` matches the
    # PRA Rulebook convention ("2.5.1 Firms must..."). ``"crr_article"``
    # matches CRR-style numbering ("Article 111 / 1. / (a) / (i)"), used
    # by rulebook instruments attached to a Policy Statement.
    parser_style: Literal["dotted", "crr_article"] = "dotted"


# Hand-maintained seed list. Add new SS / PS entries here as they are
# cited by downstream projects.
PRA_SOURCES: list[PraSource] = [
    PraSource(
        instrument="SS",
        instrument_id="SS1/23",
        title="Model risk management principles for banks",
        summary=(
            "PRA expectations on the governance, development, and validation "
            "of models used by banks."
        ),
        url=(
            "https://www.bankofengland.co.uk/prudential-regulation/publication/"
            "2023/may/model-risk-management-principles-for-banks-ss"
        ),
        local_pdf="SS1-23.pdf",
    ),
    PraSource(
        instrument="PS",
        instrument_id="PS9/24",
        title="Implementation of the Basel 3.1 standards — final rules",
        summary="Near-final PRA policy implementing Basel 3.1 in the UK.",
        url=(
            "https://www.bankofengland.co.uk/prudential-regulation/publication/"
            "2024/september/implementation-of-the-basel-3-1-standards-near-final-part-2"
        ),
        local_pdf="PS9-24.pdf",
    ),
    PraSource(
        instrument="PS",
        instrument_id="PS1/26",
        title="PRA Rulebook: CRR Firms: (CRR) Instrument 2026",
        summary=(
            "Implementation of Basel 3.1 final rules. PRA rulebook instrument "
            "effective 1 January 2027, attached to PS1/26."
        ),
        url=(
            "https://www.bankofengland.co.uk/prudential-regulation/publication/"
            "2026/january/implementation-of-basel-3-1-final-rules-policy-statement"
        ),
        local_pdf="ps126app1.pdf",
        parser_style="crr_article",
    ),
    PraSource(
        instrument="PRA_RULEBOOK",
        instrument_id="Credit Risk",
        title="Credit Risk part of the PRA Rulebook",
        summary=(
            "Quantitative and qualitative requirements on credit risk weighted exposure amounts."
        ),
        url="https://www.prarulebook.co.uk/rulebook/Content/Part/216147",
    ),
]


def iter_pra_rows(*, pdf_dir: Path | None = None) -> Iterable[Row]:
    """Yield document-level + (optionally) paragraph-level PRA rows."""

    pdf_dir = pdf_dir or PRA_PDF_DIR
    for source in PRA_SOURCES:
        yield Row(
            instrument=source.instrument,
            instrument_id=source.instrument_id,
            article=None,
            paragraph=None,
            point=None,
            subpoint=None,
            section=None,
            title=source.title,
            content_text=source.summary,
            url=source.url,
        )
        if source.local_pdf is not None:
            pdf_path = pdf_dir / source.local_pdf
            if not pdf_path.exists():
                print(f"pra: no PDF at {pdf_path} — emitting document-level only")
            else:
                try:
                    if source.parser_style == "crr_article":
                        articles = parse_crr_style_pdf(pdf_path)
                        yield from _rows_from_articles(source, articles)
                    else:
                        paragraphs = parse_pdf_paragraphs(pdf_path)
                        yield from _rows_from_paragraphs(source, paragraphs)
                except Exception as exc:  # noqa: BLE001 - log and continue
                    print(f"pra: PDF parse failed for {source.instrument_id}: {exc}")
        if source.local_txt is not None:
            txt_path = pdf_dir / source.local_txt
            if not txt_path.exists():
                print(f"pra: no TXT at {txt_path} — emitting document-level only")
            else:
                try:
                    paragraphs = parse_txt_paragraphs(txt_path)
                except Exception as exc:  # noqa: BLE001 - log and continue
                    print(f"pra: TXT parse failed for {source.instrument_id}: {exc}")
                else:
                    yield from _rows_from_paragraphs(source, paragraphs)


_SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.*)$")


def _paragraphs_from_lines(lines: Iterable[str]) -> list[tuple[str, str]]:
    """Group ``lines`` into ``[(section, text), ...]`` by dotted prefix.

    A line starting with a dotted number (``"2.5.1 foo"``) opens a new
    paragraph; subsequent lines are appended to its buffer until the
    next dotted opener. Lines before the first dotted opener are
    discarded.
    """

    out: list[tuple[str, str]] = []
    current_section: str | None = None
    current_buf: list[str] = []

    def _flush() -> None:
        if current_section is not None and current_buf:
            body = " ".join(s.strip() for s in current_buf if s.strip())
            if body:
                out.append((current_section, body))

    for line in lines:
        match = _SECTION_RE.match(line)
        if match:
            _flush()
            current_section = match.group(1)
            current_buf = [match.group(2)]
        else:
            current_buf.append(line)
    _flush()
    return out


def parse_pdf_paragraphs(pdf_path: Path) -> list[tuple[str, str]]:
    """Return ``[(section, text), ...]`` extracted from ``pdf_path``.

    Each tuple is a dotted section number (``"2.5.1"``) and the text up
    to the next numbered section. Best-effort: tables, footnotes, and
    pages with non-standard layout are absorbed into the nearest
    preceding paragraph.
    """

    from pypdf import PdfReader  # imported lazily to keep base import light

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        lines.extend(text.splitlines())
    return _paragraphs_from_lines(lines)


def parse_txt_paragraphs(txt_path: Path) -> list[tuple[str, str]]:
    """Return ``[(section, text), ...]`` extracted from a pre-extracted text file.

    Used when the PDF has been manually converted to plain text (e.g.
    BoE PDFs that ship without a clean machine-readable layer). Strips
    PRA page-header / footer boilerplate before applying the same
    dotted-section grouping as :func:`parse_pdf_paragraphs`.
    """

    # PDF extracts often contain stray cp1252 bytes (soft hyphens, smart
    # quotes); use errors="replace" so a few odd characters don't abort the
    # whole document. Section detection only depends on ASCII digits/dots.
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    return _paragraphs_from_lines(_strip_pra_boilerplate(text.splitlines()))


_PAGE_NUMBER_RE = re.compile(r"^\s*Page \d+ of \d+\s*$")
_LONE_PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,3}\s*$")
_PS_DOC_HEADER_RE = re.compile(r"^\s*PS\s*\d+\s*/\s*\d+\s*$", re.IGNORECASE)
_BOILERPLATE_PREFIXES = (
    "This document is effective from",
    "Please see: www.bankofengland.co.uk",
)


def _strip_pra_boilerplate(lines: Iterable[str]) -> Iterator[str]:
    """Drop the repeated page-header lines from a PRA PDF text dump."""

    for line in lines:
        stripped = line.strip()
        if _PAGE_NUMBER_RE.match(line):
            continue
        if _LONE_PAGE_NUMBER_RE.match(line):
            continue
        if _PS_DOC_HEADER_RE.match(line):
            continue
        if stripped == "PRA2026/1":
            continue
        if any(stripped.startswith(p) for p in _BOILERPLATE_PREFIXES):
            continue
        yield line


def _rows_from_paragraphs(
    source: PraSource, paragraphs: Iterable[tuple[str, str]]
) -> Iterable[Row]:
    for section, text in paragraphs:
        yield Row(
            instrument=source.instrument,
            instrument_id=source.instrument_id,
            article=None,
            paragraph=None,
            point=None,
            subpoint=None,
            section=section,
            title=source.title,
            content_text=text,
            url=source.url,
        )


# ---------------------------------------------------------------------------
# CRR-style PDF ingestion.
#
# Some PS instruments (notably PS 1/26 which attaches the CRR Firms (CRR)
# Instrument 2026) carry article-shaped content rather than dotted PRA
# Rulebook paragraphs. Each rule reads like a CRR article:
#
#     Article 111 EXPOSURE VALUE
#     1. The exposure value of:
#     (a) an asset item shall be ...
#     (b) subject to ...
#
# We extract these into rows shaped like CRR's: ``article`` /
# ``paragraph`` / ``point`` / ``subpoint`` populated, ``section`` is null.
# ---------------------------------------------------------------------------


@dataclass
class SubpointNode:
    label: str
    text: str = ""


@dataclass
class PointNode:
    label: str
    text: str = ""
    subpoints: list[SubpointNode] = field(default_factory=list)


@dataclass
class ParagraphNode:
    number: str
    chapeau: str = ""
    points: list[PointNode] = field(default_factory=list)


@dataclass
class ArticleNode:
    article: str
    title: str = ""
    paragraphs: list[ParagraphNode] = field(default_factory=list)


# Article header line: ``Article N`` alone, or ``Article N <TITLE>`` where
# the title starts with an uppercase letter and contains only uppercase
# letters / digits / spaces / common punctuation. This rejects in-body
# cross-references like ``Article 110 of Commission Delegated Regulation``
# and ``Article 166A, as applicable`` (the trailing text starts with
# lowercase ``of`` or with punctuation).
_ARTICLE_HEADER_RE = re.compile(r"^Article\s+(\d+[A-Za-z]*)(?:\s+([A-Z][A-Z0-9 ,'\-/&()]*))?\s*$")
_PARAGRAPH_OPENER_RE = re.compile(r"^(\d+[a-z]*)\.\s+(.*)$")
_POINT_OPENER_RE = re.compile(r"^\(([A-Za-z]{1,5})\)\s+(.*)$")
# Plausible point / subpoint labels: a single letter, or one of the roman
# numerals i..xx. Used to reject false positives like ``(see)``, ``(in)``,
# ``(EU)`` that look like point openers.
_VALID_POINT_LABEL_RE = re.compile(
    r"^(?:[a-z]"
    r"|i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3}|xiv|xv|xvi{0,3}|xix|xx)$",
    re.IGNORECASE,
)
_ROMAN_TOKENS = frozenset(
    {
        "i",
        "ii",
        "iii",
        "iv",
        "v",
        "vi",
        "vii",
        "viii",
        "ix",
        "x",
        "xi",
        "xii",
        "xiii",
        "xiv",
        "xv",
        "xvi",
        "xvii",
        "xviii",
        "xix",
        "xx",
    }
)


# Regexes used to coerce missing newlines back into the extracted text.
# pypdf sometimes joins "EXPOSURE VALUE1. The exposure" or "of:(a) an"
# into a single line; we insert breaks before structural markers.
_NORMALISE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Newline before a new "Article N" header.
    (re.compile(r"(?<!\n)(?=Article\s+\d+[A-Za-z]*\b)"), "\n"),
    # Newline before "N. " paragraph opener that follows text/punctuation.
    (re.compile(r"(?<=[A-Za-z.;:)])\s*(?=\d+[a-z]*\.\s+[A-Z(])"), "\n"),
    # Newline before "(x) " point opener that follows text/punctuation.
    (re.compile(r"(?<=[A-Za-z0-9.;:])(?=\([A-Za-z]{1,5}\)\s)"), "\n"),
)


def _normalise_structural_breaks(text: str) -> str:
    for pattern, repl in _NORMALISE_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _is_subpoint_label(label: str) -> bool:
    return label.lower() in _ROMAN_TOKENS


def _join_continuation(prev: str, new: str) -> str:
    """Append ``new`` to ``prev``, handling soft-hyphenation across wraps."""

    new = new.strip()
    if not new:
        return prev
    if not prev:
        return new
    if prev.endswith("-") and new and new[0].islower():
        return prev[:-1] + new
    return prev + " " + new


def _walk_crr_lines(lines: Iterable[str]) -> list[ArticleNode]:
    """Group CRR-style PDF lines into an ``ArticleNode`` tree.

    The walker is a small state machine: an ``Article N`` line opens an
    article, ``N.`` opens a paragraph, ``(x)`` opens a point (or a
    subpoint if a point is already open and the label looks like a roman
    numeral). Any line that doesn't match an opener is appended to the
    deepest open container's text buffer.

    Note on ``(i)`` vs ``(a)``: ``(i)/(ii)/...`` is treated as a subpoint
    *only* when a point is currently open. If a paragraph's first point
    is ``(i)`` (legal but rare in CRR drafting) it is labeled as a point.
    """

    articles: list[ArticleNode] = []
    current_article: ArticleNode | None = None
    current_paragraph: ParagraphNode | None = None
    current_point: PointNode | None = None
    current_subpoint: SubpointNode | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        m = _ARTICLE_HEADER_RE.match(line)
        if m:
            article_num = m.group(1)
            title = (m.group(2) or "").strip()
            current_article = ArticleNode(article=article_num, title=title)
            articles.append(current_article)
            current_paragraph = None
            current_point = None
            current_subpoint = None
            continue

        if current_article is None:
            continue

        m = _PARAGRAPH_OPENER_RE.match(line)
        if m:
            current_paragraph = ParagraphNode(number=m.group(1), chapeau=m.group(2).strip())
            current_article.paragraphs.append(current_paragraph)
            current_point = None
            current_subpoint = None
            continue

        if current_point is not None:
            m = _POINT_OPENER_RE.match(line)
            if m and _is_subpoint_label(m.group(1)):
                current_subpoint = SubpointNode(label=m.group(1), text=m.group(2).strip())
                current_point.subpoints.append(current_subpoint)
                continue

        if current_paragraph is not None:
            m = _POINT_OPENER_RE.match(line)
            if m and _VALID_POINT_LABEL_RE.match(m.group(1)):
                current_point = PointNode(label=m.group(1), text=m.group(2).strip())
                current_paragraph.points.append(current_point)
                current_subpoint = None
                continue

        # Continuation: append to deepest open buffer.
        if current_subpoint is not None:
            current_subpoint.text = _join_continuation(current_subpoint.text, line)
        elif current_point is not None:
            current_point.text = _join_continuation(current_point.text, line)
        elif current_paragraph is not None:
            current_paragraph.chapeau = _join_continuation(current_paragraph.chapeau, line)
        else:
            current_article.title = _join_continuation(current_article.title, line)

    return articles


def parse_crr_style_pdf(pdf_path: Path) -> list[ArticleNode]:
    """Parse a CRR-style PDF into ``ArticleNode`` trees.

    Extracts page text via ``pypdf``, normalises missing line breaks
    around structural markers (``Article N``, ``N.``, ``(x)``), strips
    PRA page-header boilerplate, then runs the walker.
    """

    from pypdf import PdfReader  # imported lazily to keep base import light

    reader = PdfReader(str(pdf_path))
    page_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    normalised = _normalise_structural_breaks(page_text)
    cleaned = _strip_pra_boilerplate(normalised.splitlines())
    return _walk_crr_lines(cleaned)


def _rows_from_articles(source: PraSource, articles: Iterable[ArticleNode]) -> Iterable[Row]:
    """Emit one ``Row`` per CRR-style node (article / paragraph / point / subpoint)."""

    for article in articles:
        article_title = article.title.strip() or f"Article {article.article}"
        yield Row(
            instrument=source.instrument,
            instrument_id=source.instrument_id,
            article=article.article,
            paragraph=None,
            point=None,
            subpoint=None,
            section=None,
            title=source.title,
            content_text=article_title,
            url=source.url,
        )
        for paragraph in article.paragraphs:
            chapeau = paragraph.chapeau.strip()
            if chapeau:
                yield Row(
                    instrument=source.instrument,
                    instrument_id=source.instrument_id,
                    article=article.article,
                    paragraph=paragraph.number,
                    point=None,
                    subpoint=None,
                    section=None,
                    title=source.title,
                    content_text=chapeau,
                    url=source.url,
                )
            for point in paragraph.points:
                point_text = point.text.strip()
                if point_text:
                    yield Row(
                        instrument=source.instrument,
                        instrument_id=source.instrument_id,
                        article=article.article,
                        paragraph=paragraph.number,
                        point=point.label,
                        subpoint=None,
                        section=None,
                        title=source.title,
                        content_text=point_text,
                        url=source.url,
                    )
                for sub in point.subpoints:
                    sub_text = sub.text.strip()
                    if sub_text:
                        yield Row(
                            instrument=source.instrument,
                            instrument_id=source.instrument_id,
                            article=article.article,
                            paragraph=paragraph.number,
                            point=point.label,
                            subpoint=sub.label,
                            section=None,
                            title=source.title,
                            content_text=sub_text,
                            url=source.url,
                        )
