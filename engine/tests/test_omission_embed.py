import numpy as np
from grounding.omission_embed import make_fasttext_embedder


class FakeGensimModel:
    """Stands in for a gensim KeyedVectors model without downloading one."""
    def __init__(self, table: dict[str, np.ndarray]):
        self.key_to_index = table

    def __getitem__(self, token: str) -> np.ndarray:
        return self.key_to_index[token]


def test_returns_vector_for_known_token(monkeypatch):
    fake_model = FakeGensimModel({"insurance": np.array([1.0, 2.0])})
    monkeypatch.setattr("gensim.downloader.load", lambda name: fake_model)
    embed = make_fasttext_embedder()
    result = embed("insurance")
    assert result is not None
    np.testing.assert_array_equal(result, np.array([1.0, 2.0]))


def test_returns_none_for_oov_token(monkeypatch):
    fake_model = FakeGensimModel({"insurance": np.array([1.0, 2.0])})
    monkeypatch.setattr("gensim.downloader.load", lambda name: fake_model)
    embed = make_fasttext_embedder()
    assert embed("zzzxyznotarealword") is None
