from src.c1_web_front_end import display_commute_result, present_entry_fields, submit_commute_request
from src.interfaces import CommuteRequest
from src.model_trace import realizes


@realizes("UC.1.1")
def open_commute_entry():
    """UC.1.1 Open Commute Entry - performed by X.1 Commuter (simulated)."""
    return present_entry_fields()  # UC.1.2 performed by C.1


@realizes("UC.1.3")
def enter_trip_details(form, mode, distance_km, date, coarse_area, not_feasible_modes=()):
    """UC.1.3 Enter Trip Details - fills the fields offered in the Entry Form."""
    assert set(form.fields) >= {"mode", "distance_km", "date", "coarse_area"}
    return CommuteRequest(
        mode=mode,
        distance_km=distance_km,
        date=date,
        coarse_area=coarse_area,
        not_feasible_modes=tuple(not_feasible_modes),
    )


@realizes("UC.1.12")
def review_result(rendered: str) -> str:
    """UC.1.12 Review Result - the Commuter reads the result; the choice stays theirs."""
    return rendered


@realizes("UC.1.4")
def run_uc1(mode="drive", distance_km=2.5, date="2026-10-07", coarse_area="Ithaca, NY",
            not_feasible_modes=()):
    """Run the primary use case UC.1 once, end to end, and return what the Commuter sees.

    Default scenario = BMA 7.2 example: a short car trip on a dry day.
    """
    form = open_commute_entry()  # UC.1.1 -> UC.1.2
    request = enter_trip_details(  # UC.1.3
        form, mode, distance_km, date, coarse_area, not_feasible_modes
    )
    result = submit_commute_request(request)  # UC.1.4 -> UC.1.5 ... UC.1.10 (C.2, C.3, X.3, C.4)
    return review_result(display_commute_result(result))  # UC.1.11 -> UC.1.12
