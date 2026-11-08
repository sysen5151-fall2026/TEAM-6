"""Function F.2.2.3 Request Weather Forecast - performed by C.0.2.3 Weather Client Module.

ICOM: input IO.12 Validated Commute Entry; outputs IO.4 Weather Query (to Open-Meteo) and
IO.24 Forecast Query Context (to F.2.2.4). Requirement 5.4.3, with system-wide requirement 5.5.6:
the query carries only the coarse area and the trip time, nothing finer. The timeout is fixed
configuration (1.0 second, requirement 5.4.4), not a parameter of the caller (docs/adr/0010).
"""

from src.interfaces import CommuteRequest, ForecastQueryContext, WeatherQuery

WEATHER_TIMEOUT_S = 1.0


def request_weather_forecast(validated_entry: CommuteRequest) -> tuple:
    query = WeatherQuery(coarse_area=validated_entry.coarse_area, date=validated_entry.date)
    context = ForecastQueryContext(
        coarse_area=validated_entry.coarse_area,
        trip_time=validated_entry.date,
        timeout_s=WEATHER_TIMEOUT_S,
    )
    return query, context
