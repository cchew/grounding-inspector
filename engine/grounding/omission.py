import re
import numpy as np

from grounding.omission_embed import Embedder

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "up", "was", "were", "will", "with",
})


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, punctuation stripped, stopwords removed."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def embed_tokens(tokens: list[str], embedder: Embedder) -> np.ndarray:
    """Embeds each token, silently dropping out-of-vocabulary ones (embedder
    returns None). Returns shape (0, 0) if every token was OOV."""
    vectors = [v for tok in tokens if (v := embedder(tok)) is not None]
    if not vectors:
        return np.empty((0, 0))
    return np.vstack(vectors)
