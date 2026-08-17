from typing import Callable
import numpy as np

Embedder = Callable[[str], "np.ndarray | None"]


def make_fasttext_embedder(model_name: str = "fasttext-wiki-news-subwords-300") -> Embedder:
    """Loads a pretrained general-English FastText model via gensim -- no
    fine-tuning (GI's fixture corpus is far too small to fine-tune anything,
    see spec Non-goals). Returns a bare callable, mirroring verify.py's
    verifier_fn convention: token -> embedding vector, or None for
    out-of-vocabulary tokens (callers drop these, never treat as zero).
    """
    import gensim.downloader
    model = gensim.downloader.load(model_name)

    def embed(token: str) -> "np.ndarray | None":
        return model[token] if token in model.key_to_index else None

    return embed
