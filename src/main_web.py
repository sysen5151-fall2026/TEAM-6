"""Start the web entry:  python -m src.main_web   (then open http://127.0.0.1:5000)"""

from src.c1_web_front_end.web_app import create_app

if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
