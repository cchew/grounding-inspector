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

def section_char_ranges(sections: list[dict], full_text: str) -> list[tuple[int, int] | None]:
    """Each section's (start, end) offset within full_text, located by substring
    search rather than assumed via section-level char_start/char_end (those are
    page-relative, confirmed against real fixture data) or a guessed join
    separator (production callers use different separators). Returns None for
    a section whose text isn't found -- defensive; shouldn't happen when
    full_text was actually built by joining these sections."""
    ranges = []
    cursor = 0
    for s in sections:
        idx = full_text.find(s["text"], cursor)
        if idx == -1:
            ranges.append(None)
            continue
        ranges.append((idx, idx + len(s["text"])))
        cursor = idx + len(s["text"])
    return ranges

def span_from_chunk_index(chunk_idx: int, full_text: str, sections: list[dict], max_chars: int = 1000) -> dict | None:
    """Resolve the section overlapping the given verifier chunk index the most."""
    chunk_start, chunk_end = chunk_idx * max_chars, chunk_idx * max_chars + max_chars
    best, best_overlap = None, 0
    for s, r in zip(sections, section_char_ranges(sections, full_text)):
        if r is None:
            continue
        overlap = max(0, min(chunk_end, r[1]) - max(chunk_start, r[0]))
        if overlap > best_overlap:
            best, best_overlap = s, overlap
    return best
