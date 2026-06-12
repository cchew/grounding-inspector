from grounding.localise import best_span

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
