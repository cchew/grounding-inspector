import json
from grounding.decompose import decompose_output, DECOMPOSE_PROMPT

class FakeClient:
    def __init__(self, payload): self.payload = payload
    def chat(self, model, messages):
        return {"message": {"content": self.payload}}

def test_decompose_parses_claims_and_subclaims():
    payload = json.dumps([
        {"claim": "Medical is covered up to $10m.",
         "subclaims": ["Medical is covered", "limit is $10m"]},
        {"claim": "Excellent value for money.",
         "subclaims": ["policy is excellent value for money"]},
    ])
    claims = decompose_output("ignored", client=FakeClient(payload), model="m")
    assert [c["text"] for c in claims] == ["Medical is covered up to $10m.", "Excellent value for money."]
    assert claims[0]["subclaims"] == ["Medical is covered", "limit is $10m"]

def test_prompt_is_fixed_and_versioned():
    assert "v1" in DECOMPOSE_PROMPT

def test_decompose_claude_raises_value_error_on_empty_content():
    from grounding.decompose import decompose_output_claude

    class FakeMessage:
        content = []

    class FakeMessages:
        def create(self, **kwargs):
            return FakeMessage()

    class FakeClaudeClient:
        messages = FakeMessages()

    import pytest
    with pytest.raises(ValueError, match="empty content"):
        decompose_output_claude("ignored", FakeClaudeClient())
