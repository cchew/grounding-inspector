import json
import pytest

from grounding.comprehensiveness import generate_question, judge_coverage


class FakeMessage:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)

    def create(self, **kwargs):
        return FakeMessage(self.responses.pop(0))


class FakeClaudeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def test_generate_question_returns_stripped_text():
    client = FakeClaudeClient(["  Does the policy cover pre-existing conditions?  "])
    q = generate_question("policy excludes pre-existing conditions", client, model="m")
    assert q == "Does the policy cover pre-existing conditions?"


def test_generate_question_raises_on_empty_content():
    client = FakeClaudeClient([])

    class EmptyMessage:
        content = []

    class EmptyMessages:
        def create(self, **kwargs):
            return EmptyMessage()

    class EmptyClient:
        messages = EmptyMessages()

    with pytest.raises(ValueError, match="empty content"):
        generate_question("fact", EmptyClient(), model="m")


def test_judge_coverage_parses_covered_status():
    client = FakeClaudeClient([json.dumps({"status": "COVERED", "evidence": "the policy covers X"})])
    result = judge_coverage("does it cover X?", "policy covers X", "the policy covers X", client, model="m")
    assert result == {"status": "COVERED", "evidence": "the policy covers X"}


def test_judge_coverage_parses_omitted_status_with_null_evidence():
    client = FakeClaudeClient([json.dumps({"status": "OMITTED", "evidence": None})])
    result = judge_coverage("does it cover Y?", "policy covers Y", "unrelated output text", client, model="m")
    assert result == {"status": "OMITTED", "evidence": None}


def test_judge_coverage_strips_markdown_fence():
    fenced = "```json\n" + json.dumps({"status": "COVERED", "evidence": "x"}) + "\n```"
    client = FakeClaudeClient([fenced])
    result = judge_coverage("q", "fact", "output", client, model="m")
    assert result["status"] == "COVERED"


def test_judge_coverage_raises_on_malformed_json():
    client = FakeClaudeClient(["not json"])
    with pytest.raises(ValueError, match="could not parse"):
        judge_coverage("q", "fact", "output", client, model="m")


def test_judge_coverage_raises_on_unexpected_status():
    client = FakeClaudeClient([json.dumps({"status": "MAYBE", "evidence": None})])
    with pytest.raises(ValueError, match="unexpected status"):
        judge_coverage("q", "fact", "output", client, model="m")
