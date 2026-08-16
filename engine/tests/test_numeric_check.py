# engine/tests/test_numeric_check.py
from grounding.numeric_check import (
    extract_numbers, select_policy, check_numeric_claim, format_mismatch_rationale,
    check_exact, check_rounded, check_alias, check_tolerance,
    Verified, Contradicted, NotChecked,
)

# --- extract_numbers -------------------------------------------------------

def test_extract_numbers_parses_dollar_figures():
    assert extract_numbers("Laptop Computer $4,000; Tablet $3,000") == [4000.0, 3000.0]

def test_extract_numbers_handles_no_numbers():
    assert extract_numbers("no figures here") == []

def test_extract_numbers_parses_percentages():
    assert extract_numbers("excess is 12.5%") == [12.5]

def test_extract_numbers_parses_day_month_year_counts():
    assert extract_numbers("compensated for 5 days") == [5.0]
    assert extract_numbers("valid for 3 months") == [3.0]
    assert extract_numbers("covered for 1 year") == [1.0]

def test_extract_numbers_scaled_dollar_figure_extracts_base_value():
    # "$1.5K" -- the existing money regex already stops at the first
    # non-numeric character, so this needs no new regex; select_policy
    # re-scans the raw text to detect the "K" suffix separately.
    assert extract_numbers("excess of $1.5K applies") == [1.5]

def test_extract_numbers_preserves_text_order_across_kinds():
    assert extract_numbers("5 days delay, then $4,000, then 10%") == [5.0, 4000.0, 10.0]

# --- policy functions --------------------------------------------------

def test_check_exact():
    assert check_exact(4000.0, [4000.0, 3000.0]) is True
    assert check_exact(5000.0, [4000.0, 3000.0]) is False

def test_check_rounded_matches_within_decimals():
    assert check_rounded(20.04, [20.0], decimals=1) is True

def test_check_rounded_rejects_outside_decimals():
    assert check_rounded(21.0, [20.0], decimals=1) is False

def test_check_alias_each_starter_set_unit():
    assert check_alias(1.5, [1500.0], scale=1e3) is True   # K / thousand
    assert check_alias(2.0, [2_000_000.0], scale=1e6) is True  # M / million
    assert check_alias(1.5, [1400.0], scale=1e3) is False

def test_check_tolerance_within_and_outside_relative_bound():
    assert check_tolerance(1050.0, [1000.0], rel_tolerance=0.1) is True   # within 10%
    assert check_tolerance(1200.0, [1000.0], rel_tolerance=0.1) is False  # outside 10%

# --- select_policy -------------------------------------------------------

def test_select_policy_qualifier_word_selects_tolerance():
    policy, params = select_policy("Excess is roughly $1,050.", 1050.0)
    assert policy == "tolerance"
    assert params == {"rel_tolerance": 0.1}

def test_select_policy_up_to_does_not_select_tolerance():
    # Reviewed correction: "up to $X" is an exact-cap statement in this
    # domain's fixtures, not an approximation qualifier.
    policy, _ = select_policy("Covered up to $5,000.", 5000.0)
    assert policy == "exact"

def test_select_policy_scale_suffix_selects_alias():
    policy, params = select_policy("Excess of $1.5K applies.", 1.5)
    assert policy == "alias"
    assert params == {"scale": 1e3}

def test_select_policy_percentage_always_rounded_never_falls_through_to_exact():
    policy, params = select_policy("Excess is 12%.", 12.0)
    assert policy == "rounded"
    assert params == {"decimals": 1}

def test_select_policy_plain_dollar_figure_selects_exact():
    policy, params = select_policy("Laptop Computer covered for $4,000.", 4000.0)
    assert policy == "exact"
    assert params == {}

# --- check_numeric_claim (replaces numeric_mismatch) ----------------------

def test_verified_when_claim_number_present_in_evidence():
    claim = "Cameras are covered for up to $4,000."
    evidence = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    assert check_numeric_claim(claim, evidence) == Verified()

def test_contradicted_when_claim_number_absent_from_evidence():
    claim = "Each laptop is covered for up to $5,000."
    evidence = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    assert check_numeric_claim(claim, evidence) == Contradicted(claim_value=5000.0, policy="exact")

def test_not_checked_when_claim_has_no_number():
    result = check_numeric_claim("Cameras are covered.", "Camera $4,000.")
    assert result == NotChecked(reason="no_numeric_span")

def test_not_checked_when_claim_has_multiple_numbers():
    result = check_numeric_claim("$4,000 or $5,000 depending on plan.", "Camera $4,000.")
    assert result == NotChecked(reason="multiple_numeric_spans")

def test_not_checked_when_evidence_has_no_numbers():
    result = check_numeric_claim("Covered up to $5,000.", "No figures mentioned here.")
    assert result == NotChecked(reason="no_evidence_numbers")

def test_contradicted_percentage_uses_rounded_policy():
    claim = "The co-payment is 15%."
    evidence = "The co-payment rate is 10.0% of the claim amount."
    assert check_numeric_claim(claim, evidence) == Contradicted(claim_value=15.0, policy="rounded")

def test_verified_tolerance_qualifier_within_bound():
    claim = "The excess is roughly $1,050."
    evidence = "The excess is $1,000."
    assert check_numeric_claim(claim, evidence) == Verified()

def test_verified_alias_scaled_dollar_figure():
    claim = "Excess of $1.5K applies."
    evidence = "The excess amount is $1,500."
    assert check_numeric_claim(claim, evidence) == Verified()

# --- format_mismatch_rationale ---------------------------------------------

def test_format_mismatch_rationale_dollar_claim():
    result = Contradicted(claim_value=5000.0, policy="exact")
    text = format_mismatch_rationale("Each laptop is covered for up to $5,000.", result)
    assert "$5,000" in text
    assert "exact" in text
    assert "automated numeric check" in text

def test_format_mismatch_rationale_percentage_claim():
    result = Contradicted(claim_value=15.0, policy="rounded")
    text = format_mismatch_rationale("The co-payment is 15%.", result)
    assert "15%" in text
    assert "rounded" in text
