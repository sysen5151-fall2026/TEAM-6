import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime

from src.c2_application_service.bus_planner import find_bus, local_now
from src.c2_application_service.comparison import bus_comparison, compare_modes
from src.c2_application_service.recommendation import recommend_mode
from src.c0_2_reference_data import WEATHER_TIMEOUT_S, resolve_trip_forecast
from src.c3_data_adapter import current_weather, geocode
from src.interfaces import CommutePlan, ForecastQueryContext
from src.model_trace import realizes

VEHICLES = ("bike", "scooter")  # the student has neither unless they say so

# ADR 0012. "concurrent" (selected, Chapter 11 alternative C) starts the weather call as soon as the start place is known,
# so it runs beside the route calls; "sequential" (alternative A, the Chapter 10 build) asks for the weather after the
# routes and is kept so the two can be measured on the same code (docs/ch11/spike/measure_dispatch.py).
DISPATCH = "concurrent"
# Guardrail for risk TR.16: a forecast that has not arrived this long after its call started is treated as unavailable
# (requirement 5.4.4) and the recommendation says the weather rules were not applied. The call itself is left to finish
# on its pool thread so that its connection goes back to the pool warm.
WEATHER_DEADLINE_S = WEATHER_TIMEOUT_S
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="wx")
# Monitoring indicators of risk TR.16 (docs/risks.md): how often the guardrail had to drop the forecast.
STATS = {"plans": 0, "weather_ok": 0, "weather_missed_deadline": 0, "weather_failed": 0}


def dispatch_stats() -> dict:
    return dict(STATS)


def _await_weather(future, started: float):
    """The forecast, or None when the call failed or missed its deadline."""
    remaining = max(0.0, WEATHER_DEADLINE_S - (time.monotonic() - started))
    try:
        forecast = future.result(timeout=remaining)
    except FutureTimeout:
        STATS["weather_missed_deadline"] += 1
        return None
    except (OSError, ValueError, KeyError, TypeError):
        STATS["weather_failed"] += 1
        return None
    STATS["weather_ok" if forecast is not None else "weather_failed"] += 1
    return forecast


@realizes("UC.3.5")
def plan_commute(origin_text: str, destination_text: str, have=(), when: datetime = None, bus_route: str = "") -> CommutePlan:
    """Compare the ways the Commuter can use, apply weather and time checks, and recommend one.

    Drive and walk are always compared; a bike or scooter only when listed in `have`; the
    bus when the TCAT schedule has a direct ride leaving at or after `when` (default: now,
    Ithaca time). When several routes link the places, `bus_route` picks which one the bus
    row is built from (default: the one that arrives first). Weather is the current condition at the start place; if it cannot be
    fetched the recommendation still works and says the weather rules were not applied.
    """
    when = when or local_now()
    STATS["plans"] += 1
    weather_future, weather_started = None, 0.0
    if DISPATCH == "concurrent":
        early = geocode(origin_text)  # answered from the sample list or the place cache; compare_modes repeats it for free
        if early is not None:
            weather_started = time.monotonic()
            weather_future = _pool.submit(current_weather, early)
    comparisons, origin, dest, errors = compare_modes(origin_text, destination_text)
    if errors:
        return CommutePlan(origin, dest, (), None, tuple(errors))
    usable = tuple(c for c in comparisons if c.mode not in VEHICLES or c.mode in have)
    bus = find_bus(origin, dest, when)
    rows, choice = (), ""
    if bus.options:
        drive = next(c for c in comparisons if c.mode == "drive")
        rows = tuple(bus_comparison(option, drive) for option in bus.options)
        chosen = next((i for i, o in enumerate(bus.options) if o.route_id == bus_route), 0)  # else the best
        choice = bus.options[chosen].route_id
        usable += (rows[chosen],)
    context = ForecastQueryContext(origin.label, when.isoformat(timespec="minutes"), WEATHER_TIMEOUT_S)  # IO.24
    if weather_future is None:  # sequential dispatch, or the start place was not found early
        weather_started = time.monotonic()
        weather_future = _pool.submit(current_weather, origin)
    weather = resolve_trip_forecast(_await_weather(weather_future, weather_started), context=context).forecast  # F.2.2.4
    return CommutePlan(origin, dest, usable, recommend_mode(usable, weather), (), bus, rows, choice)
