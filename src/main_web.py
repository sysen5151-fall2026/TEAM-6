"""Start the web entry:  python -m src.main_web   (then open http://127.0.0.1:5000)"""

from src.c1_web_front_end.web_app import create_app
from src.c3_data_adapter import open_store
from src.key_loader import load_ors_key


def transit_status(store=None) -> str:
    """One line on whether the TCAT bus schedule is available, shown when the server starts."""
    store = store or open_store()
    if store is None:
        return "TCAT bus schedule: not built, so the bus card will say so (run: python -m src.update_transit)."
    info = store.feed_info()
    return f"TCAT bus schedule: feed {info['version']}, service {info['start_date']} to {info['end_date']}."


if __name__ == "__main__":
    source = load_ors_key()
    print(f"OpenRouteService key: found in the {source}." if source else
          "OpenRouteService key: not found, so only sample places and estimates are available "
          "(see README: Run the web entry).")
    print(transit_status())
    create_app().run(host="127.0.0.1", port=5000)
