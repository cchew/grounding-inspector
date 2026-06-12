import math
from collections import Counter
from scipy.stats import beta

_WEIGHTS = {"grounded": 1.0, "partial": 0.5, "unsupported": 0.0}

def groundedness(labels: list[str]) -> dict:
    bad = [l for l in labels if l not in _WEIGHTS]
    if bad:
        raise ValueError(f"unknown label(s): {bad}; expected one of {list(_WEIGHTS)}")
    c = Counter(labels)
    n = len(labels)
    # Use round-half-up (not Python banker's rounding) to match spec
    score = math.floor(100 * sum(_WEIGHTS[l] for l in labels) / n + 0.5) if n else 0
    return {
        "score": score,
        "n_grounded": c["grounded"], "n_partial": c["partial"], "n_unsupported": c["unsupported"],
    }

def recall_with_ci(tp: int, fn: int, alpha: float = 0.05) -> tuple[float, tuple[float, float]]:
    """Recall on the ungrounded class with an exact Clopper-Pearson interval.
    tp = hallucinations caught, fn = hallucinations missed."""
    n = tp + fn
    if n == 0:
        return 0.0, (0.0, 0.0)
    k = tp
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return k / n, (float(lo), float(hi))
