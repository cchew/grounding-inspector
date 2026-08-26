import json

from grounding.live import run_live_check

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
