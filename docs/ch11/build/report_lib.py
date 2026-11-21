"""Shared helpers of the Chapter 11 and 12 report build: data, formatting, figure and table numbering."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "ch8-ch9", "build"))
sys.path.insert(0, os.path.join(ROOT, "docs", "ch11", "sim"))
import docx_helpers as H  # noqa: E402
from docx.shared import Pt, RGBColor  # noqa: E402

_orig = H._runs
H._runs = lambda p, text, *a, **k: _orig(p, text.replace("`", ""), *a, **k)   # no backticks in the Word text

D11 = os.path.join(ROOT, "docs", "ch11", "data")
DIA = os.path.join(ROOT, "docs", "ch11", "diagrams")
SHOT = os.path.join(ROOT, "docs", "ch11", "innoslate")
A = json.load(open(os.path.join(D11, "analysis.json"), encoding="utf-8"))
SEL = A["selected"]
TESTS = json.load(open(os.path.join(D11, "test_run.json"), encoding="utf-8"))
NAMES = {"A": "Sequential dispatch", "B": "Concurrent dispatch", "C": "Concurrent dispatch with keep-alive",
         "D": "Concurrent dispatch with name cache", "E": "Queued asynchronous handling"}
SHORT = {"A": "Sequential", "B": "Concurrent", "C": "Keep-alive", "D": "Name cache", "E": "Queued"}

NUM = {"fig": {}, "tab": {}}
_counter = {"fig": 0, "tab": 0}


def reset_counters():
    _counter["fig"] = _counter["tab"] = 0


def F(key):
    return f"Figure {NUM['fig'].get(key, '?')}"


def T(key):
    return f"Table {NUM['tab'].get(key, '?')}"


def cap_fig(d, key, text):
    _counter["fig"] += 1
    NUM["fig"][key] = _counter["fig"]
    H.caption(d, f"Figure {_counter['fig']}. {text}")


def cap_tab(d, key, text):
    _counter["tab"] += 1
    NUM["tab"][key] = _counter["tab"]
    p = H.caption(d, f"Table {_counter['tab']}. {text}")
    p.paragraph_format.keep_with_next = True


def fig(d, key, filename, caption, width=6.4, shot=None):
    """A drawn figure, or the Innoslate screenshot of the same name when the team has added one."""
    path = os.path.join(SHOT, shot) if shot and os.path.exists(os.path.join(SHOT, shot)) else os.path.join(DIA, filename)
    H.picture(d, path, width)
    cap_fig(d, key, caption)


def f1(x):
    return f"{x:.1f}"


def f2(x):
    return f"{x:.2f}"


def f3(x):
    return f"{x:.3f}"


def money(x):
    return f"${x:,.0f}"


def pct(x):
    return f"{x:.0f}%"


def sec(x):
    return f"{x:.2f} s" if x >= 0.1 else f"{x * 1000:.0f} ms" if x >= 0.001 else f"{x * 1e6:.0f} microseconds"
