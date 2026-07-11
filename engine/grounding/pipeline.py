from grounding.verify import verify_subclaim, chunk_document
from grounding.labelling import aggregate_label
from grounding.localise import best_span
from grounding.numeric_check import numeric_mismatch


def label_claims(decomposed: list[dict], full_text: str, sections: list[dict], verifier_fn) -> list[dict]:
    """Wire decompose -> verify -> aggregate_label -> localise -> claim record.

    verifier_fn: callable(subclaim: str, chunks: list[str]) -> bool
    Use make_minicheck_verifier() or make_claude_verifier() from grounding.verify.

    A deterministic numeric-consistency check runs after aggregation: if the
    claim states a figure absent from its matched evidence, the label is
    downgraded (grounded -> unsupported, partial stays partial) and an
    honest, factual rationale is generated. This check is not part of the
    RAGTruth-validated verifier itself -- see numeric_check.py's docstring.
    """
    chunks = chunk_document(full_text)
    out = []
    for i, dc in enumerate(decomposed):
        supported = [verifier_fn(sc, chunks) for sc in dc["subclaims"]]
        label = aggregate_label(supported)
        span = None if label == "unsupported" else best_span(dc["text"], sections)
        rationale = ""
        if span is not None:
            mismatch_value = numeric_mismatch(dc["text"], span["text"])
            if mismatch_value is not None:
                label = "unsupported" if label == "grounded" else "partial"
                rationale = (
                    f"Claim states ${mismatch_value:,.0f}; this figure does not "
                    f"appear in the matched evidence (automated numeric check)."
                )
        out.append({
            "id": f"c{i+1}", "text": dc["text"], "label": label,
            "evidence_span_ids": [span["id"]] if span else [],
            "quote": (span["text"][:80] if span else None),
            "page": (span["page"] if span else None),
            "rationale": rationale,
        })
    return out
