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

def test_build_claude_client_reads_key_from_repo_dotenv(tmp_path, monkeypatch):
    # The billed comprehensiveness_qa path fails at auth if the client only
    # reads an exported shell variable -- the README documents engine/.env and
    # repo/.env, and only pilot_claude.py used to load them.
    import pathlib
    from grounding import decompose

    # setenv-then-delenv so monkeypatch records the pre-test state and its
    # teardown clears the key load_dotenv is about to inject into os.environ.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "tracked-placeholder")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    fake_repo = tmp_path / "repo"
    (fake_repo / "engine" / "grounding").mkdir(parents=True)
    (fake_repo / ".env").write_text("ANTHROPIC_API_KEY=sk-ant-from-dotenv\n")
    monkeypatch.setattr(decompose, "__file__", str(fake_repo / "engine" / "grounding" / "decompose.py"))

    client = decompose.build_claude_client()
    assert client.api_key == "sk-ant-from-dotenv"
    assert pathlib.Path(fake_repo / ".env").exists()


def test_build_claude_client_prefers_exported_key_over_dotenv(monkeypatch):
    from grounding.decompose import build_claude_client

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-exported")
    assert build_claude_client().api_key == "sk-ant-exported"


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
