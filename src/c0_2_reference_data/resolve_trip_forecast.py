"""Function F.2.2.4 Resolve Trip Forecast - performed by C.0.2.4 Forecast Resolver Module.

ICOM: input IO.5 Weather Forecast (one forecast or an hourly series from Open-Meteo, or None);
control IO.24 Forecast Query Context (keyword-only); output IO.15 Trip Weather Forecast.
Requirement 5.4.4: resolve the response to the forecast for the trip time, with its forecast
timestamp, or flag the forecast unavailable when no response arrives within the timeout.
"""

from src.interfaces import ForecastQueryContext, TripForecast, WeatherForecast


def _unavailable(note: str) -> TripForecast:
    return TripForecast(forecast=None, forecast_timestamp="", available=False, note=note)


def resolve_trip_forecast(response, *, context: ForecastQueryContext, response_seconds: float | None = None) -> TripForecast:
    if response is None:
        return _unavailable("No forecast response; forecast unavailable.")
    if response_seconds is not None and response_seconds > context.timeout_s:
        return _unavailable(f"Forecast arrived after {context.timeout_s:g} s; forecast unavailable.")
    candidates = (response,) if isinstance(response, WeatherForecast) else tuple(response)
    if len(candidates) > 1 and context.trip_time:
        hour = context.trip_time[:13]  # YYYY-MM-DDTHH
        candidates = tuple(c for c in candidates if c.forecast_timestamp[:13] == hour)
    if not candidates:
        return _unavailable("No forecast for the trip hour; forecast unavailable.")
    chosen = candidates[0]
    return TripForecast(forecast=chosen, forecast_timestamp=chosen.forecast_timestamp, available=True, note="Forecast for the trip time.")
