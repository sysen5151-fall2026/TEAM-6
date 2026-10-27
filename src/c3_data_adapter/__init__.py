"""C.3 Data Adapter - factor store, trip store, weather and route access (factors, trips, trip weather are STUB)."""
from .data_adapter import request_weather, retrieve_factor, store_trip, update_trends
from .route_adapter import geocode, get_route_options, sample_places
from .weather_adapter import current_weather

__all__ = [
    "current_weather",
    "geocode",
    "get_route_options",
    "request_weather",
    "retrieve_factor",
    "sample_places",
    "store_trip",
    "update_trends",
]
