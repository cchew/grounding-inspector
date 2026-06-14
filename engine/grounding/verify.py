_VERIFY_SYSTEM = (
    "You are a fact-checking system. Given a CLAIM and DOCUMENT CONTEXT, "
    "determine whether the document context supports the claim. "
    "Respond with exactly one word: SUPPORTED or UNSUPPORTED."
)


def chunk_document(text: str, max_chars: int = 1000) -> list[str]:
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or [""]


def verify_subclaim(subclaim: str, doc_chunks: list[str], scorer) -> tuple[bool, float]:
    """MiniCheck: score sub-claim against every chunk, max-pool. No retrieval gate."""
    if not doc_chunks:
        raise ValueError("doc_chunks must not be empty")
    labels, probs, *_ = scorer.score(docs=doc_chunks, claims=[subclaim] * len(doc_chunks))
    best = max(probs) if probs else 0.0
    return best >= 0.5, float(best)


def verify_subclaim_claude(subclaim: str, doc_chunks: list[str], client, model: str = "claude-haiku-4-5-20251001") -> bool:
    """Claude: send all chunks as one context, return True if supported."""
    context = "\n\n".join(doc_chunks)
    msg = client.messages.create(
        model=model,
        max_tokens=10,
        system=_VERIFY_SYSTEM,
        messages=[{"role": "user", "content": f"CLAIM: {subclaim}\n\nDOCUMENT CONTEXT:\n{context}"}],
    )
    return msg.content[0].text.strip().upper().startswith("SUPPORTED")


def build_scorer(model_name: str = "flan-t5-large"):
    from minicheck.minicheck import MiniCheck
    return MiniCheck(model_name=model_name, enable_prefix_caching=False, cache_dir="./ckpts")


def make_minicheck_verifier(scorer):
    """Wrap a MiniCheck scorer as a (subclaim, chunks) -> bool callable."""
    return lambda sc, chunks: verify_subclaim(sc, chunks, scorer)[0]


def make_claude_verifier(model: str = "claude-haiku-4-5-20251001"):
    """Build an Anthropic client and return a (subclaim, chunks) -> bool callable."""
    import anthropic
    client = anthropic.Anthropic()
    return lambda sc, chunks: verify_subclaim_claude(sc, chunks, client, model)
