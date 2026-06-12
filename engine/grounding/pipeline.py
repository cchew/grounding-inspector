from grounding.verify import verify_subclaim, chunk_document
from grounding.labelling import aggregate_label
from grounding.localise import best_span


def label_claims(decomposed: list[dict], full_text: str, sections: list[dict], scorer) -> list[dict]:
    """Wire decompose -> verify (per sub-claim, full-doc) -> aggregate_label -> localise -> claim record."""
    chunks = chunk_document(full_text)
    out = []
    for i, dc in enumerate(decomposed):
        supported = [verify_subclaim(sc, chunks, scorer)[0] for sc in dc["subclaims"]]
        label = aggregate_label(supported)
        span = None if label == "unsupported" else best_span(dc["text"], sections)
        out.append({
            "id": f"c{i+1}", "text": dc["text"], "label": label,
            "evidence_span_ids": [span["id"]] if span else [],
            "quote": (span["text"][:80] if span else None),
            "page": (span["page"] if span else None),
            "rationale": "",  # filled by author in the frozen fixture
        })
    return out
