# engine/tests/test_validate.py
from grounding.validate import map_ragtruth_label, summarise

def test_label_mapping():
    assert map_ragtruth_label({"labels": []}) == 0          # no hallucination span -> grounded(0)
    assert map_ragtruth_label({"labels": [{"start": 1}]}) == 1  # has hallucination -> 1

def test_summarise_computes_recall_and_kappa():
    gold = [1, 1, 0, 0, 1]
    pred = [1, 0, 0, 0, 1]   # missed one hallucination
    m = summarise(gold, pred)
    assert m["false_negatives"] == 1
    assert m["n_positive"] == 3
    assert 0.0 <= m["recall"] <= 1.0
    assert "recall_ci" in m and "cohen_kappa" in m and "balanced_accuracy" in m
