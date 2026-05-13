"""Standardised approach — a small slice of what rwa_calculator does."""

from watchfire import cites


@cites("CRR Art. 113")
def calculate_sa_rwa(exposures):
    return exposures


@cites("CRR Art. 114")
def sovereign_rw(country):
    return 0.0


@cites("CRR Art. 111")
def exposure_value_sa(gross_exposure, ccf):
    return gross_exposure * ccf
