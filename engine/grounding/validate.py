import json as _json
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score
from grounding.metrics import recall_with_ci


def map_ragtruth_label(example: dict) -> int:
    """1 = contains hallucination (positive/ungrounded), 0 = grounded.
    RAGTruth field: hallucination_labels — a JSON-encoded list of span dicts."""
    raw = example.get("hallucination_labels", "[]")
    try:
        return 1 if _json.loads(raw) else 0
    except (_json.JSONDecodeError, TypeError):
        return 0


def summarise(gold: list[int], pred: list[int]) -> dict:
    tp = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 1)
    fn = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 0)
    recall, ci = recall_with_ci(tp, fn)
    return {
        "recall": round(recall, 3), "recall_ci": [round(ci[0], 3), round(ci[1], 3)],
        "false_negatives": fn, "n_positive": tp + fn,
        "balanced_accuracy": round(balanced_accuracy_score(gold, pred), 3),
        "cohen_kappa": round(cohen_kappa_score(gold, pred), 3),
    }


def run_sample(
    n: int = 300,
    seed: int = 0,
    decompose_model: str = "qwen2.5:7b-instruct",
    verifier: str = "minicheck",
):
    """Run the full decompose->verify pipeline on a RAGTruth sample.

    verifier: "minicheck" (local, default) | "haiku" (Claude Haiku, requires ANTHROPIC_API_KEY)
    """
    from datasets import load_dataset
    from grounding.verify import chunk_document, make_minicheck_verifier, make_claude_verifier
    from grounding.decompose import decompose_output, build_client, decompose_output_claude, build_claude_client

    ds = load_dataset("wandb/RAGTruth-processed", split="test").shuffle(seed=seed).select(range(n))

    if verifier == "minicheck":
        from grounding.verify import build_scorer
        scorer = build_scorer()
        verify_fn = make_minicheck_verifier(scorer)
        ollama_client = build_client()
        _model = decompose_model
        decompose_fn = lambda text: decompose_output(text, ollama_client, _model)
    elif verifier == "haiku":
        claude_client = build_claude_client()
        verify_fn = make_claude_verifier()
        decompose_fn = lambda text: decompose_output_claude(text, claude_client)
    else:
        raise ValueError(f"Unknown verifier '{verifier}'. Choose 'minicheck' or 'haiku'.")

    gold, pred = [], []
    for ex in ds:
        gold.append(map_ragtruth_label(ex))
        chunks = chunk_document(ex["context"])
        try:
            claims = decompose_fn(ex["output"])
            subclaims = [sc for c in claims for sc in c["subclaims"]]
            if not subclaims:
                subclaims = [ex["output"]]
            supported = [verify_fn(sc, chunks) for sc in subclaims]
            pred.append(0 if all(supported) else 1)
        except (ValueError, KeyError):
            pred.append(0)
    return summarise(gold, pred)
