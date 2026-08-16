import re
from dataclasses import dataclass
from typing import Literal

_MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")
_COUNT_RE = re.compile(r"\b(\d+)\s*(?:days?|months?|years?)\b")
_ALIAS_SUFFIX_AFTER_RE = re.compile(r"\s*(K|M|thousand|million)\b")
_QUALIFIERS = {"about", "approximately", "roughly"}
_ALIAS_SCALES = {"K": 1e3, "thousand": 1e3, "M": 1e6, "million": 1e6}


def _find_claim_span(claim_text: str):
    """Locate the single matched numeric span in claim_text (money, percent,
    or count) and return its match object -- not just the value -- so
    select_policy can inspect text immediately following the specific
    number being checked, rather than searching the whole claim for an
    alias-looking token that might belong to a different, unrelated number.
    Assumes check_numeric_claim's precondition of exactly one numeric span
    already holds; tries each extraction regex in turn and returns the
    first (and, under that precondition, only) match."""
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

    Claim texts in this codebase are single short sentences already (see
    extract_numbers' callers), so PCN's "within the same sentence" qualifier
    scope reduces to "anywhere in claim_text" here -- no sentence splitting
    needed.

    Priority order (spec section 1, with the reviewed correction already
    applied -- "up to" and "around" are NOT qualifiers; both were unstated
    additions beyond PCN's own set and "up to $X" is an exact-cap statement
    in this domain's fixtures, not an approximation):
      1. qualifier word {"about", "approximately", "roughly"} -> tolerance
      2. a scale suffix/word attached to the number ("$1.5K") -> alias
      3. a "%" anywhere in the claim -> rounded
      4. everything else -> exact
    """
    words = set(re.findall(r"[a-z]+", claim_text.lower()))
    if words & _QUALIFIERS:
        return "tolerance", {"rel_tolerance": 0.1}
    span = _find_claim_span(claim_text)
    if span is not None:
        suffix_match = _ALIAS_SUFFIX_AFTER_RE.match(claim_text, span.end())
        if suffix_match:
            return "alias", {"scale": _ALIAS_SCALES[suffix_match.group(1)]}
    if "%" in claim_text:
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
    return Verified() if ok else Contradicted(claim_value=claim_value, policy=policy)


def _format_claim_value(claim_text: str, value: float) -> str:
    """Best-effort human-readable rendering of a claim's numeric value for
    rationale text: money keeps its $ prefix and thousands separators,
    percentages keep a % suffix, everything else renders plain."""
    if _MONEY_RE.search(claim_text):
        return f"${value:,.0f}"
    if _PERCENT_RE.search(claim_text):
        return f"{value:g}%"
    return f"{value:g}"


def format_mismatch_rationale(claim_text: str, result: Contradicted) -> str:
    """Shared rationale text for a Contradicted result -- used by both
    pipeline.py's label-downgrade path and notebook/patch_fixtures.py's
    one-off fixture regeneration, so the wording can't drift between them."""
    value_str = _format_claim_value(claim_text, result.claim_value)
    return (
        f"Claim states {value_str}; this figure does not appear in the "
        f"matched evidence under the {result.policy} policy (automated numeric check)."
    )
