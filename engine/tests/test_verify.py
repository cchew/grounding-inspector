from grounding.verify import verify_subclaim, chunk_document

class FakeScorer:
    """Returns support prob keyed by (chunk_text, claim)."""
    def __init__(self, table): self.table = table
    def score(self, docs, claims):
        probs = [self.table.get((d, c), 0.0) for d, c in zip(docs, claims)]
        labels = [1 if p >= 0.5 else 0 for p in probs]
        return labels, probs, None, None

def test_chunking_splits_long_doc():
    chunks = chunk_document("a" * 2500, max_chars=1000)
    assert len(chunks) == 3

def test_supported_in_any_chunk_is_supported():
    # the supporting sentence is only in chunk 2; a top-k retriever might miss it,
    # full-doc max-pool must not.
    doc_chunks = ["irrelevant text", "the limit is $1,000 per item"]
    claim = "limit is $1,000"
    scorer = FakeScorer({(doc_chunks[1], claim): 0.92, (doc_chunks[0], claim): 0.03})
    supported, prob = verify_subclaim(claim, doc_chunks, scorer)
    assert supported is True
    assert prob == 0.92  # max-pooled

def test_unsupported_everywhere_is_unsupported():
    doc_chunks = ["a", "b"]
    claim = "invented coverage"
    scorer = FakeScorer({})
    supported, prob = verify_subclaim(claim, doc_chunks, scorer)
    assert supported is False
