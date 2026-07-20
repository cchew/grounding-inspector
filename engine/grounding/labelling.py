from typing import Literal

Label = Literal["grounded", "partial", "unsupported"]

def aggregate_label(subclaim_supported: list[bool]) -> Label:
    """A displayed claim is grounded iff all its atomic sub-claims are supported,
    unsupported iff none are, and partial otherwise (council: operational, not
    threshold-derived). A claim with zero sub-claims (the decomposer found
    nothing atomic/checkable, e.g. a pure opinion statement) has no supported
    verdict to aggregate -- treated as unsupported."""
    if not subclaim_supported:
        return "unsupported"
    if all(subclaim_supported):
        return "grounded"
    if not any(subclaim_supported):
        return "unsupported"
    return "partial"
