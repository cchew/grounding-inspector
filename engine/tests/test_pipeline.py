# engine/tests/test_pipeline.py
from grounding.pipeline import label_claims

SECTIONS = [
    {"id": "s1", "page": 1, "char_start": 0, "char_end": 50,
     "text": "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."},
]


def always_true(subclaim, chunks):
    return True


def test_numeric_mismatch_downgrades_grounded_to_unsupported():
    # Claim text shares enough vocabulary with the section ("laptop", "computer")
    # for best_span()'s token-overlap threshold to find a match even though the
    # mismatched number itself ($5 vs $4/$3) contributes no shared token -- a
    # claim using only "laptops... $5,000" without "Computer" scores 0.125,
    # just under best_span()'s 0.15 threshold, and no span is found at all.
    decomposed = [{"text": "Laptop Computer is covered for up to $5,000.", "subclaims": ["laptop computer covered to $5,000"]}]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "unsupported"
    assert "$5,000" in claims[0]["rationale"]
    assert "automated numeric check" in claims[0]["rationale"]


def test_no_numeric_mismatch_keeps_grounded_label_and_empty_rationale():
    decomposed = [{"text": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]}]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "grounded"
    assert claims[0]["rationale"] == ""


def test_mixed_subclaims_with_numeric_mismatch_stays_partial():
    decomposed = [{
        "text": "Laptop Computer is covered, for up to $5,000.",
        "subclaims": ["laptop computer is covered", "the limit is $5,000"],
    }]
    def half_true(subclaim, chunks):
        return "covered" in subclaim
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, half_true)
    assert claims[0]["label"] == "partial"
    assert "$5,000" in claims[0]["rationale"]
