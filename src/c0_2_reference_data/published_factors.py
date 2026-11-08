"""The factor set the product ships with: EPA GHG Emission Factors Hub, January 2025.

Source table: "Table 10 Scope 3 Category 6: Business Travel and Category 7: Employee Commuting"
(Emission Factors for Greenhouse Gas Inventories, Last Modified 15 January 2025,
https://www.epa.gov/system/files/documents/2025-01/ghg-emission-factors-hub-2025.pdf).

    Passenger Car   0.297 kg CO2, 0.0059 g CH4, 0.0053 g N2O per vehicle-mile
    Bus             0.066 kg CO2, 0.0046 g CH4, 0.0019 g N2O per passenger-mile
    GWP (Table 11, IPCC AR5, 100 years): CH4 28, N2O 265

    car: (0.297 x 1000 + 0.0059 x 28 + 0.0053 x 265) / 1.609344 = 185.523 g CO2e per vehicle-km
    bus: (0.066 x 1000 + 0.0046 x 28 + 0.0019 x 265) / 1.609344 =  41.403 g CO2e per passenger-km

Status: transcribed from the published table and **reviewed by the Method Reviewer, Yinping Yin, on
2026-11-09** (docs/factor-review.md). Tailpipe (tank-to-wheel) emissions only, no upstream emissions. Walk and
bike are 0 because no fuel is burned: that is an assumption, not an EPA table value. EPA publishes no
factor for an electric scooter or for a carpool (the carpool is the drive factor shared by the people in
the car, see ADR 0008), so those modes keep the placeholder of the Data Adapter (C.3).
"""

from functools import lru_cache

from src.c0_2_reference_data.load_emission_factors import build_factor_set
from src.interfaces import FactorSet

KM_PER_MILE = 1.609344
GWP_CH4, GWP_N2O = 28, 265  # EPA Table 11 (IPCC AR5)


def g_co2e_per_km(kg_co2: float, g_ch4: float, g_n2o: float) -> float:
    """Grams CO2e per kilometre from EPA's per-mile CO2 (kg), CH4 (g) and N2O (g), kept to 0.001 g/km."""
    return round((kg_co2 * 1000 + g_ch4 * GWP_CH4 + g_n2o * GWP_N2O) / KM_PER_MILE, 3)


EPA_2025 = {
    "version": "epa-hub-2025-01",
    "source": "EPA GHG Emission Factors Hub, 15 Jan 2025, Table 10 (passenger car per vehicle-mile, bus per passenger-mile)",
    "units": "g CO2e per km (per vehicle for drive, per passenger for bus)",
    "geography": "US",
    "methodology": "Tailpipe CO2 + CH4 x 28 + N2O x 265 (IPCC AR5 GWP), miles converted to km; walk and bike set to 0 (no fuel burned)",
    "factors": {
        "drive": g_co2e_per_km(0.297, 0.0059, 0.0053),
        "bus": g_co2e_per_km(0.066, 0.0046, 0.0019),
        "walk": 0.0,
        "bike": 0.0,
    },
}


@lru_cache(maxsize=1)
def default_factor_set() -> FactorSet:
    return build_factor_set(EPA_2025)
