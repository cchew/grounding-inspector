import numpy as np
from grounding.omission import tokenize, embed_tokens


class FakeEmbedder:
    """Dict-keyed lookup, mirrors test_verify.py's FakeScorer. Returns None
    for tokens not in the table (out-of-vocabulary), never a zero vector."""
    def __init__(self, table: dict[str, np.ndarray]):
        self.table = table

    def __call__(self, token: str) -> "np.ndarray | None":
        return self.table.get(token)


def test_tokenize_lowercases_strips_punctuation_and_drops_stopwords():
    tokens = tokenize("Overseas medical expenses ARE covered, up to $10,000,000.")
    assert "are" not in tokens          # stopword
    assert "up" not in tokens           # stopword
    assert "to" not in tokens           # stopword
    assert "overseas" in tokens
    assert "medical" in tokens
    assert "expenses" in tokens
    assert "covered" in tokens


def test_embed_tokens_drops_oov_silently():
    embedder = FakeEmbedder({"insurance": np.array([1.0, 0.0])})
    result = embed_tokens(["insurance", "zzznotaword"], embedder)
    assert result.shape == (1, 2)
    np.testing.assert_array_equal(result[0], np.array([1.0, 0.0]))


def test_embed_tokens_all_oov_returns_empty_array():
    embedder = FakeEmbedder({})
    result = embed_tokens(["zzznotaword"], embedder)
    assert result.shape == (0, 0)


from grounding.omission import compute_om_scores


def test_source_token_far_from_output_cluster_scores_higher():
    # Output embeddings form a tight cluster near the origin.
    output_emb = np.array([
        [0.0, 0.0], [0.1, 0.1], [-0.1, 0.1], [0.1, -0.1], [-0.1, -0.1],
    ])
    # First source token sits inside the cluster (in-distribution);
    # second sits far outside it (should read as a likely omission).
    source_emb = np.array([[0.0, 0.0], [10.0, 10.0]])
    scores = compute_om_scores(source_emb, output_emb, pca_components=2, kde_bandwidth=1.0)
    assert scores.shape == (2,)
    assert scores[1] > scores[0]


def test_pca_components_capped_to_available_dimensions():
    # Only 2 output tokens / 2 dims -- must not raise even though
    # pca_components defaults to 16 (small-fixture edge case).
    output_emb = np.array([[0.0, 0.0], [0.1, 0.1]])
    source_emb = np.array([[5.0, 5.0]])
    scores = compute_om_scores(source_emb, output_emb, pca_components=16, kde_bandwidth=1.0)
    assert scores.shape == (1,)
