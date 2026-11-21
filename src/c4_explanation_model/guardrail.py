"""C.4 guardrail: decides whether a language-model explanation may be shown (requirement 2.1.10, risk TR.4).

The model is only allowed to rephrase. It receives facts that C.2 already calculated and its text is accepted
only if it states nothing else. `check_explanation` is deterministic and has no model in it: every figure in the
text must be one of the calculated figures, every travel mode named must be one the result is about (or the
always-drive baseline), no weather condition or overclaim may appear that the template did not already contain,
and the figures the result must state (the required ones) must all be present. Anything else returns a list of
violations and the caller shows the template text instead (ADR 0011).
"""
import re
from dataclasses import dataclass

MAX_CHARS = 600

# canonical mode -> words that name it. A word that names a mode the result is not about is a violation.
MODE_WORDS = {
    "drive": ("drive", "drives", "driving", "drove", "car", "cars", "driver"),
    "walk": ("walk", "walks", "walking", "walked", "foot"),
    "bike": ("bike", "bikes", "biking", "cycle", "cycling", "bicycle", "bicycles"),
    "scooter": ("scooter", "scooters"),
    "bus": ("bus", "buses", "transit"),
    "carpool": ("carpool", "carpooling"),
    "train": ("train", "trains", "subway", "metro", "tram", "rail"),
    "taxi": ("taxi", "taxis", "uber", "lyft", "rideshare"),
    "air": ("plane", "flight", "flying", "airplane"),
    "motorbike": ("motorcycle", "motorbike", "moped"),
    "boat": ("ferry", "boat"),
}
# weather and condition words; allowed only when the template itself used them
CONDITION_WORDS = (
    "rain", "raining", "rainy", "snow", "snowing", "storm", "stormy", "wind", "windy", "sunny", "sun", "cloudy",
    "fog", "foggy", "ice", "icy", "cold", "hot", "warm", "freezing", "humid", "temperature", "degrees", "forecast",
    "traffic", "congestion", "hill", "hills", "crash", "accident",
)
# claims the result cannot support
OVERCLAIM = re.compile(
    r"\b(guarantee\w*|definitely|certainly|proven|will save|you saved|you have saved|saves the planet|zero emissions?)\b",
    re.IGNORECASE,
)
NUMBER_WORDS = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|"
    r"half|double|twice|triple|dozen)\b",
    re.IGNORECASE,
)
MARKUP = re.compile(r"[<>\[\]{}`*#_|\\]|https?://|www\.", re.IGNORECASE)
NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


@dataclass(frozen=True)
class Facts:
    """What the explanation is allowed to say. Built by C.4 from values C.2 already calculated."""
    allowed_numbers: tuple            # every figure that may appear
    required_numbers: tuple           # figures that must appear
    allowed_modes: tuple              # canonical modes the text may name
    allowed_text: str = ""            # strings whose words and numbers are allowed (factor source, version, reason)
    required_phrases: tuple = ()      # phrases that must appear (case-insensitive); "a|b" means either
    forbidden: tuple = ()             # ((regex, why), ...) wording that would reverse or inflate a calculated fact


def _numbers(text: str):
    return [float(m.replace(",", "")) for m in NUMBER.findall(text)]


def _same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 + 1e-6 * max(abs(a), abs(b))


def _words(text: str):
    return re.findall(r"[a-z]+", text.lower())


def check_explanation(text, facts: Facts):
    """Return the list of violations (empty means the text may be shown). Never raises on bad input."""
    if not isinstance(text, str):
        return ["output is not text"]
    body = text.strip()
    if not body:
        return ["empty output"]
    problems = []
    if len(body) > MAX_CHARS:
        problems.append(f"longer than {MAX_CHARS} characters")
    if MARKUP.search(body):
        problems.append("contains markup, a link or code characters")

    allowed = list(facts.allowed_numbers) + _numbers(facts.allowed_text)
    for value in _numbers(body):
        if not any(_same(value, a) for a in allowed):
            problems.append(f"figure {value:g} is not in the calculated result")
    for needed in facts.required_numbers:
        if not any(_same(needed, v) for v in _numbers(body)):
            problems.append(f"required figure {needed:g} is missing")
    # clauses the template itself contains word for word are not judged again ("the fastest one that was not ruled out")
    scrubbed = body
    for clause in re.split(r"[;.]", facts.allowed_text):
        clause = clause.strip()
        if len(clause) > 15 and clause in scrubbed:
            scrubbed = scrubbed.replace(clause, " ")
    word_hit = NUMBER_WORDS.search(scrubbed)
    if word_hit:
        problems.append("a figure is written as a word (" + word_hit.group(0).lower() + ")")

    allowed_words = set(_words(facts.allowed_text))
    words = _words(body)
    for mode, names in MODE_WORDS.items():
        if mode in facts.allowed_modes:
            continue
        for name in names:
            if name in words and name not in allowed_words:
                problems.append(f"names a travel mode that is not in the result ({name})")
                break
    for word in CONDITION_WORDS:
        if word in words and word not in allowed_words:
            problems.append(f"states a condition that is not in the result ({word})")
    hit = OVERCLAIM.search(body)
    if hit and hit.group(0).lower() not in facts.allowed_text.lower():
        problems.append(f"overclaims ({hit.group(0).lower()})")
    lowered = body.lower()
    for phrase in facts.required_phrases:
        if not any(option in lowered for option in phrase.lower().split("|")):
            problems.append(f"required wording is missing ({phrase})")
    for pattern, why in facts.forbidden:
        if re.search(pattern, scrubbed, re.IGNORECASE):
            problems.append(f"contradicts the result ({why})")
    return problems


def direction_rules(chosen_is_fastest: bool, extra_minutes: float, difference_g: float):
    """Wording that would reverse a calculated comparison (a well-formed but wrong explanation).

    Found by reading real model output (docs/ch11/data/spike_gpu_guard_v1_cases.csv): a small model wrote
    "9 minutes faster than the fastest" for a ride that takes 9 minutes longer.
    """
    rules = []
    if not chosen_is_fastest:
        rules += [(r"\b(faster|quicker|shorter|less time|fewer minutes)\b", "says faster when it is slower"),
                  (r"\b(is|as) (also )?the (fastest|quickest)\b", "calls it the fastest when it is not")]
    else:
        rules += [(r"\b(slower|longer than|more minutes)\b", "says slower when it is the fastest")]
    if difference_g > 0:
        rules += [(r"\b(more|higher|worse|greater) than driving\b", "says more than driving when it is less")]
    else:
        rules += [(r"\b(less|lower|fewer|better) than driving\b", "says less than driving when it is not")]
    return tuple(rules)
