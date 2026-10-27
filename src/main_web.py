"""Start the web entry:  python -m src.main_web   (then open http://127.0.0.1:5000)"""

from src.c1_web_front_end.web_app import create_app
from src.key_loader import load_ors_key

if __name__ == "__main__":
    source = load_ors_key()
    print(f"OpenRouteService key: found in the {source}." if source else
          "OpenRouteService key: not found, so only sample places and estimates are available "
          "(see README: Run the web entry).")
    create_app().run(host="127.0.0.1", port=5000)
