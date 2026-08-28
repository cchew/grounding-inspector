import json

import pytest

from grounding.live import CheckTooComplex, MAX_CLAIMS, run_live_check

SECTIONS = [
    {"id": "s1", "page": 1, "char_start": 0, "char_end": 40, "text": "Medical expenses covered up to $10,000."},
]


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeContentBlock(text)]


class FakeMessages:
    def __init__(self, decompose_response, verify_responses):
        self.decompose_response = decompose_response
        self.verify_responses = list(verify_responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeMessage(self.decompose_response)
        return FakeMessage(self.verify_responses.pop(0))


class FakeClient:
    def __init__(self, decompose_response, verify_responses):
        self.messages = FakeMessages(decompose_response, verify_responses)


def test_run_live_check_returns_claims_and_groundedness_no_scorecard():
    decompose_json = json.dumps([
        {"claim": "Medical is covered up to $10,000.", "subclaims": ["medical covered to $10,000"]},
    ])
    client = FakeClient(decompose_json, ["SUPPORTED"])
    result = run_live_check("Medical is covered up to $10,000.", SECTIONS, client)
    assert result["claims"][0]["label"] == "grounded"
    assert result["groundedness"]["n_grounded"] == 1
    assert "scorecard" not in result
    assert result["verifier_model"] == "claude-haiku-4-5-20251001"
    assert result["ai_output"] == "Medical is covered up to $10,000."
    assert result["source"]["sections"] == SECTIONS


def test_run_live_check_unsupported_subclaim_yields_unsupported_label():
    decompose_json = json.dumps([
        {"claim": "Dental is fully covered.", "subclaims": ["dental fully covered"]},
    ])
    client = FakeClient(decompose_json, ["UNSUPPORTED"])
    result = run_live_check("Dental is fully covered.", SECTIONS, client)
    assert result["claims"][0]["label"] == "unsupported"


def test_run_live_check_uses_custom_verifier_model():
    decompose_json = json.dumps([{"claim": "x", "subclaims": ["x"]}])
    client = FakeClient(decompose_json, ["SUPPORTED"])
    result = run_live_check("x", SECTIONS, client, verifier_model="claude-opus-4")
    assert result["verifier_model"] == "claude-opus-4"
    assert client.messages.calls[1]["model"] == "claude-opus-4"


def test_run_live_check_rejects_too_many_claims():
    many = json.dumps([{"claim": f"c{i}", "subclaims": ["s"]} for i in range(MAX_CLAIMS + 1)])
    client = FakeClient(many, ["SUPPORTED"] * (MAX_CLAIMS + 1))
    with pytest.raises(CheckTooComplex):
        run_live_check("x", SECTIONS, client)


def test_run_live_check_rejects_too_many_subclaims():
    # few claims, but a combined subclaim count over the verifier-call cap
    payload = json.dumps([{"claim": "c", "subclaims": ["s"] * 200}])
    client = FakeClient(payload, ["SUPPORTED"] * 200)
    with pytest.raises(CheckTooComplex):
        run_live_check("x", SECTIONS, client)


def test_run_live_check_rejects_a_context_budget_blowout():
    # Under both count caps (1 claim, 30 subclaims < MAX_VERIFIER_CALLS) but
    # the document is re-sent as context on every verify call, so
    # chars x subclaims is what actually drives cost.
    from grounding.live import MAX_CONTEXT_CHAR_BUDGET, MAX_VERIFIER_CALLS

    n_sub = 30
    assert n_sub <= MAX_VERIFIER_CALLS
    doc_chars = MAX_CONTEXT_CHAR_BUDGET // n_sub + 1000
    big_sections = [{"id": "s1", "page": 1, "char_start": 0,
                     "char_end": doc_chars, "text": "x" * doc_chars}]
    payload = json.dumps([{"claim": "c", "subclaims": [f"s{i}" for i in range(n_sub)]}])
    client = FakeClient(payload, ["SUPPORTED"] * n_sub)
    with pytest.raises(CheckTooComplex):
        run_live_check("x", big_sections, client)


def test_run_live_check_allows_a_document_within_the_context_budget():
    from grounding.live import MAX_CONTEXT_CHAR_BUDGET

    n_sub = 2
    doc_chars = MAX_CONTEXT_CHAR_BUDGET // n_sub - 1000
    sections = [{"id": "s1", "page": 1, "char_start": 0,
                 "char_end": doc_chars, "text": "x" * doc_chars}]
    payload = json.dumps([{"claim": "c", "subclaims": ["s1", "s2"]}])
    client = FakeClient(payload, ["SUPPORTED", "SUPPORTED"])
    result = run_live_check("x", sections, client)
    assert result["claims"][0]["label"] == "grounded"


def test_run_live_check_allows_a_normal_size_check():
    payload = json.dumps([{"claim": "c", "subclaims": ["s1", "s2"]}])
    client = FakeClient(payload, ["SUPPORTED", "SUPPORTED"])
    result = run_live_check("x", SECTIONS, client)
    assert result["claims"][0]["label"] == "grounded"


def test_run_live_check_joins_sections_with_a_blank_line(monkeypatch):
    captured = {}

    def fake_label_claims(decomposed, full_text, sections, verifier_fn, **kwargs):
        captured["full_text"] = full_text
        return []

    monkeypatch.setattr("grounding.live.label_claims", fake_label_claims)
    monkeypatch.setattr("grounding.live.decompose_output_claude", lambda ai, client: [])

    run_live_check("ai", [{"text": "Alpha section."}, {"text": "Beta section."}], client=object())
    assert captured["full_text"] == "Alpha section.\n\nBeta section."
