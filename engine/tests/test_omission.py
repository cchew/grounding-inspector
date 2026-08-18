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


def test_tokenize_drops_pure_digit_tokens_but_keeps_mixed_alphanumerics():
    # "$10,000,000" splits into the bare fragments "10"/"000"/"000", which sit
    # far from any content word in embedding space and would otherwise dominate
    # the OM score. Numeric claims are grounding.numeric_check's job.
    tokens = tokenize("covered up to $10,000,000 for item10 from 10am")
    assert "10" not in tokens
    assert "000" not in tokens
    assert not any(t.isdigit() for t in tokens)
    assert "item10" in tokens      # mixed alnum survives
    assert "10am" in tokens        # mixed alnum survives
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


def _sentinel_pollution_fixture():
    """Three real sections at increasing distance from the output cluster,
    plus one all-OOV ("no data") section. Vectors are chosen so that the
    sentinel's 0.0 placeholder, if it were allowed into the mean/std, would
    drag the threshold down far enough to flag s2 as well as s3."""
    embedder = FakeEmbedder({
        # output cluster, tight around the origin
        "alpha": np.array([0.0, 0.0]),
        "bravo": np.array([0.1, 0.1]),
        "charlie": np.array([-0.1, 0.1]),
        "delta": np.array([0.1, -0.1]),
        "echo": np.array([-0.1, -0.1]),
        # source tokens at increasing distance from that cluster
        "near": np.array([0.0, 0.0]),
        "mid": np.array([0.2, 0.2]),
        "far": np.array([0.4, 0.4]),
    })
    real_sections = [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "near"},
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 0, "text": "mid"},
        {"id": "s3", "page": 1, "char_start": 0, "char_end": 0, "text": "far"},
    ]
    sentinel = {"id": "s_nodata", "page": 1, "char_start": 0, "char_end": 0,
                "text": "zzznotaword qqqnotaword"}  # every token OOV -> no data
    ai_output = "alpha bravo charlie delta echo"
    return embedder, real_sections, sentinel, ai_output


def test_sentinel_section_does_not_change_which_real_sections_flag():
    embedder, real_sections, sentinel, ai_output = _sentinel_pollution_fixture()
    kwargs = dict(pca_components=2, kde_bandwidth=1.0, threshold_std=0.5)

    without = check_omissions_embedkde(real_sections, ai_output, embedder, **kwargs)
    with_sentinel = check_omissions_embedkde(
        real_sections + [sentinel], ai_output, embedder, **kwargs,
    )

    flagged_without = [f["section_id"] for f in without["flagged_sections"]]
    flagged_with = [f["section_id"] for f in with_sentinel["flagged_sections"]]

    assert flagged_without == ["s3"]          # guards the fixture itself
    assert flagged_with == flagged_without    # sentinel must not pollute the threshold
    assert "s_nodata" not in flagged_with     # a no-data section is never a finding
    assert with_sentinel["global_score"] == without["global_score"]


def test_all_sections_sentinel_returns_zero_score_and_no_flags():
    # Empty real-score array: mean/std/global_score must default to 0.0
    # rather than producing nan from an empty-array .mean()/.std().
    embedder = FakeEmbedder({"alpha": np.array([0.0, 0.0]), "bravo": np.array([0.1, 0.1])})
    sections = [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "zzznotaword"},
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 0, "text": "qqqnotaword"},
    ]
    result = check_omissions_embedkde(
        sections, "alpha bravo", embedder, pca_components=2, kde_bandwidth=1.0,
    )
    assert result["flagged_sections"] == []
    assert result["global_score"] == 0.0


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
