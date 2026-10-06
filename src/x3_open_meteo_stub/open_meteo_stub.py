from src.interfaces import WeatherForecast, WeatherQuery
from src.model_trace import realizes


@realizes("UC.1.7")
def return_weather_forecast(query: WeatherQuery) -> WeatherForecast:
    """UC.1.7 Return Weather Forecast - performed by X.3 Open-Meteo.

    STUB: returns a fixed dry forecast. The real X.3 is an HTTPS API
    (docs/context.md, interface X.3); no real source access at this stage.
    """
    return WeatherForecast(precipitation_mm=0.0, forecast_timestamp="2026-10-07T08:00:00Z")
