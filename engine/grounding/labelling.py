from typing import Literal

Label = Literal["grounded", "partial", "unsupported"]

def aggregate_label(subclaim_supported: list[bool]) -> Label:
    """A displayed claim is grounded iff all its atomic sub-claims are supported,
    unsupported iff none are, and partial otherwise (council: operational, not
    threshold-derived)."""
    if not subclaim_supported:
        raise ValueError("need at least one sub-claim verdict")
    if all(subclaim_supported):
        return "grounded"
    if not any(subclaim_supported):
        return "unsupported"
    return "partial"
