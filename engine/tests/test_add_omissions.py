import json
import numpy as np
from notebook.add_omissions import regenerate_fixture


class FakeEmbedder:
    def __init__(self, table):
        self.table = table

    def __call__(self, token):
        return self.table.get(token)


class FakeMessage:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return FakeMessage(self.responses.pop(0))


class FakeClaudeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


FIXTURE = {
    "fixture_id": "t1",
    "source": {"title": "T", "sections": [
        {"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "alpha bravo"},
    ]},
    "ai_output": "alpha",
    "claims": [],
    "groundedness": {"score": 0, "n_grounded": 0, "n_partial": 0, "n_unsupported": 0},
    "scorecard": {
        "recall": 0, "recall_ci": [0, 0], "false_negatives": 0, "n_positive": 0,
        "citation_precision": None, "cohen_kappa": None, "balanced_accuracy": None,
        "validated_on": "x", "domain_note": "y", "pipeline_commit": "abc", "verifier_model": "m",
        "source_sha256": "0" * 64,
    },
}


def test_default_methods_only_calls_embedkde_never_touches_client():
    embedder = FakeEmbedder({"alpha": np.array([0.0, 0.0])})
    client = FakeClaudeClient([])  # would raise IndexError (empty pop) if ever called
    updated = regenerate_fixture(dict(FIXTURE), ("embedkde",), embedder=embedder, client=client)
    assert [o["method"] for o in updated["omissions"]] == ["embedkde"]
    assert client.messages.calls == 0


def test_comprehensiveness_qa_produces_second_entry():
    embedder = FakeEmbedder({"alpha": np.array([0.0, 0.0])})
    responses = [
        json.dumps([{"claim": "alpha is bravo", "subclaims": ["alpha is bravo"]}]),  # decompose
        "Is alpha bravo?",  # generate_question
        json.dumps({"status": "OMITTED", "evidence": None}),  # judge_coverage
    ]
    client = FakeClaudeClient(responses)
    updated = regenerate_fixture(dict(FIXTURE), ("embedkde", "comprehensiveness_qa"), embedder=embedder, client=client)
    assert [o["method"] for o in updated["omissions"]] == ["embedkde", "comprehensiveness_qa"]


def test_byte_for_byte_guard_holds_with_both_methods():
    embedder = FakeEmbedder({"alpha": np.array([0.0, 0.0])})
    responses = [
        json.dumps([{"claim": "alpha is bravo", "subclaims": ["alpha is bravo"]}]),
        "Is alpha bravo?",
        json.dumps({"status": "COVERED", "evidence": "alpha"}),
    ]
    client = FakeClaudeClient(responses)
    original = dict(FIXTURE)
    updated = regenerate_fixture(dict(FIXTURE), ("embedkde", "comprehensiveness_qa"), embedder=embedder, client=client)
    for key in ("fixture_id", "source", "ai_output", "claims", "groundedness", "scorecard"):
        assert updated[key] == original[key]
