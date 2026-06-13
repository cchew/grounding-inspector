from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score
from grounding.metrics import recall_with_ci


def map_ragtruth_label(example: dict) -> int:
    """1 = contains hallucination (positive/ungrounded), 0 = grounded."""
    return 1 if example.get("labels") else 0


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


def run_sample(n: int = 300, seed: int = 0):
    """Integration: load a stratified RAGTruth sample, run verify over each,
    return summarise(gold, pred). Kept thin; called from the notebook."""
    from datasets import load_dataset
    from grounding.verify import build_scorer, verify_subclaim, chunk_document
    ds = load_dataset("wandb/RAGTruth-processed", split="test").shuffle(seed=seed).select(range(n))
    scorer = build_scorer()
    gold, pred = [], []
    for ex in ds:
        gold.append(map_ragtruth_label(ex))
        supported, _ = verify_subclaim(ex["response"], chunk_document(ex["prompt"]), scorer)
        pred.append(0 if supported else 1)  # unsupported -> hallucination(1)
    return summarise(gold, pred)
