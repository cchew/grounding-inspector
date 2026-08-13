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
    span = span_from_chunk_index(0, full_text, sections, max_chars=10)  # chunk 0: chars 0-10, entirely inside sA
    assert span["id"] == "sA"

def test_span_from_chunk_index_chunk_crosses_section_boundary():
    sections = [
        {"id": "sA", "page": 1, "text": "A" * 20},
        {"id": "sB", "page": 2, "text": "B" * 20},
    ]
    full_text = "".join(s["text"] for s in sections)  # sA spans 0-20, sB spans 20-40
    # chunk 1 with max_chars=15 spans chars 15-30: 5 chars inside sA (15-20),
    # 10 chars inside sB (20-30) -- sB has the larger overlap and wins.
    span = span_from_chunk_index(1, full_text, sections, max_chars=15)
    assert span["id"] == "sB"
