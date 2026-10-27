from src.c3_data_adapter import geocode, get_route_options, retrieve_factor
from src.interfaces import CommuteRequest, ModeComparison, Place, RouteOption
from src.model_trace import realizes

MIN_DISTANCE_KM = 0.05  # origin and destination closer than this are treated as the same place


def _factor_g_per_km(mode: str) -> float:
    request = CommuteRequest(mode=mode, distance_km=1.0, date="", coarse_area="")
    return retrieve_factor(request).g_co2e_per_km


@realizes("UC.3.5")
def compare_modes(origin_text: str, destination_text: str, transit_minutes=None):
    """Compare drive, walk and bike between two places, and bus when the Commuter enters a time.

    Each mode keeps its own routed distance, so the baseline is the drive route's
    distance x the drive factor (not the walking distance). Returns
    (comparisons, origin, destination, errors); comparisons is empty when errors is not.
    """
    origin, dest = geocode(origin_text), geocode(destination_text)
    errors = []
    if origin is None:
        errors.append(f"Could not find a place for the start: {origin_text.strip()!r}.")
    if dest is None:
        errors.append(f"Could not find a place for the destination: {destination_text.strip()!r}.")
    if errors:
        return (), origin, dest, errors

    options = get_route_options(origin, dest)
    if min(o.distance_km for o in options) < MIN_DISTANCE_KM:
        return (), origin, dest, ["Start and destination are the same place."]

    if transit_minutes is not None:  # entered by the Commuter; no transit routing exists
        drive_km_for_bus = next(o.distance_km for o in options if o.mode == "drive")
        options = options + (
            RouteOption(
                mode="bus",
                distance_km=drive_km_for_bus,  # ASSUMPTION: the bus follows the drive route
                duration_min=float(transit_minutes),
                source="entered by you; distance assumed equal to the drive route",
            ),
        )

    drive_km = next(o.distance_km for o in options if o.mode == "drive")
    baseline_g = round(drive_km * _factor_g_per_km("drive"))
    comparisons = []
    for option in options:
        co2e_g = round(option.distance_km * _factor_g_per_km(option.mode))
        comparisons.append(
            ModeComparison(
                mode=option.mode,
                distance_km=option.distance_km,
                duration_min=option.duration_min,
                co2e_g=co2e_g,
                difference_g=baseline_g - co2e_g,
                source=option.source,
            )
        )
    return tuple(comparisons), origin, dest, []


def preview_routes(origin: Place, dest: Place):
    """The routes between two chosen points, for drawing before the Commuter compares.

    Returns (options, error); options is empty when error is not.
    """
    options = get_route_options(origin, dest)
    if min(o.distance_km for o in options) < MIN_DISTANCE_KM:
        return (), "Start and destination are the same place."
    return options, ""
