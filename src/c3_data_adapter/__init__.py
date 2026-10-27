"""C.3 Data Adapter - factor store, trip store, weather and route access (factors, weather, trips are STUB)."""
from .data_adapter import request_weather, retrieve_factor, store_trip, update_trends
from .route_adapter import geocode, get_route_options, sample_places

__all__ = [
    "geocode",
    "get_route_options",
    "request_weather",
    "retrieve_factor",
    "sample_places",
    "store_trip",
    "update_trends",
]
