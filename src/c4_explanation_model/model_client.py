"""C.4 language-model client: a locally hosted model behind Ollama's HTTP API (ADR 0011).

Nothing here decides what is shown; `explainer.py` does that after `guardrail.check_explanation`.
Environment (all optional):
  ECOCOMMUTE_EXPLAINER            "template" (default) or "local"
  ECOCOMMUTE_OLLAMA_URL           default http://127.0.0.1:11434; a non-loopback host is refused unless
                                  ECOCOMMUTE_ALLOW_REMOTE_MODEL=1 (trip facts must not leave the machine unnoticed, risk TR.19)
  ECOCOMMUTE_OLLAMA_MODEL         default qwen2.5:1.5b
  ECOCOMMUTE_EXPLAINER_TIMEOUT_S  default 2.0 (the whole 3 s display budget of requirement 2.1.2 is shared with routing)
"""
import ipaddress
import json
import os
import urllib.request
from urllib.parse import urlparse

DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:1.5b"
DEFAULT_TIMEOUT_S = 2.0
MAX_REPLY_TOKENS = 120


class ModelUnavailable(Exception):
    """The model could not be reached, timed out, or answered in a shape we do not accept."""


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OllamaClient:
    def __init__(self, url=None, model=None, timeout_s=None, opener=None):
        self.url = (url or os.environ.get("ECOCOMMUTE_OLLAMA_URL") or DEFAULT_URL).rstrip("/")
        self.model = model or os.environ.get("ECOCOMMUTE_OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout_s = float(timeout_s or os.environ.get("ECOCOMMUTE_EXPLAINER_TIMEOUT_S") or DEFAULT_TIMEOUT_S)
        self._open = opener or urllib.request.urlopen
        host = urlparse(self.url).hostname or ""
        if not _is_loopback(host) and os.environ.get("ECOCOMMUTE_ALLOW_REMOTE_MODEL") != "1":
            raise ModelUnavailable(f"refusing a non-local model host ({host}); trip facts must not leave this machine")

    def generate(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.model, "prompt": prompt, "stream": False, "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 7, "num_predict": MAX_REPLY_TOKENS},
        }).encode()
        request = urllib.request.Request(self.url + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
        try:
            with self._open(request, timeout=self.timeout_s) as reply:
                data = json.loads(reply.read().decode("utf-8"))
        except Exception as error:  # timeouts, refused connections, bad JSON: all mean "unavailable"
            raise ModelUnavailable(f"{type(error).__name__}: {error}") from error
        text = data.get("response") if isinstance(data, dict) else None
        if not isinstance(text, str):
            raise ModelUnavailable("reply has no 'response' text (schema drift)")
        return text


def build_prompt(template_text: str) -> str:
    """The model sees only the calculated sentence and is asked to rephrase it (never to calculate)."""
    return (
        "Rewrite the message below in friendly, plain English for a student. Keep every number exactly as written "
        "and keep it an estimate. Do not add any number, place, weather, travel mode or advice that is not in the "
        "message. Use at most two sentences and no lists or formatting. Reply with the rewritten message only.\n\n"
        f"Message: {template_text}"
    )
