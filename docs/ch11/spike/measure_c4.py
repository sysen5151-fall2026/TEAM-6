"""Chapter 11 prototype spike: the same 40 explanation cases through each C.4 alternative.

    python docs/ch11/spike/measure_c4.py --label gpu      (Ollama must be running with qwen2.5:1.5b pulled)

Alternative A: deterministic template (the stub of Chapters 2-10).
Alternative B: locally hosted model (Ollama, qwen2.5:1.5b) asked to rephrase the template; RAW output is checked
               with the C.4 guardrail so the rate of unsupported text is measured before any fallback.
Alternative C: hosted API. Not run (no key): only the network floor to the API host is measured, with no trip data sent.
Writes docs/ch11/data/spike_<label>.json and spike_<label>_cases.csv.
"""
import argparse
import csv
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from src.interfaces import ModeComparison  # noqa: E402
from src.c4_explanation_model.explainer import MODE_ALTERNATIVES, recommendation_template  # noqa: E402
from src.c4_explanation_model.guardrail import Facts, check_explanation, direction_rules  # noqa: E402
from src.c4_explanation_model.model_client import OllamaClient, ModelUnavailable, build_prompt  # noqa: E402

DATA = os.path.join(ROOT, "docs", "ch11", "data")
FACTOR = {"drive": 185.523, "bus": 41.403, "walk": 0.0, "bike": 0.0}
SPEED = {"drive": 30.0, "bus": 20.0, "bike": 15.0, "walk": 5.0}


def syllables(word):
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups) - (1 if word.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def fk_grade(text):
    """Flesch-Kincaid grade level (heuristic syllable count); ';' counts as a sentence break."""
    sentences = max(1, len(re.findall(r"[.!?;]+(?:\s|$)", text)))
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return 0.0
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / sentences + 11.8 * syl / len(words) - 15.59


def make_cases(n=40, seed=5151):
    rnd = random.Random(seed)
    cases = []
    while len(cases) < n:
        km = round(rnd.uniform(0.6, 9.0), 1)
        raw = {m: (round(km / SPEED[m] * 60 + (4 if m == "bus" else 0)), round(km * FACTOR[m])) for m in FACTOR}
        base = raw["drive"][1]
        rows = {m: ModeComparison(m, km, d, c, base - c, "estimate") for m, (d, c) in raw.items()}
        fastest = min(rows.values(), key=lambda c: (c.duration_min, c.mode))
        met = rnd.random() > 0.2
        if met:
            pool = [m for m in rows if m != "drive"] if rnd.random() > 0.1 else list(rows)
            chosen = rows[rnd.choice(pool)]
        else:
            chosen = rows[rnd.choice(list(rows))]
        cases.append((chosen, fastest, met))
    return cases


def facts_for(chosen, fastest, template):
    return Facts(
        allowed_numbers=(chosen.duration_min, chosen.co2e_g, chosen.difference_g, fastest.duration_min,
                         chosen.duration_min - fastest.duration_min),
        required_numbers=(chosen.duration_min, chosen.co2e_g),
        allowed_modes=("drive", chosen.mode, fastest.mode), allowed_text=template,
        required_phrases=("estimate", MODE_ALTERNATIVES.get(chosen.mode, chosen.mode)),
        forbidden=direction_rules(chosen.mode == fastest.mode, chosen.duration_min - fastest.duration_min,
                                  chosen.difference_g))


def ollama_proc():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-Process | Where-Object {$_.ProcessName -like 'ollama*'} | "
                          "Select-Object ProcessName,@{n='MB';e={[int]($_.WorkingSet64/1MB)}} | ConvertTo-Json"],
                         capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else []


def vram():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="gpu")
    ap.add_argument("--no-hosted-floor", action="store_true")
    a = ap.parse_args()
    cases = make_cases()
    res = {"label": a.label, "n": len(cases), "model": "qwen2.5:1.5b", "stamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    t_lat, t_fk = [], []
    for chosen, fastest, met in cases:
        s = time.perf_counter()
        for _ in range(200):
            txt = recommendation_template(chosen, fastest, met)
        t_lat.append((time.perf_counter() - s) / 200 * 1000)
        t_fk.append(fk_grade(txt))
    res["A"] = {"latency_ms_median": statistics.median(t_lat), "latency_ms_p95": pct(t_lat, 95),
                "unsupported_rate": 0.0, "fk_grade_mean": statistics.mean(t_fk)}

    client = OllamaClient(timeout_s=120)
    rows, lat, fk, viol, gated_fk, cats = [], [], [], 0, [], {}
    try:
        s = time.perf_counter()
        client.generate("Say OK.")
        res["B_first_call_ms"] = (time.perf_counter() - s) * 1000
    except ModelUnavailable as e:
        sys.exit(f"Ollama not reachable: {e}")
    for i, (chosen, fastest, met) in enumerate(cases):
        tpl = recommendation_template(chosen, fastest, met)
        s = time.perf_counter()
        raw = client.generate(build_prompt(tpl))
        ms = (time.perf_counter() - s) * 1000
        text = raw.strip().strip('"').strip()
        v = check_explanation(text, facts_for(chosen, fastest, tpl))
        lat.append(ms)
        fk.append(fk_grade(text))
        gated_fk.append(fk_grade(text if not v else tpl))
        viol += bool(v)
        for x in v:
            k = re.split(r" \(| [0-9]", x)[0]
            cats[k] = cats.get(k, 0) + 1
        rows.append({"i": i, "chosen": chosen.mode, "template": tpl, "model_text": text, "latency_ms": round(ms),
                     "violations": "; ".join(v)})
    res["B"] = {"latency_ms_median": statistics.median(lat), "latency_ms_p95": pct(lat, 95), "latency_ms_max": max(lat),
                "raw_unsupported_rate": viol / len(cases), "raw_unsupported_count": viol,
                "violation_categories": cats, "fk_grade_mean_raw": statistics.mean(fk),
                "fk_grade_mean_after_guardrail": statistics.mean(gated_fk),
                "within_2s": sum(1 for x in lat if x <= 2000) / len(lat),
                "ollama_process_mb": ollama_proc(), "gpu_mem_used": vram()}
    with open(os.path.join(DATA, f"spike_{a.label}_cases.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    if not a.no_hosted_floor:
        floor = []
        for _ in range(10):
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=b"{}", method="POST",
                                         headers={"content-type": "application/json", "anthropic-version": "2023-06-01"})
            s = time.perf_counter()
            try:
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass
            floor.append((time.perf_counter() - s) * 1000)
        res["C_network_floor_ms"] = {"median": statistics.median(floor), "min": min(floor), "max": max(floor), "n": len(floor)}
    with open(os.path.join(DATA, f"spike_{a.label}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
