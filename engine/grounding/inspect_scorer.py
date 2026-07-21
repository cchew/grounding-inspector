from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from grounding.decompose import build_client, decompose_output
from grounding.metrics import groundedness
from grounding.pipeline import label_claims
from grounding.verify import build_scorer, make_claude_verifier, make_minicheck_verifier

DECOMPOSE_MODEL = "qwen2.5:7b-instruct"


@scorer(metrics=[mean(), stderr()])
def grounded_claim_scorer(verifier: str = "minicheck"):
    """Wraps engine/grounding's decompose -> verify -> label -> groundedness
    pipeline as an Inspect Scorer.

    `target` is unused -- Inspect's Target models a graded answer, which isn't
    what this checks. The source document instead travels via `state.metadata
    ["sections"]` (set by the Sample that produced this TaskState).

    Every call re-decomposes and re-verifies live (it does not replay a
    fixture's precomputed `claims`) -- this is deliberate: the point is
    proving the pipeline runs inside Inspect, not replaying a frozen result.
    The default `verifier="minicheck"` path uses local Ollama decomposition
    and local MiniCheck verification -- free, no API calls. `verifier="haiku"`
    switches the verifier only; decomposition still uses the local Ollama
    path (Claude-based decomposition is out of scope here).
    """
    async def score(state: TaskState, target: Target) -> Score:
        ai_output = state.output.completion
        sections = state.metadata["sections"]
        source_text = "\n".join(s["text"] for s in sections)
        verifier_fn = (
            make_minicheck_verifier(build_scorer())
            if verifier == "minicheck"
            else make_claude_verifier()
        )
        decomposed = decompose_output(ai_output, build_client(), model=DECOMPOSE_MODEL)
        labeled = label_claims(decomposed, source_text, sections, verifier_fn)
        stats = groundedness([c["label"] for c in labeled])
        n_claims = len(labeled)
        return Score(
            value=stats["score"] / 100,
            answer=(
                f"{stats['n_grounded']} grounded, {stats['n_partial']} partial, "
                f"{stats['n_unsupported']} unsupported ({n_claims} total)"
            ),
            metadata={"claims": labeled},
        )

    return score
