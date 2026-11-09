"""Function F.2.2.1 Load Emission Factors - performed by C.0.2.1 Factor Import Module.

ICOM: control IO.6 Reviewed Emission Factors (keyword-only); output IO.23 Versioned Factor Set.
Requirement 5.4.1: load each reviewed factor set into a versioned set and reject any set that lacks
source, units, geography, methodology or version. The set the product ships with is
`published_factors.py` (EPA 2025), loaded through `build_factor_set` below.
"""

from src.interfaces import FactorSet

REQUIRED_ATTRIBUTES = ("source", "units", "geography", "methodology", "version")

_STORE = {}  # version -> FactorSet; every accepted set is kept as its own version


class FactorSetRejected(ValueError):
    """The factor set lacks a required attribute, has no factors, or repeats a stored version."""


def build_factor_set(reviewed_factors: dict) -> FactorSet:
    """Validate a factor set and return it (nothing is stored)."""
    missing = [a for a in REQUIRED_ATTRIBUTES if not str(reviewed_factors.get(a, "")).strip()]
    if missing:
        raise FactorSetRejected("factor set rejected, missing: " + ", ".join(missing))
    factors = reviewed_factors.get("factors") or {}
    if not factors:
        raise FactorSetRejected("factor set rejected, it contains no factors")
    return FactorSet(
        version=str(reviewed_factors["version"]).strip(),
        source=str(reviewed_factors["source"]).strip(),
        units=str(reviewed_factors["units"]).strip(),
        geography=str(reviewed_factors["geography"]).strip(),
        methodology=str(reviewed_factors["methodology"]).strip(),
        factors=tuple((str(mode), float(value)) for mode, value in factors.items()),
    )


def load_emission_factors(*, reviewed_factors: dict) -> FactorSet:
    accepted = build_factor_set(reviewed_factors)
    if accepted.version in _STORE:
        raise FactorSetRejected(f"factor set rejected, version {accepted.version} is already stored")
    _STORE[accepted.version] = accepted
    return accepted


def stored_versions() -> tuple:
    return tuple(_STORE)


def reset_factor_store() -> None:
    """Test helper only; not part of the modeled behavior."""
    _STORE.clear()
