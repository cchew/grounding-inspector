import re

def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$]+", s.lower()))

def best_span(claim: str, sections: list[dict], min_overlap: float = 0.15) -> dict | None:
    ct = _tokens(claim)
    if not ct:
        return None
    best, best_score = None, 0.0
    for s in sections:
        st = _tokens(s["text"])
        score = len(ct & st) / len(ct)
        if score > best_score:
            best, best_score = s, score
    return best if best_score >= min_overlap else None
