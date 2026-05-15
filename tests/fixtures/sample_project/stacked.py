"""Stacked citations — the same rule lives in CRR and the corresponding PRA PS."""

from watchfire import cites


@cites("CRR Art. 163")  # outer / primary
@cites("PS1/26, paragraph 163")  # inner / secondary
def apply_pd_floor():
    """Equity exposure PD floor — same rule in CRR and PRA PS1/26."""
    return 0.0
