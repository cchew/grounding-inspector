from grounding.labelling import aggregate_label

def test_all_supported_is_grounded():
    assert aggregate_label([True, True]) == "grounded"

def test_none_supported_is_unsupported():
    assert aggregate_label([False, False]) == "unsupported"

def test_mixed_is_partial():
    assert aggregate_label([True, False]) == "partial"

def test_single_subclaim():
    assert aggregate_label([True]) == "grounded"
    assert aggregate_label([False]) == "unsupported"

def test_empty_is_unsupported():
    # A claim with zero atomic sub-claims (e.g. a pure opinion statement the
    # decomposer found nothing checkable in) has no supported verdict to
    # aggregate -- treated as unsupported, not an error.
    assert aggregate_label([]) == "unsupported"
