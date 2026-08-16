import re
from dataclasses import dataclass
from typing import Literal

_MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")
_COUNT_RE = re.compile(r"\b(\d+)\s*(?:days?|months?|years?)\b")
_ALIAS_SUFFIX_AFTER_RE = re.compile(r"\s*(K|M|thousand|million)\b")
_QUALIFIERS = {"about", "approximately", "roughly"}
_ALIAS_SCALES = {"K": 1e3, "thousand": 1e3, "M": 1e6, "million": 1e6}
_QUALIFIER_WINDOW_CHARS = 30


def _find_claim_span(claim_text: str):
    """Locate the single matched numeric span in claim_text (money, percent,
    or count) and return its match object -- not just the value -- so
    select_policy can inspect text immediately surrounding the specific
    number being checked, rather than scanning the whole claim for a
    qualifier word, alias suffix, or "%" that might belong to a different,
    unrelated number. Assumes check_numeric_claim's precondition of exactly
    one numeric span already holds; tries each extraction regex in turn and
    returns the first (and, under that precondition, only) match."""
    for regex in (_MONEY_RE, _PERCENT_RE, _COUNT_RE):
        m = regex.search(claim_text)
        if m:
            return m
    return None


def extract_numbers(text: str) -> list[float]:
    """Extract numeric spans from text in reading order: dollar figures,
    percentages, and day/month/year counts. Scoped to these three shapes --
    the domain's real numeric-claim shapes per FUTURE.md's SOTA scan -- not
    a general number extractor. A scaled dollar figure like "$1.5K" already
    extracts as 1.5 via _MONEY_RE, which stops at the first non-numeric
    character; select_policy() re-scans the raw text separately to detect
    the "K" suffix for policy selection.
    """
    matches: list[tuple[int, float]] = []
    for regex in (_MONEY_RE, _PERCENT_RE, _COUNT_RE):
        for m in regex.finditer(text):
            matches.append((m.start(), float(m.group(1).replace(",", ""))))
    matches.sort(key=lambda pair: pair[0])
    return [value for _, value in matches]


@dataclass(frozen=True)
class Verified:
    pass


@dataclass(frozen=True)
class Contradicted:
    claim_value: float
    policy: str
    scale: float = 1.0
    """The scale applied by the alias policy (1.0 for every other policy).
    claim_value stays the pre-scale number check_alias() received -- e.g. 1.5
    for a claim reading "$1.5K" -- because that's what check_alias() itself
    operates on. Rationale rendering needs claim_value * scale (the effective
    dollar amount, e.g. 1500) to describe what the claim actually said."""


@dataclass(frozen=True)
class NotChecked:
    reason: Literal["no_numeric_span", "multiple_numeric_spans", "no_evidence_numbers"]


NumericResult = Verified | Contradicted | NotChecked


def check_exact(claim_value: float, evidence_values: list[float]) -> bool:
    return claim_value in evidence_values


def check_rounded(claim_value: float, evidence_values: list[float], decimals: int) -> bool:
    return round(claim_value, decimals) in {round(v, decimals) for v in evidence_values}


def check_alias(claim_value: float, evidence_values: list[float], scale: float) -> bool:
    return any(abs(claim_value * scale - v) < 1e-9 for v in evidence_values)


def check_tolerance(claim_value: float, evidence_values: list[float], rel_tolerance: float) -> bool:
    return any(abs(claim_value - v) <= rel_tolerance * abs(v) for v in evidence_values)


_POLICY_FNS = {
    "exact": check_exact,
    "rounded": check_rounded,
    "alias": check_alias,
    "tolerance": check_tolerance,
}


