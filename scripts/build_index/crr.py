"""Scrape and parse CRR (Regulation EU 575/2013) articles from legislation.gov.uk.

The UK-retained version of CRR is published as CLML XML. The element
naming for EU regulations differs from UK Acts:

- ``<P1 id="article-N">``  = the Article (Pnumber says "Article N")
- ``<P2 id="article-N-M">`` = paragraph M of article N
- ``<P3>`` or ``<OrderedList><ListItem>`` = numbered/lettered points
- Further ``<OrderedList>`` nesting = subpoints

For paragraphs and points without explicit ``Pnumber`` we derive the
label from ``OrderedList`` position + ``Type``:

- ``Type="arabic"`` -> ``"1"``, ``"2"``, ...
- ``Type="alpha"``  -> ``"a"``, ``"b"``, ...
- ``Type="roman"``  -> ``"i"``, ``"ii"``, ...

Row emission per article:

- One article-level row carrying the full article text.
- One row per paragraph (carrying the full paragraph text).
- One row per point inside a paragraph.
- One row per subpoint inside a point.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from scripts.build_index.http import default_cache_dir, get_cached, make_client
from scripts.build_index.schema import Row

CRR_NUMBER = "2013/575"
BASE_URL = f"https://www.legislation.gov.uk/eur/{CRR_NUMBER}"
TOC_URL = f"{BASE_URL}/contents/data.xml"
ARTICLE_URL_TEMPLATE = f"{BASE_URL}/article/{{n}}/data.xml"
HUMAN_URL_TEMPLATE = f"{BASE_URL}/article/{{n}}"

# Elements we never want in extracted text.
_TEXT_EXCLUDED = {"CommentaryRef", "FootnoteRef"}
# Elements that are structural subdivisions; their subtrees are owned by
# nested rows so we exclude them when collecting a parent's "own" text.
_STRUCTURAL = {"P2", "P3", "P4", "OrderedList"}


@dataclass(frozen=True)
class _Paragraph:
    number: int | None
    label: str | None  # raw label for non-integer paragraphs, e.g. "1A"
    elem: etree._Element


@dataclass(frozen=True)
class _Point:
    label: str
    elem: etree._Element


@dataclass(frozen=True)
class _Subpoint:
    label: str
    elem: etree._Element


def fetch_toc(cache_dir: Path, *, refresh: bool = False) -> list[int]:
    cache_path = cache_dir / "eur-2013-575" / "contents.xml"
    with make_client() as client:
        xml = get_cached(client, TOC_URL, cache_path, refresh=refresh)
    return sorted(_extract_article_numbers(xml))


def fetch_article_xml(article: int, cache_dir: Path, *, refresh: bool = False) -> bytes:
    cache_path = cache_dir / "eur-2013-575" / f"article-{article}.xml"
    with make_client() as client:
        return get_cached(
            client,
            ARTICLE_URL_TEMPLATE.format(n=article),
            cache_path,
            refresh=refresh,
        )


def iter_crr_rows(
    cache_dir: Path | None = None,
    *,
    refresh: bool = False,
    only_articles: Iterable[int] | None = None,
) -> Iterable[Row]:
    if cache_dir is None:
        repo_root = Path(__file__).resolve().parents[2]
        cache_dir = default_cache_dir(repo_root)

    articles = fetch_toc(cache_dir, refresh=refresh)
    if only_articles is not None:
        wanted = set(only_articles)
        articles = [a for a in articles if a in wanted]

    print(f"crr: {len(articles)} articles to process")
    with make_client() as client:
        for n in articles:
            cache_path = cache_dir / "eur-2013-575" / f"article-{n}.xml"
            try:
                xml = get_cached(
                    client,
                    ARTICLE_URL_TEMPLATE.format(n=n),
                    cache_path,
                    refresh=refresh,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"crr: skipped article {n}: {exc}")
                continue
            yield from parse_clml_article(n, xml)


def parse_clml_article(article: int, xml: bytes) -> Iterable[Row]:
    try:
        root = etree.fromstring(xml)
    except etree.XMLSyntaxError as exc:
        print(f"crr: failed to parse article {article}: {exc}")
        return

    article_elem = _find_article_element(root, article)
    if article_elem is None:
        print(f"crr: no P1 element for article {article}")
        return

    title = _article_title(article_elem, article)
    url = HUMAN_URL_TEMPLATE.format(n=article)
    full_text = _gather_text(article_elem)
    if not full_text:
        return

    yield Row(
        instrument="CRR",
        instrument_id=None,
        article=article,
        paragraph=None,
        point=None,
        subpoint=None,
        section=None,
        title=title,
        content_text=full_text,
        url=url,
    )

    for paragraph in _iter_paragraphs(article_elem):
        para_text = _gather_text(paragraph.elem)
        if para_text:
            yield Row(
                instrument="CRR",
                instrument_id=None,
                article=article,
                paragraph=paragraph.number,
                point=None,
                subpoint=None,
                section=None,
                title=title,
                content_text=para_text,
                url=url,
            )
        for point in _iter_points(paragraph.elem):
            point_text = _gather_text(point.elem)
            if point_text:
                yield Row(
                    instrument="CRR",
                    instrument_id=None,
                    article=article,
                    paragraph=paragraph.number,
                    point=point.label,
                    subpoint=None,
                    section=None,
                    title=title,
                    content_text=point_text,
                    url=url,
                )
            for sub in _iter_subpoints(point.elem):
                sub_text = _gather_text(sub.elem)
                if sub_text:
                    yield Row(
                        instrument="CRR",
                        instrument_id=None,
                        article=article,
                        paragraph=paragraph.number,
                        point=point.label,
                        subpoint=sub.label,
                        section=None,
                        title=title,
                        content_text=sub_text,
                        url=url,
                    )


# ---- internals -----------------------------------------------------------


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _extract_article_numbers(xml: bytes) -> set[int]:
    try:
        root = etree.fromstring(xml)
    except etree.XMLSyntaxError:
        return set()
    numbers: set[int] = set()
    for elem in root.iter():
        for attr in ("DocumentURI", "IdURI", "href"):
            value = elem.get(attr)
            if value is None:
                continue
            match = re.search(r"/article/(\d+)(?:/|$)", value)
            if match:
                numbers.add(int(match.group(1)))
    return numbers


def _find_article_element(root: etree._Element, article: int) -> etree._Element | None:
    """Return ``<P1 id="article-N">`` for the requested article."""

    target_id = f"article-{article}"
    for elem in root.iter():
        if _local(elem.tag) == "P1" and elem.get("id") == target_id:
            return elem
    # Fallback: first P1 with id starting article-{N}
    for elem in root.iter():
        if _local(elem.tag) == "P1":
            eid = elem.get("id") or ""
            if eid.startswith(target_id):
                return elem
    return None


def _article_title(article_elem: etree._Element, article: int) -> str:
    """CRR title sits in a sibling ``<Title>``; fall back to Pnumber text."""

    # The <Title> for the article is a sibling under the P1group containing
    # the article's P1. Walk upward to P1group/EUTitle to find it.
    parent = article_elem.getparent()
    if parent is not None:
        for sibling in parent:
            if _local(sibling.tag) == "Title":
                text = _gather_text(sibling)
                if text:
                    return text
    return f"Article {article}"


def _gather_text(elem: etree._Element) -> str:
    """Collect human-visible text, skipping structural and ref tags."""

    parts: list[str] = []

    def _walk(node: etree._Element, is_root: bool) -> None:
        tag = _local(node.tag)
        if not is_root and tag in _STRUCTURAL:
            return
        if tag in _TEXT_EXCLUDED:
            return
        if node.text:
            parts.append(node.text)
        for child in node:
            _walk(child, is_root=False)
            if child.tail:
                ctag = _local(child.tag)
                if ctag not in _TEXT_EXCLUDED:
                    parts.append(child.tail)

    _walk(elem, is_root=True)
    return _normalise_whitespace("".join(parts))


def _normalise_whitespace(text: str) -> str:
    # Normalise NBSP (U+00A0) to plain space; CLML uses it liberally.
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _pnumber(elem: etree._Element) -> str | None:
    """Return the explicit Pnumber for ``elem`` if any (whitespace-stripped)."""

    for child in elem:
        if _local(child.tag) == "Pnumber":
            text = _gather_text(child)
            text = text.strip().strip("()").strip()
            return text or None
    return None


def _iter_paragraphs(article_elem: etree._Element) -> Iterable[_Paragraph]:
    """Yield paragraphs of an article.

    First preference: explicit ``<P2 id="article-N-M">`` children. If
    none exist, the article body itself is treated as one unnumbered
    paragraph (so single-paragraph articles still get a paragraph row
    when their content sits directly in ``<P1para>``).
    """

    p2_children: list[etree._Element] = []
    for p1para in article_elem:
        if _local(p1para.tag) != "P1para":
            continue
        for child in p1para:
            if _local(child.tag) == "P2":
                p2_children.append(child)
    if p2_children:
        for p2 in p2_children:
            raw = _pnumber(p2)
            yield _Paragraph(number=_to_int(raw), label=raw, elem=p2)
        return

    # No P2 — treat the article body as a single unnumbered paragraph.
    # We yield the article element itself so points come from any
    # OrderedList inside its P1para children.
    yield _Paragraph(number=None, label=None, elem=article_elem)


_LIST_TYPE_TO_FORMATTER = {
    "alpha": lambda i: _alpha_label(i),
    "roman": lambda i: _roman_label(i),
    "arabic": lambda i: str(i + 1),
}


def _alpha_label(idx: int) -> str:
    """0 -> 'a', 25 -> 'z', 26 -> 'aa'."""
    out = ""
    n = idx
    while True:
        out = chr(ord("a") + (n % 26)) + out
        n = n // 26 - 1
        if n < 0:
            break
    return out


def _roman_label(idx: int) -> str:
    """1-based lowercase roman."""
    n = idx + 1
    pairs = (
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    )
    out = []
    for value, letters in pairs:
        while n >= value:
            out.append(letters)
            n -= value
    return "".join(out)


def _iter_points(paragraph_elem: etree._Element) -> Iterable[_Point]:
    """Yield points inside a paragraph.

    Two shapes are recognised:

    1. Explicit ``<P3>`` children inside any ``<P2para>``.
    2. Otherwise a top-level ``<OrderedList>`` whose ``<ListItem>``
       siblings produce labels from their position + Type.
    """

    p3_children: list[etree._Element] = []
    ordered_lists: list[etree._Element] = []
    for child in paragraph_elem.iter():
        tag = _local(child.tag)
        # Only first-generation occurrences (no intervening same-tag ancestor).
        if tag == "P3" and not _has_ancestor_of_type(child, paragraph_elem, "P3"):
            p3_children.append(child)
        elif tag == "OrderedList" and not _has_ancestor_of_type(
            child, paragraph_elem, "OrderedList"
        ):
            ordered_lists.append(child)
    if p3_children:
        for p3 in p3_children:
            label = _pnumber(p3) or ""
            if label:
                yield _Point(label=label, elem=p3)
        return
    for ol in ordered_lists:
        list_type = (ol.get("Type") or "arabic").lower()
        formatter = _LIST_TYPE_TO_FORMATTER.get(list_type, lambda i: str(i + 1))
        items = [c for c in ol if _local(c.tag) == "ListItem"]
        for idx, item in enumerate(items):
            yield _Point(label=formatter(idx), elem=item)


def _iter_subpoints(point_elem: etree._Element) -> Iterable[_Subpoint]:
    """Yield subpoints inside a point (one level deeper)."""

    p4_children: list[etree._Element] = []
    ordered_lists: list[etree._Element] = []
    for child in point_elem.iter():
        tag = _local(child.tag)
        if tag == "P4" and not _has_ancestor_of_type(child, point_elem, "P4"):
            p4_children.append(child)
        elif tag == "OrderedList" and not _has_ancestor_of_type(child, point_elem, "OrderedList"):
            ordered_lists.append(child)
    if p4_children:
        for p4 in p4_children:
            label = _pnumber(p4) or ""
            if label:
                yield _Subpoint(label=label, elem=p4)
        return
    for ol in ordered_lists:
        list_type = (ol.get("Type") or "roman").lower()
        formatter = _LIST_TYPE_TO_FORMATTER.get(list_type, _roman_label)
        items = [c for c in ol if _local(c.tag) == "ListItem"]
        for idx, item in enumerate(items):
            yield _Subpoint(label=formatter(idx), elem=item)


def _has_ancestor_of_type(elem: etree._Element, boundary: etree._Element, tag: str) -> bool:
    """True if ``elem`` has an ancestor with local name ``tag`` before
    reaching ``boundary``."""

    parent = elem.getparent()
    while parent is not None and parent is not boundary:
        if _local(parent.tag) == tag:
            return True
        parent = parent.getparent()
    return False


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
