from grounding.decompose import decompose_output_claude
from grounding.metrics import groundedness
from grounding.pipeline import label_claims
from grounding.verify import verify_subclaim_claude

DEFAULT_VERIFIER_MODEL = "claude-haiku-4-5-20251001"

# One Claude call per decomposed claim (decompose) + one per subclaim
# (verify). An adversarially padded ai_output that decomposes into hundreds
# of subclaims would otherwise turn one free check into hundreds of
# large-context Claude calls. A real <=3,500-char output rarely exceeds
# ~30 subclaims; these caps sit well clear of legitimate use.
MAX_CLAIMS = 50
MAX_VERIFIER_CALLS = 100


class CheckTooComplex(ValueError):
    """Raised when a decomposed check would exceed the per-request fan-out
    caps. Mapped to a generic HTTP 400 by the API layer -- it is a property
    of the input, not a server fault, so it must not 502."""


def _claude_verifier(client, model):
    def verify(subclaim, chunks):
        return (verify_subclaim_claude(subclaim, chunks, client, model), None, None)
    return verify


def run_live_check(
    ai_output: str, sections: list[dict], client, verifier_model: str = DEFAULT_VERIFIER_MODEL,
) -> dict:
    """Orchestrates a single live grounding check: decompose -> verify -> label -> score.

    Deliberately returns no `scorecard` -- recall/kappa are corpus-level
    validation stats with no committed measurement for the live Claude
    verifier (every committed fixture validates flan-t5-large/MiniCheck
    instead). Reusing those numbers here would misrepresent this verifier's
    actual measured reliability. Callers needing a user-facing disclosure
    should use `verifier_model` to build one, not fabricate scorecard fields.
    """
    full_text = "".join(s["text"] for s in sections)
    decomposed = decompose_output_claude(ai_output, client)
    total_subclaims = sum(len(d["subclaims"]) for d in decomposed)
    if len(decomposed) > MAX_CLAIMS or total_subclaims > MAX_VERIFIER_CALLS:
        raise CheckTooComplex(
            f"{len(decomposed)} claims / {total_subclaims} subclaims exceeds "
            f"the per-check limit ({MAX_CLAIMS}/{MAX_VERIFIER_CALLS})"
        )
    verifier_fn = _claude_verifier(client, verifier_model)
    claims = label_claims(decomposed, full_text, sections, verifier_fn, verifier_model=verifier_model)
    return {
        "ai_output": ai_output,
        "source": {"sections": sections},
        "claims": claims,
        "groundedness": groundedness([c["label"] for c in claims]),
        "verifier_model": verifier_model,
    }
