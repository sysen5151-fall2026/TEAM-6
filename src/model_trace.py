"""Static model-to-code markers.

`@realizes("UC.1.5", ...)` tags a function with the Innoslate action IDs it
implements. It only attaches metadata and fills REGISTRY at import time; it does
not log or record anything at runtime (the Chapter 2 skeleton has no runtime
logging). tests/test_model_linkage.py uses REGISTRY to check that every UC.1
action has code and every tagged ID exists in the model.
"""

REGISTRY = {}  # action ID -> "module.function"


def realizes(*action_ids):
    def mark(fn):
        fn.model_ids = tuple(action_ids)
        for action_id in action_ids:
            REGISTRY.setdefault(action_id, []).append(f"{fn.__module__}.{fn.__qualname__}")
        return fn

    return mark
