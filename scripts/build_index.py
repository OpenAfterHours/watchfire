"""Hand-curated CRR index builder.

This script writes ``src/watchfire/data/index.parquet``, which is shipped
inside the wheel and consulted by ``watchfire check``.

For v0.1 we do not scrape ``legislation.gov.uk`` — the data here is
hand-curated against the on-shored CRR snapshot dated 2024-07-09. Each
article entry carries a short summary in ``content_text`` (the full
statutory text lives on legislation.gov.uk via ``url``). When the
automated scraper lands in v0.3 it will replace this curated set with
verbatim article text and the rest of the schema is unchanged.

Run from the repo root:

    uv run python scripts/build_index.py
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl

SNAPSHOT_VERSION = date(2024, 7, 9)
BASE_URL = "https://www.legislation.gov.uk/eur/2013/575/article"

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "watchfire" / "data" / "index.parquet"


@dataclass(frozen=True)
class Entry:
    article: int | None
    title: str
    summary: str
    paragraph: int | None = None
    point: str | None = None
    subpoint: str | None = None
    instrument: str = "CRR"
    instrument_id: str | None = None
    url: str | None = None


ENTRIES: list[Entry] = [
    # Article 4 — Definitions. Only the specific definition paragraphs
    # referenced by rwa_calculator are indexed individually; the whole-
    # article entry is added by _expand_with_article_rows() below.
    Entry(4, "Definitions",
          "General definitions used throughout the regulation."),
    Entry(4, "Definition: credit institution",
          "Undertaking whose business is to take deposits or other repayable "
          "funds from the public and to grant credit for its own account.",
          paragraph=1, point="1"),
    Entry(4, "Definition: residential property",
          "Property classification used to set residential mortgage risk "
          "weights under the standardised and IRB approaches.",
          paragraph=1, point="75"),
    Entry(4, "Definition: commercial immovable property",
          "Property classification distinct from residential property used "
          "to set commercial real-estate risk weights.",
          paragraph=1, point="78"),
    Entry(4, "Definition: speculative immovable property financing",
          "Lending to acquire, develop, or build property with the primary "
          "intent of reselling at a profit.",
          paragraph=1, point="79"),

    Entry(92, "Own funds requirements",
          "Minimum Common Equity Tier 1, Tier 1, and total capital ratios "
          "expressed as a percentage of total risk exposure amount."),
    Entry(107, "Approaches to credit risk",
          "Institutions must apply either the Standardised Approach or, "
          "with PRA permission, the Internal Ratings Based Approach to "
          "calculate risk-weighted exposure amounts."),
    Entry(111, "Exposure value under SA",
          "Exposure value of an asset item is its accounting value remaining "
          "after specific credit risk adjustments. For off-balance-sheet "
          "items the nominal value is multiplied by the applicable CCF."),
    Entry(113, "Calculation of risk-weighted exposure amounts under SA",
          "Each exposure is assigned to a CRR exposure class and a risk "
          "weight from the relevant table is applied."),
    Entry(114, "Exposures to central governments or central banks",
          "Risk weights for sovereign exposures; preferential treatment "
          "available for certain currency and rating combinations."),
    Entry(142, "Definitions (IRB approach)",
          "Definitions specific to the IRB approach including obligor "
          "grades, exposure classes, and large financial sector entity."),
    Entry(143, "Permission to use the IRB approach",
          "Conditions and competent-authority permissions required before "
          "an institution may apply the IRB approach."),
    Entry(153, "Risk-weighted exposure amounts for corporates, "
                "institutions, central governments and central banks",
          "Risk-weight formula for non-retail IRB exposures using PD, LGD, "
          "and maturity adjustment."),
    Entry(154, "Risk-weighted exposure amounts for retail exposures",
          "Risk-weight formula for retail IRB exposures; differentiated "
          "treatment for residential mortgages and qualifying revolving "
          "retail exposures."),
    Entry(166, "Exposure value under IRB",
          "Exposure value of an on- or off-balance-sheet item under the "
          "IRB approach, including treatment of conversion factors."),

    # PRA Supervisory and Policy Statements cited by rwa_calculator.
    Entry(None, "Model risk management principles for banks",
          "PRA expectations on the governance, development, and validation "
          "of models used by banks.",
          instrument="SS", instrument_id="SS1/23",
          url="https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss"),
    Entry(None, "Implementation of the Basel 3.1 standards — final rules",
          "Near-final PRA policy implementing Basel 3.1 in the UK.",
          instrument="PS", instrument_id="PS9/24",
          url="https://www.bankofengland.co.uk/prudential-regulation/publication/2024/september/implementation-of-the-basel-3-1-standards-near-final-part-2"),
    Entry(None, "Credit Risk part of the PRA Rulebook",
          "Quantitative and qualitative requirements on credit risk weighted "
          "exposure amounts.",
          instrument="PRA_RULEBOOK", instrument_id="Credit Risk",
          url="https://www.prarulebook.co.uk/rulebook/Content/Part/216147"),
]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row(entry: Entry) -> dict:
    if entry.url is not None:
        url = entry.url
    elif entry.instrument == "CRR" and entry.article is not None:
        url = f"{BASE_URL}/{entry.article}"
    else:
        url = ""
    return {
        "instrument": entry.instrument,
        "instrument_id": entry.instrument_id,
        "article": entry.article,
        "paragraph": entry.paragraph,
        "point": entry.point,
        "subpoint": entry.subpoint,
        "title": entry.title,
        "version": SNAPSHOT_VERSION,
        "content_text": entry.summary,
        "content_hash": _hash(entry.summary),
        "url": url,
    }


def build() -> pl.DataFrame:
    rows = [_row(e) for e in ENTRIES]
    return pl.DataFrame(rows, schema={
        "instrument": pl.Utf8,
        "instrument_id": pl.Utf8,
        "article": pl.Int32,
        "paragraph": pl.Int32,
        "point": pl.Utf8,
        "subpoint": pl.Utf8,
        "title": pl.Utf8,
        "version": pl.Date,
        "content_text": pl.Utf8,
        "content_hash": pl.Utf8,
        "url": pl.Utf8,
    })


def main() -> None:
    df = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT)
    print(f"wrote {OUTPUT} ({df.height} rows)")


if __name__ == "__main__":
    main()
