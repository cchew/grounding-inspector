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
    """Lowercase word tokens, punctuation stripped, stopwords and bare
    numbers removed.

    Pure-digit tokens are dropped: the regex splits a formatted figure like
    "$1,000" into "1" and "000", and those fragments sit far from every
    content word in FastText space, so they dominate the OM score as
    meaningless outliers. Numeric claims are already checked deterministically
    by grounding.numeric_check, which is the right tool for that job.
    Mixed alphanumerics ("10am", "item10") are kept -- they carry lexical
    meaning a pure digit run does not.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and not w.isdigit()]


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


_CAVEAT = (
    "Omission signals are unvalidated: no ground-truth omission labels exist for "
    "these fixtures, and detection hyperparameters (PCA components, KDE bandwidth, "
    "per-document threshold) are unadjusted defaults, not calibrated against labeled "
    "data. Treat a flagged span as a prompt to review the source directly, not a finding."
)


def _embed_with_survivors(tokens: list[str], embedder: Embedder) -> tuple[list[str], np.ndarray]:
    """Like embed_tokens, but also returns the surviving (non-OOV) tokens in
    the same order as the embedding rows. embed_tokens silently drops OOV
    tokens, which otherwise misaligns any score index derived from its output
    against the original, uncompacted token list -- this keeps token and
    score indices in lockstep."""
    survivors = [tok for tok in tokens if embedder(tok) is not None]
    if not survivors:
        return survivors, np.empty((0, 0))
    return survivors, np.vstack([embedder(tok) for tok in survivors])


def check_omissions_embedkde(
    source_sections: list[dict], ai_output: str, embedder: Embedder,
    pca_components: int = 16, kde_bandwidth: float = 1.0, threshold_std: float = 1.5,
) -> dict:
    """Tokenizes+embeds the ai_output once, then each source section
    separately, computing per-token OM scores via compute_om_scores() and
    aggregating to section-level (max token score per section -- same
    aggregation the paper uses for its single whole-document global score,
    applied per-section here). Flags sections scoring more than
    threshold_std standard deviations above this document's own mean
    section score -- a self-relative threshold, not an absolute magnitude,
    because OM_score has no calibrated absolute scale without labeled data
    (the paper's own absolute threshold came from random search against
    ground truth GI doesn't have).
    """
    output_tokens = tokenize(ai_output)
    output_emb = embed_tokens(output_tokens, embedder)

    # (section_id, score, top_tokens, scored) -- `scored` is False for
    # "no data" sentinels (section or output had no in-vocabulary tokens).
    # A sentinel's 0.0 is a placeholder, not a measurement of "perfectly
    # represented", so it must never enter the distribution the threshold
    # is derived from, and it can never itself be flagged.
    section_results: list[tuple[str, float, list[str], bool]] = []
    for section in source_sections:
        tokens = tokenize(section["text"])
        surviving_tokens, source_emb = _embed_with_survivors(tokens, embedder)
        if source_emb.shape[0] == 0 or output_emb.shape[0] == 0:
            section_results.append((section["id"], 0.0, [], False))
            continue
        scores = compute_om_scores(source_emb, output_emb, pca_components, kde_bandwidth)
        top_idx = np.argsort(scores)[::-1][:3]
        top_tokens = [surviving_tokens[i] for i in top_idx]
        section_results.append((section["id"], float(scores.max()), top_tokens, True))

    real_scores = np.array([s for _, s, _, scored in section_results if scored])
    if real_scores.size:
        mean, std = float(real_scores.mean()), float(real_scores.std())
        global_score = float(real_scores.max())
    else:
        mean = std = global_score = 0.0
    flagged = [
        {"section_id": sid, "score": score, "top_tokens": tokens}
        for sid, score, tokens, scored in section_results
        if scored and std > 0 and score > mean + threshold_std * std
    ]

    return {
        "method": "embedkde",
        "global_score": global_score,
        "flagged_sections": flagged,
        "hyperparameters": {
            "pca_components": pca_components,
            "kde_bandwidth": kde_bandwidth,
            "threshold_std": threshold_std,
        },
        "validated": False,
        "caveat": _CAVEAT,
    }
