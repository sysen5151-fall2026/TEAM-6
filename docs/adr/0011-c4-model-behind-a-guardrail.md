# ADR 0011: C.4 may use a local language model only behind a guardrail, with the template as the fallback

Status: **Proposed - needs team review and merge approval** (date: 2026-11-22).

## Context

C.4 Explanation Model has been a fixed sentence template since the walking skeleton ("a stub instead of a local language model", BMA Section 7.9). Requirement 2.1.10 says the explanation may state only facts contained in the calculated result, and risk TR.4 is the chance that a language-model explanation states a figure, condition or mode that is not there. Chapter 12 (risk assessment) asks for the AI-specific risks of the product and for a guardrail or fallback for the top AI risk, with a test of the failure path.

Chapter 11 includes a spike on this: 40 explanation cases were given to a locally hosted model (qwen2.5:1.5b, Ollama 0.40.17, on an RTX 5060 laptop GPU) with the instruction to rephrase the template sentence, and every raw reply was checked against the calculated values.

## Decision

- Keep the template as the **authoritative** text. `src/c4_explanation_model/explainer.py` builds it from the calculated values exactly as before.
- Add an **optional** local model (`ECOCOMMUTE_EXPLAINER=local`; off by default). It receives only the template sentence (never a place name or any text from a data source) and may only rephrase it.
- Add a **guardrail** (`guardrail.py`): the model's text is shown only if every figure is one of the calculated figures, every travel mode named is one the result is about (or the always-drive baseline), no weather condition or overclaim appears that the template did not contain, the required figures and the word "estimate" are present, and no comparison is reversed (faster/slower, more/less than driving). Anything else, or a model that is down, slow (2.0 s), on another machine, or answers in an unexpected shape, shows the template instead (the **fallback**), is counted in `explanation_stats()`, and a 60 s circuit breaker stops asking a model that has just failed.
- The model host must be loopback; another host is refused unless `ECOCOMMUTE_ALLOW_REMOTE_MODEL=1`, so trip facts do not leave the machine unnoticed.

We built a guardrail and a fallback. The guardrail prevents the failure (a wrong sentence cannot pass); the fallback contains the model being unavailable. The guardrail is the primary control because the failure is silent: a wrong sentence looks like a right one.

## Measures

| Measure | Result (40 cases, 22 November 2026) |
|---|---|
| Raw outputs rejected by the first version of the check | 7 of 40 (17.5%), all for missing wording; the check did not look at comparisons |
| Raw outputs rejected by the final check | 20 of 40 (50.0%); 20 contradict the result (reversed "faster", "the fastest" for a slower ride), 3 drop the word "estimate", 1 omits a required figure |
| Rejected outputs shown to a commuter | 0 (the template is shown instead) |
| Reply time, median / 95th percentile / maximum (GPU, warm) | 0.226 s / 0.261 s / 0.273 s |
| First call after the model server starts | up to 44.7 s (model load) |
| Template reply time | 0.7 microseconds |
| Reading grade (Flesch-Kincaid, heuristic): template / model | 6.9 / 9.0 |

The first version of the check missed the reversed comparisons (for example "9 minutes faster than the fastest" for a ride that takes 9 minutes longer). They were found by reading the recorded outputs (`docs/ch11/data/spike_gpu_guard_v1_cases.csv`), not by the assistant, and the direction rules were added. The corpus is kept as the regression set.

## Reasons

- A 1.5-billion-parameter model got the facts wrong in half of the cases, so it cannot be the author of what a commuter reads. It reads at a higher grade than the template. Its only advantage is the variety of phrasing.
- A guardrail that checks the model's text against the values makes the model's reliability irrelevant to requirement 2.1.10: the measure of that requirement (sampled explanations with an unsupported figure, condition or mode; target 0) is met by construction for what is shown.
- Qwen2.5 1.5B is licensed Apache License 2.0 (Ollama library page for qwen2.5:1.5b, checked 2026-11-22); Ollama is open source. Neither is a required dependency.

## What the losing choices would have required

- **Model as the only author (no template):** no failure path at all; each wrong sentence would reach the commuter, so the 2.1.10 measure would have been 50% on this model.
- **Hosted model:** an API key, a per-call price and the trip facts leaving the machine (risk TR.19); it was not measured here (no key), so its quality is not claimed.

## Consequences

- Tests: `tests/test_c4_guardrail.py` (23 tests): the template always passes its own check; each wrong output (invented figure, mode, condition; reversed comparison; overclaim; markup; empty; non-text) is rejected; an unavailable model falls back and the breaker holds; an untrusted string never reaches the prompt; a reply with another shape is "schema drift"; another host is refused.
- The existing tests are unchanged and pass with the template default.
- The model is not needed for the pilot. Turn it on only after a sample of 50 displayed explanations is inspected field by field (requirement 2.1.10 validation).

## Evidence that would change this decision

- A model that gets the reversed-comparison cases right on the 40-case corpus, so the fallback is rare.
- A requirement for a language the template does not cover.
