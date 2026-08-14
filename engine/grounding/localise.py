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

def span_from_chunk_index(
    chunk_idx: int,
    full_text: str,
    sections: list[dict],
    claim_text: str,
    max_chars: int = 1000,
    section_ranges: list[tuple[int, int] | None] | None = None,
) -> dict | None:
    """Resolve the section that is the verifier's actual evidence for the given
    chunk index.

    Raw character-overlap with the chunk is the primary signal, but it stops
    being discriminative when several sections are small enough to sit
    entirely inside one chunk (max_chars is much larger than typical section
    length on real fixtures) -- every fully-contained section then has
    overlap == its own length, and ranking by that value degenerates to
    "pick the longest section," discarding all relevance to the claim. When
    more than one section is fully contained in the winning chunk, keyword
    relevance (best_span) breaks the tie among just those candidates. When at
    most one section is fully contained -- the case fixed-size chunking was
    actually designed for, a chunk boundary cutting between sections -- raw
    overlap alone correctly identifies the section the boundary favours.
    """
    if section_ranges is None:
        section_ranges = section_char_ranges(sections, full_text)
    chunk_start, chunk_end = chunk_idx * max_chars, chunk_idx * max_chars + max_chars
    fully_contained: list[dict] = []
    partial: list[tuple[int, dict]] = []
    for s, r in zip(sections, section_ranges):
        if r is None:
            continue
        start, end = r
        overlap = max(0, min(chunk_end, end) - max(chunk_start, start))
        if overlap <= 0:
            continue
        if overlap == (end - start):
            fully_contained.append(s)
        else:
            partial.append((overlap, s))
    if len(fully_contained) > 1:
        return best_span(claim_text, fully_contained)
    if fully_contained:
        return fully_contained[0]
    if partial:
        return max(partial, key=lambda p: p[0])[1]
    return None
