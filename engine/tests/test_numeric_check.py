# engine/tests/test_numeric_check.py
from grounding.numeric_check import extract_numbers, numeric_mismatch

def test_extract_numbers_parses_dollar_figures():
    assert extract_numbers("Laptop Computer $4,000; Tablet $3,000") == [4000.0, 3000.0]

def test_extract_numbers_handles_no_numbers():
    assert extract_numbers("no figures here") == []

def test_mismatch_detected_when_claim_number_absent_from_evidence():
    claim = "Each laptop is covered for up to $5,000."
    evidence = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    assert numeric_mismatch(claim, evidence) == 5000.0

def test_no_mismatch_when_claim_number_present_in_evidence():
    claim = "Cameras are covered for up to $4,000."
    evidence = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    assert numeric_mismatch(claim, evidence) is None

def test_no_mismatch_when_claim_has_no_number():
    assert numeric_mismatch("Cameras are covered.", "Camera $4,000.") is None

def test_no_mismatch_when_claim_has_multiple_numbers():
    # Ambiguous -- the conservative check declines rather than guessing which
    # of the claim's own numbers to compare.
    assert numeric_mismatch("$4,000 or $5,000 depending on plan.", "Camera $4,000.") is None

def test_no_mismatch_when_evidence_has_no_numbers():
    assert numeric_mismatch("Covered up to $5,000.", "No figures mentioned here.") is None
