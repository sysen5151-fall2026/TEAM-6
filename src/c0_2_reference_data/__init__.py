"""C.0.2 Reference Data Subsystem - one module per second-level function of F.2.2.

    F.2.2.1 Load Emission Factors     -> load_emission_factors.py    (C.0.2.1 Factor Import Module)
    F.2.2.2 Select Emission Factor    -> select_emission_factor.py   (C.0.2.2 Factor Lookup Module)
    F.2.2.3 Request Weather Forecast  -> request_weather_forecast.py (C.0.2.3 Weather Client Module)
    F.2.2.4 Resolve Trip Forecast     -> resolve_trip_forecast.py    (C.0.2.4 Forecast Resolver Module)

Signatures follow the ICOMs of the second-level IDEF0 (model 11.3, Table 4 of the Chapter 8-9 report):
inputs are parameters, controls are keyword-only, outputs are return values. The contract is
contracts/api-v1.yaml; the requirements are 5.4.1 to 5.4.4 of the component specification.
"""
from .load_emission_factors import FactorSetRejected, load_emission_factors, reset_factor_store, stored_versions
from .request_weather_forecast import WEATHER_TIMEOUT_S, request_weather_forecast
from .resolve_trip_forecast import resolve_trip_forecast
from .select_emission_factor import select_emission_factor

__all__ = [
    "FactorSetRejected",
    "WEATHER_TIMEOUT_S",
    "load_emission_factors",
    "request_weather_forecast",
    "reset_factor_store",
    "resolve_trip_forecast",
    "select_emission_factor",
    "stored_versions",
]
