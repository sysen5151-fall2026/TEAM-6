"""Return types exchanged between participants.

Names follow the input/output entities of the Innoslate Action Diagram
(Entry Form, Entry Request, Commute Request, Weather Query, Weather Forecast,
Commute Impact Result). Source: BMA Section 7.5; docs/context.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryForm:  # I/O "Entry Form" (UC.1.2 -> UC.1.3)
    fields: tuple


@dataclass(frozen=True)
class CommuteRequest:  # I/O "Entry Request" / "Commute Request" (UC.1.3/1.4 -> UC.1.5)
    mode: str
    distance_km: float
    date: str
    coarse_area: str
    occupancy: int = 1
    not_feasible_modes: tuple = ()


@dataclass(frozen=True)
class WeatherQuery:  # I/O "Weather Query" (UC.1.6 -> UC.1.7)
    coarse_area: str
    date: str


@dataclass(frozen=True)
class WeatherForecast:  # I/O "Weather Forecast" (UC.1.7 -> UC.1.8)
    precipitation_mm: float
    forecast_timestamp: str


@dataclass(frozen=True)
class EmissionFactor:  # reviewed-factor record (SRD 2.4.1: source, units, geography, version)
    mode: str
    g_co2e_per_km: float
    units: str
    geography: str
    source: str
    version: str


@dataclass(frozen=True)
class TripRecord:
    request: CommuteRequest
    co2e_g: float


@dataclass(frozen=True)
class TrendSummary:
    weekly_total_g: float
    monthly_total_g: float
    cumulative_difference_g: float


@dataclass(frozen=True)
class CommuteImpactResult:  # I/O "Commute Impact Result" (UC.1.10/1.11 -> UC.1.12)
    estimated_co2e_g: float
    baseline_co2e_g: float
    estimated_difference_g: float  # labelled "estimated" per SRD 2.4.4
    difference_label: str
    factor_source: str  # SRD 2.1.3
    factor_version: str
    distance_convention: str
    trend: TrendSummary
    alternative_mode: str  # "" when no eligible lower-emission option
    alternative_reason: str
    explanation: str
