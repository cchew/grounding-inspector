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
