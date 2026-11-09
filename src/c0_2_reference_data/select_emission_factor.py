"""Function F.2.2.2 Select Emission Factor - performed by C.0.2.2 Factor Lookup Module.

ICOM: input IO.12 Validated Commute Entry; control IO.23 Versioned Factor Set (keyword-only);
output IO.14 Emission Factor Record. Requirement 5.4.2: select the applicable factor for the entry
from the versioned factor set and return it with its provenance (source, units, geography, version).
Without a factor set the shipped EPA 2025 set is used (published_factors.py); a mode that set does not
cover (scooter, carpool) falls back to the labelled placeholder of the Data Adapter (C.3).
"""

from src.c0_2_reference_data.published_factors import default_factor_set
from src.c3_data_adapter.data_adapter import retrieve_factor
from src.interfaces import CommuteRequest, EmissionFactor, FactorSet


def select_emission_factor(validated_entry: CommuteRequest, *, factor_set: FactorSet | None = None) -> EmissionFactor:
    explicit = factor_set is not None
    factor_set = factor_set if explicit else default_factor_set()
    table = dict(factor_set.factors)
    if validated_entry.mode not in table:
        if not explicit:
            return retrieve_factor(validated_entry)  # labelled placeholder
        raise LookupError(f"factor set {factor_set.version} has no factor for mode {validated_entry.mode}")
    return EmissionFactor(
        mode=validated_entry.mode,
        g_co2e_per_km=table[validated_entry.mode],
        units=factor_set.units,
        geography=factor_set.geography,
        source=factor_set.source,
        version=factor_set.version,
    )