def select_policy(claim_text: str, claim_value: float) -> tuple[str, dict]:
    """Pick a PCN policy for a claim's numeric span, first match wins.

    All three text-scanning rules (qualifier, alias suffix, percent) are
    anchored to the specific numeric span _find_claim_span locates, not
    scanned across the whole claim_text. A whole-text scan would let a
    qualifier, alias suffix, or stray "%" belonging to a different, unrelated
    number in the same sentence hijack policy selection -- confirmed as a
    real false-negative risk during final review (e.g. "approximately 24
    hours before departure, with an excess of $250" must not loosen the $250
    check just because "approximately" appears earlier in the sentence).

    Priority order (spec section 1, with the reviewed correction already
    applied -- "up to" and "around" are NOT qualifiers; both were unstated
    additions beyond PCN's own set and "up to $X" is an exact-cap statement
    in this domain's fixtures, not an approximation):
      1. qualifier word {"about", "approximately", "roughly"} within
         _QUALIFIER_WINDOW_CHARS immediately before the number -> tolerance
      2. a scale suffix/word attached to the number ("$1.5K") -> alias
      3. a "%" immediately after the number's digits -> rounded
      4. everything else -> exact
    """
    span = _find_claim_span(claim_text)
    if span is None:
        return "exact", {}
    preceding = claim_text[max(0, span.start() - _QUALIFIER_WINDOW_CHARS):span.start()]
    if set(re.findall(r"[a-z]+", preceding.lower())) & _QUALIFIERS:
        return "tolerance", {"rel_tolerance": 0.1}
    suffix_match = _ALIAS_SUFFIX_AFTER_RE.match(claim_text, span.end(1))
    if suffix_match:
        return "alias", {"scale": _ALIAS_SCALES[suffix_match.group(1)]}
    if claim_text[span.end(1):span.end(1) + 1] == "%":
        return "rounded", {"decimals": 1}
    return "exact", {}


def check_numeric_claim(claim_text: str, evidence_text: str) -> NumericResult:
    """Three-state result, replacing numeric_mismatch()'s overloaded
    Optional[float]. Conservative by design, same precondition as before:
    only checks when the claim states exactly one number -- declines
    (NotChecked) rather than guessing which of several claim numbers, or
    which of several evidence numbers, to compare.
    """
    claim_nums = extract_numbers(claim_text)
    if len(claim_nums) == 0:
        return NotChecked(reason="no_numeric_span")
    if len(claim_nums) > 1:
        return NotChecked(reason="multiple_numeric_spans")
    evidence_nums = extract_numbers(evidence_text)
    if not evidence_nums:
        return NotChecked(reason="no_evidence_numbers")
    claim_value = claim_nums[0]
    policy, params = select_policy(claim_text, claim_value)
    ok = _POLICY_FNS[policy](claim_value, evidence_nums, **params)
    if ok:
        return Verified()
    return Contradicted(claim_value=claim_value, policy=policy, scale=params.get("scale", 1.0))


def _format_claim_value(claim_text: str, value: float) -> str:
    """Best-effort human-readable rendering of a claim's numeric value for
    rationale text: money keeps its $ prefix, thousands separators, and cents
    when the value isn't a whole number; percentages keep a % suffix;
    everything else renders plain."""
    if _MONEY_RE.search(claim_text):
        return f"${value:,.2f}" if value % 1 else f"${value:,.0f}"
    if _PERCENT_RE.search(claim_text):
        return f"{value:g}%"
    return f"{value:g}"


def format_mismatch_rationale(claim_text: str, result: Contradicted) -> str:
    """Shared rationale text for a Contradicted result -- used by both
    pipeline.py's label-downgrade path and notebook/patch_fixtures.py's
    one-off fixture regeneration, so the wording can't drift between them.
    Renders claim_value * scale (the effective value the claim actually
    stated) rather than the raw pre-scale claim_value -- for a non-alias
    result scale is 1.0 and this is a no-op."""
    effective_value = result.claim_value * result.scale
    value_str = _format_claim_value(claim_text, effective_value)
    return (
        f"Claim states {value_str}; this figure does not appear in the "
        f"matched evidence under the {result.policy} policy (automated numeric check)."
    )
