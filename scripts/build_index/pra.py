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
from dataclasses import dataclass
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
        local_txt="PS1-26.txt",
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
                    paragraphs = parse_pdf_paragraphs(pdf_path)
                except Exception as exc:  # noqa: BLE001 - log and continue
                    print(f"pra: PDF parse failed for {source.instrument_id}: {exc}")
                else:
                    yield from _rows_from_paragraphs(source, paragraphs)
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
