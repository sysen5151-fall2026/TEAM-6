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
    temperature_c: float | None = None  # only set by the live weather adapter
    wind_kmh: float | None = None


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


@dataclass(frozen=True)
class Place:  # a geocoded origin or destination
    label: str
    lon: float
    lat: float
    source: str  # who resolved it, so the page can disclose it


@dataclass(frozen=True)
class RouteOption:  # one mode's route between two places
    mode: str  # "drive" | "walk" | "bike"
    distance_km: float
    duration_min: float
    source: str  # "OpenRouteService" or an estimate label
    path: tuple = ()  # ((lat, lon), ...) along the route, for drawing on a map


@dataclass(frozen=True)
class ModeComparison:  # RouteOption plus emissions, for the compare page
    mode: str
    distance_km: float
    duration_min: float
    co2e_g: float
    difference_g: float  # estimated difference from the always-drive baseline
    source: str


@dataclass(frozen=True)
class Recommendation:  # result of the feasibility filter and ranking
    mode: str  # "" when nothing could be recommended
    reason: str  # built only from values already computed
    excluded: tuple  # ((mode, reason), ...) for every mode ruled out
    weather_note: str  # what weather was (or was not) applied


@dataclass(frozen=True)
class BusStop:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class BusItinerary:  # one direct bus ride from the schedule, with the walks at both ends
    route_id: str
    route_name: str  # the number riders see, e.g. "30"
    color: str  # route colour, six hex digits without "#"
    text_color: str
    headsign: str  # where the bus says it is going
    direction_id: int  # -1 when the feed does not say
    board: BusStop
    alight: BusStop
    leave_time: str  # when to set off from the start, "HH:MM"
    depart_time: str  # bus leaves the boarding stop
    arrive_time: str  # bus reaches the stop where you get off
    arrive_destination: str
    walk_to_m: int
    walk_from_m: int
    walk_to_min: int
    walk_from_min: int
    wait_min: int
    ride_min: int
    ride_km: float  # along the route, from the feed's own distances
    total_min: int  # from leaving to arriving, waiting included
    service_date: str  # YYYY-MM-DD the schedule applies to
    next_departures: tuple  # later "HH:MM" departures of the same route from the same stop
    path: tuple  # ((lat, lon), ...) of the ride, stop to stop
    feed_version: str


@dataclass(frozen=True)
class BusResult:
    itinerary: "BusItinerary | None"  # a bus on the requested day at or after the requested time
    status: str  # "ok", "not_installed", "outside_feed", "no_stop_near_start", "no_stop_near_destination",
    #              "no_direct_route", "no_service_that_day", "no_more_that_day"
    note: str  # plain-language reason shown on the bus card
    later: "BusItinerary | None" = None  # the next bus on a later day when there is none on the requested day
    options: tuple = ()  # the best ride of each route that links the places, earliest arrival first


@dataclass(frozen=True)
class CommutePlan:  # everything the compare page shows
    origin: "Place | None"
    destination: "Place | None"
    comparisons: tuple
    recommendation: "Recommendation | None"
    errors: tuple
    bus: "BusResult | None" = None
    bus_rows: tuple = ()  # a ModeComparison for each bus option, in the same order as bus.options
    bus_choice: str = ""  # route id of the option the bus row of `comparisons` is built from


@dataclass(frozen=True)
class ConfirmedTrip:  # a trip the Commuter says they actually took
    date: str
    mode: str
    origin: str
    destination: str
    distance_km: float
    co2e_g: float
    difference_g: float  # estimated difference from the always-drive baseline
    recommended_mode: str  # what the page recommended at the time ("" if none)
    occupants: int = 1  # people sharing the car (the Commuter included); more than 1 means a carpool
    route: str = ""  # the bus route number when the way was the bus


@dataclass(frozen=True)
class BadgeStatus:
    id: str
    name: str
    condition: str  # shown to the Commuter, so the rule is visible
    icon: str
    progress: int
    target: int
    unit: str
    earned: bool


@dataclass(frozen=True)
class CampusGoal:
    total_g: float  # everyone's estimated difference, seed plus this Commuter
    goal_g: float  # one tree
    trees_reached: int
    into_next_g: float  # progress toward the next tree
    trips: int
    students: int
    sample_note: str  # discloses which part is sample data
