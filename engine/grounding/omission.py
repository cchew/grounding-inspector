import re
import numpy as np
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity

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


def compute_om_scores(
    source_token_emb: np.ndarray, output_token_emb: np.ndarray,
    pca_components: int = 16, kde_bandwidth: float = 1.0,
) -> np.ndarray:
    """PCA-reduce both embedding sets, fit only on the output (source is only
    ever transformed, never fit) -- this build's own design choice, made to
    keep dimensionality reduction and density estimation anchored to the
    same reference distribution (the paper is explicit that the KDE itself
    is fit on the output only; its own PCA step is ambiguous on this point).
    Fits a Gaussian KDE on the reduced output embeddings, then scores each
    source token: OM_score = min_density_over_output / density(token) -- a
    source token whose embedding falls in a low-density region of the
    output's learned distribution scores high (semantically distant from
    anything the output actually said).

    pca_components is capped to the available sample/feature count -- GI's
    fixture corpus is tiny (single-digit sections per document), so the
    default of 16 would otherwise raise inside sklearn on any small doc.

    Unvalidated defaults (16 components, bandwidth=1.0): no labeled data
    exists to tune these against. See spec Background.
    """
    n_components = min(pca_components, output_token_emb.shape[0], output_token_emb.shape[1])
    pca = PCA(n_components=n_components)
    output_reduced = pca.fit_transform(output_token_emb)
    source_reduced = pca.transform(source_token_emb)

    kde = KernelDensity(kernel="gaussian", bandwidth=kde_bandwidth)
    kde.fit(output_reduced)

    output_density = np.exp(kde.score_samples(output_reduced))
    min_output_density = output_density.min()

    source_density = np.exp(kde.score_samples(source_reduced))
    source_density = np.clip(source_density, a_min=1e-300, a_max=None)  # avoid div-by-zero

    return min_output_density / source_density
