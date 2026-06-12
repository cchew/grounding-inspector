import math
from grounding.metrics import groundedness, recall_with_ci

def test_groundedness_triple_and_score():
    g = groundedness(["grounded", "grounded", "partial", "unsupported"])
    assert (g["n_grounded"], g["n_partial"], g["n_unsupported"]) == (2, 1, 1)
    # weighted: (1 + 1 + 0.5 + 0) / 4 = 0.625 -> 63
    assert g["score"] == 63

def test_recall_perfect():
    r, (lo, hi) = recall_with_ci(tp=40, fn=0)
    assert r == 1.0
    assert hi == 1.0
    assert lo < 1.0  # exact CI has a lower bound below 1 even at 0 misses

def test_recall_clopper_pearson_known_value():
    # 8/10 -> Clopper-Pearson 95% CI approx [0.444, 0.975]
    r, (lo, hi) = recall_with_ci(tp=8, fn=2)
    assert r == 0.8
    assert math.isclose(lo, 0.4439, abs_tol=1e-3)
    assert math.isclose(hi, 0.9748, abs_tol=1e-3)
