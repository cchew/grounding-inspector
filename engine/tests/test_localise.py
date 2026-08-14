from grounding.localise import best_span, section_char_ranges, span_from_chunk_index

SECTIONS = [
    {"id": "s1", "page": 1, "text": "General terms and definitions."},
    {"id": "s7_1", "page": 22, "text": "Baggage sub-limit of $1,000 per item."},
]

def test_picks_most_similar_section():
    span = best_span("items limited to $1,000 each", SECTIONS)
    assert span["id"] == "s7_1"
    assert span["page"] == 22

def test_returns_none_below_threshold():
    span = best_span("zzzz totally unrelated quantum", SECTIONS, min_overlap=0.5)
    assert span is None

def test_section_char_ranges_works_with_space_separator():
    full_text = " ".join(s["text"] for s in SECTIONS)
    ranges = section_char_ranges(SECTIONS, full_text)
    assert ranges[0] == (0, len(SECTIONS[0]["text"]))
    expected_start = len(SECTIONS[0]["text"]) + 1  # +1 for the space separator
    assert ranges[1] == (expected_start, expected_start + len(SECTIONS[1]["text"]))

def test_section_char_ranges_works_with_newline_separator():
    full_text = "\n".join(s["text"] for s in SECTIONS)
    ranges = section_char_ranges(SECTIONS, full_text)
    assert ranges[0] == (0, len(SECTIONS[0]["text"]))
    expected_start = len(SECTIONS[0]["text"]) + 1  # +1 for the newline separator
    assert ranges[1] == (expected_start, expected_start + len(SECTIONS[1]["text"]))

def test_section_char_ranges_returns_none_for_missing_section():
    missing = {"id": "s99", "page": 99, "text": "This text is not in full_text."}
    full_text = " ".join(s["text"] for s in SECTIONS)  # missing's text is not included
    ranges = section_char_ranges(SECTIONS + [missing], full_text)
    assert ranges[2] is None

def test_span_from_chunk_index_chunk_fully_inside_one_section():
    sections = [
        {"id": "sA", "page": 1, "text": "A" * 20},
        {"id": "sB", "page": 2, "text": "B" * 20},
    ]
    full_text = "".join(s["text"] for s in sections)  # sA spans 0-20, sB spans 20-40
    span = span_from_chunk_index(0, full_text, sections, "placeholder claim", max_chars=10)  # chunk 0: chars 0-10, entirely inside sA
    assert span["id"] == "sA"

def test_span_from_chunk_index_chunk_crosses_section_boundary():
    sections = [
        {"id": "sA", "page": 1, "text": "A" * 20},
        {"id": "sB", "page": 2, "text": "B" * 20},
    ]
    full_text = "".join(s["text"] for s in sections)  # sA spans 0-20, sB spans 20-40
    # chunk 1 with max_chars=15 spans chars 15-30: 5 chars inside sA (15-20),
    # 10 chars inside sB (20-30) -- sB has the larger overlap and wins.
    span = span_from_chunk_index(1, full_text, sections, "placeholder claim", max_chars=15)
    assert span["id"] == "sB"

def test_span_from_chunk_index_breaks_ties_by_keyword_relevance_when_chunk_dwarfs_sections():
    # Real fixtures are far smaller than max_chars (1000): a whole document's
    # sections often sit entirely inside one chunk. Raw overlap alone can't
    # discriminate then -- every fully-contained section's overlap equals its
    # own length, so ranking by overlap degenerates to "pick the longest
    # section," discarding all relevance to the claim (the exact bug found in
    # final review against real fixture data, e.g. travel-pds-01).
    sections = [
        {"id": "intro", "page": 1, "text": "This document sets out the terms of the SunSafe Travel Insurance policy for eligible travellers."},
        {"id": "medical", "page": 1, "text": "Overseas medical expenses are covered up to $10,000,000 for emergency treatment while travelling."},
        {"id": "baggage", "page": 2, "text": "Baggage and personal effects are covered subject to a sub-limit of $1,000 per item and $5,000 in total value."},
        {"id": "exclusions", "page": 3, "text": "Exclusions: claims arising from extreme sports, war, or pre-existing conditions not declared at purchase."},
    ]
    full_text = " ".join(s["text"] for s in sections)
    assert len(full_text) < 1000  # sanity check: this must be a single-chunk document
    claim = "Overseas medical expenses are covered up to $10,000,000."
    span = span_from_chunk_index(0, full_text, sections, claim, max_chars=1000)
    assert span["id"] == "medical"  # not "baggage", which is the longest section

def test_span_from_chunk_index_sole_fully_contained_section_still_competes_on_overlap():
    # When at most one section is fully contained, raw overlap must still be
    # compared against partially-overlapping sections, not returned unconditionally
    # just because it's the only fully-contained one -- a tiny fully-contained
    # section should not beat a large section that has far more of its own text
    # inside the same chunk.
    sections = [
        {"id": "tiny", "page": 1, "text": "X" * 10},
        {"id": "large", "page": 2, "text": "Y" * 1490},
    ]
    full_text = "".join(s["text"] for s in sections)  # tiny spans 0-10, large spans 10-1500
    # chunk 0 (max_chars=1000) fully contains "tiny" (overlap 10) and partially
    # overlaps "large" (990 of its 1490 chars) -- "large" has the greater overlap.
    span = span_from_chunk_index(0, full_text, sections, "placeholder claim", max_chars=1000)
    assert span["id"] == "large"
