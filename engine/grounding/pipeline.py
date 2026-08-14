from grounding.verify import chunk_document, CHUNK_MAX_CHARS
from grounding.labelling import aggregate_label
from grounding.localise import best_span, span_from_chunk_index, section_char_ranges
from grounding.numeric_check import numeric_mismatch


def label_claims(decomposed: list[dict], full_text: str, sections: list[dict], verifier_fn) -> list[dict]:
    """Wire decompose -> verify -> aggregate_label -> localise -> claim record.

    verifier_fn: callable(subclaim: str, chunks: list[str]) -> tuple[bool, float | None, int | None]
    Use make_minicheck_verifier() or make_claude_verifier() from grounding.verify.
    score/idx are None for verifiers with no per-chunk signal (Claude Haiku).

    The evidence span for a grounded/partial claim is resolved from the
    highest-scoring supported subclaim's verifier chunk index
    (span_from_chunk_index), falling back to best_span()'s keyword-overlap
    heuristic when no usable chunk index exists (Haiku verifier, or a chunk
    that doesn't overlap any section) -- never a hard failure or an empty
    span where one was previously found.

    A deterministic numeric-consistency check runs after aggregation: if the
    claim states a figure absent from its matched evidence, the label is
    downgraded (grounded -> unsupported, partial stays partial) and an
    honest, factual rationale is generated. This check is not part of the
    RAGTruth-validated verifier itself -- see numeric_check.py's docstring.
    """
    chunks = chunk_document(full_text, max_chars=CHUNK_MAX_CHARS)
    section_ranges = section_char_ranges(sections, full_text)
    out = []
    for i, dc in enumerate(decomposed):
        results = [verifier_fn(sc, chunks) for sc in dc["subclaims"]]
        label = aggregate_label([r[0] for r in results])
        span = None
        if label != "unsupported":
            candidates = [(score, idx) for supported, score, idx in results if supported and score is not None and idx is not None]
            if candidates:
                _, best_idx = max(candidates, key=lambda c: c[0])
                span = span_from_chunk_index(
                    best_idx, full_text, sections, dc["text"],
                    max_chars=CHUNK_MAX_CHARS, section_ranges=section_ranges,
                )
            if span is None:
                span = best_span(dc["text"], sections)
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
