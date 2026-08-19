import pytest

from grounding.comprehensiveness import generate_question


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
