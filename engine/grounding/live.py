from grounding.decompose import decompose_output_claude
from grounding.metrics import groundedness
from grounding.pipeline import label_claims
from grounding.verify import verify_subclaim_claude

DEFAULT_VERIFIER_MODEL = "claude-haiku-4-5-20251001"


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
    verifier_fn = _claude_verifier(client, verifier_model)
    claims = label_claims(decomposed, full_text, sections, verifier_fn, verifier_model=verifier_model)
    return {
        "ai_output": ai_output,
        "source": {"sections": sections},
        "claims": claims,
        "groundedness": groundedness([c["label"] for c in claims]),
        "verifier_model": verifier_model,
    }
