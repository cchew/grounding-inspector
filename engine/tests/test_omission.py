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


from grounding.omission import check_omissions_embedkde


def test_flags_section_semantically_absent_from_output():
    # Mirrors the EmbedKDECheck paper's own worked example (hepatectomy /
    # infection vs. surgery): s1 restates what the output already says,
    # s2 introduces content the output never mentions.
    embedder = FakeEmbedder({
        "patient": np.array([0.1, 0.1]),
        "underwent": np.array([-0.1, 0.1]),
        "surgery": np.array([0.0, 0.0]),
        "showed": np.array([0.1, -0.1]),
        "hepatectomy": np.array([10.0, 10.0]),
        "postoperative": np.array([10.1, 10.1]),
        "infection": np.array([10.0, 10.2]),
    })
    sections = [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "patient underwent surgery"},
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 0, "text": "hepatectomy showed postoperative infection"},
    ]
    ai_output = "patient underwent surgery and showed no infection"

    result = check_omissions_embedkde(
        sections, ai_output, embedder, pca_components=2, kde_bandwidth=1.0, threshold_std=0.5,
    )

    assert result["method"] == "embedkde"
    assert result["validated"] is False
    assert "unvalidated" in result["caveat"].lower()
    flagged_ids = [f["section_id"] for f in result["flagged_sections"]]
    assert "s2" in flagged_ids
    assert "s1" not in flagged_ids
    s2 = next(f for f in result["flagged_sections"] if f["section_id"] == "s2")
    assert set(s2["top_tokens"]) & {"hepatectomy", "postoperative", "infection"}


def test_no_flags_when_all_scores_identical():
    # Every token maps to the exact same vector, so every section's
    # aggregated score comes out identical (std=0 across sections) and
    # nothing gets flagged. Note: this does NOT isolate the `std > 0` guard
    # as a distinct branch -- when std==0, mean equals every score exactly,
    # so `score > mean + threshold_std * std` already reduces to
    # `score > score` (always False) with or without the guard. The guard
    # is provably redundant for this case; see the fix report appended
    # 2026-08-18 for the reasoning. This test verifies the observable
    # behavior (uniform scores -> no flags), not the guard's necessity.
    same_vec = np.array([0.0, 0.0])
    embedder = FakeEmbedder({"cat": same_vec, "dog": same_vec, "bird": same_vec})
    sections = [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "cat"},
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 0, "text": "dog"},
    ]
    result = check_omissions_embedkde(sections, "bird", embedder, pca_components=1, kde_bandwidth=1.0)
    assert result["flagged_sections"] == []


def test_top_tokens_align_with_scores_when_section_has_oov_token():
    # An OOV token ("oovword") sits between two in-vocabulary tokens in s1's
    # text. embed_tokens/_embed_with_survivors silently drops it, so the
    # embedding/score array has only 2 rows for a 3-token section. Reported
    # top_tokens must be derived from the surviving-token list (index-aligned
    # with scores), not the raw, uncompacted tokenize() output -- otherwise
    # the dropped OOV token can appear in top_tokens and the true top scorer
    # can be shifted out.
    embedder = FakeEmbedder({
        "output": np.array([0.0, 0.0]),
        "word": np.array([0.1, 0.1]),
        "alpha": np.array([0.0, 0.1]),
        "beta": np.array([0.1, 0.0]),
        "zulu": np.array([10.0, 10.0]),
    })
    sections = [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "alpha oovword zulu"},
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 0, "text": "beta output"},
    ]
    ai_output = "output word"

    result = check_omissions_embedkde(
        sections, ai_output, embedder, pca_components=2, kde_bandwidth=1.0, threshold_std=0.5,
    )

    flagged_ids = [f["section_id"] for f in result["flagged_sections"]]
    assert "s1" in flagged_ids
    s1 = next(f for f in result["flagged_sections"] if f["section_id"] == "s1")
    assert "oovword" not in s1["top_tokens"]
    assert s1["top_tokens"][0] == "zulu"  # true highest scorer, not shifted by the dropped OOV token
