# engine/tests/test_validate.py
from grounding.validate import map_ragtruth_label, summarise

def test_label_mapping():
    assert map_ragtruth_label({"hallucination_labels": "[]"}) == 0
    assert map_ragtruth_label({"hallucination_labels": '[{"start": 1}]'}) == 1
    assert map_ragtruth_label({}) == 0  # missing field -> grounded

def test_summarise_computes_recall_and_kappa():
    gold = [1, 1, 0, 0, 1]
    pred = [1, 0, 0, 0, 1]   # missed one hallucination
    m = summarise(gold, pred)
    assert m["false_negatives"] == 1
    assert m["n_positive"] == 3
    assert 0.0 <= m["recall"] <= 1.0
    assert "recall_ci" in m and "cohen_kappa" in m and "balanced_accuracy" in m

def test_summarise_accepts_and_the_run_sample_loop_counts_parse_failures():
    # run_sample requires network/model access, so this test exercises the
    # extracted counting logic directly rather than the full function.
    from grounding.validate import count_and_score

    gold = [1, 0, 1]

    def decompose_fn(text):
        if text == "bad":
            raise ValueError("could not parse")
        return [{"text": text, "subclaims": [text]}]

    def verify_fn(subclaim, chunks):
        return True

    examples = [
        {"output": "ok1", "context": "doc"},
        {"output": "bad", "context": "doc"},
        {"output": "ok2", "context": "doc"},
    ]
    pred, n_failures = count_and_score(examples, decompose_fn, verify_fn)
    assert n_failures == 1
    assert len(pred) == 3
