import re

_MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")


def extract_numbers(text: str) -> list[float]:
    """Extract dollar-figure numbers from text, e.g. '$4,000' -> [4000.0]."""
    return [float(m.replace(",", "")) for m in _MONEY_RE.findall(text)]


def numeric_mismatch(claim_text: str, evidence_text: str) -> float | None:
    """Return the claim's asserted number if it does not appear anywhere in
    the evidence text's number set, else None.

    Conservative by design: does not attempt to identify which evidence
    number a claim's figure should be compared against (an evidence span can
    contain many numbers, e.g. a whole benefits table) -- only flags when the
    claim states exactly one number and that number is entirely absent from
    the evidence. Declines (returns None) when the claim contains zero or
    multiple numbers, or when the evidence contains no numbers at all.
    """
    claim_nums = extract_numbers(claim_text)
    evidence_nums = extract_numbers(evidence_text)
    if len(claim_nums) != 1 or not evidence_nums:
        return None
    claim_value = claim_nums[0]
    if claim_value in evidence_nums:
        return None
    return claim_value
