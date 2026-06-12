def chunk_document(text: str, max_chars: int = 1000) -> list[str]:
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or [""]

def verify_subclaim(subclaim: str, doc_chunks: list[str], scorer) -> tuple[bool, float]:
    """Score the sub-claim against EVERY chunk and max-pool. No retrieval gate:
    we never pre-select top-k chunks, so retrieval recall cannot cap detection."""
    labels, probs, *_ = scorer.score(docs=doc_chunks, claims=[subclaim] * len(doc_chunks))
    best = max(probs) if probs else 0.0
    return best >= 0.5, float(best)

def build_scorer(model_name: str = "flan-t5-large"):
    from minicheck.minicheck import MiniCheck
    return MiniCheck(model_name=model_name, enable_prefix_caching=False, cache_dir="./ckpts")
