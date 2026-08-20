import json
import pytest

from grounding.comprehensiveness import (
    generate_question,
    judge_coverage,
    decompose_source_section,
    check_omissions_comprehensiveness_qa,
)


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


def test_judge_coverage_raises_truncation_error_on_max_tokens_stop():
    # A truncated response is unparseable JSON. The generic "could not parse"
    # message sent the reader hunting the wrong cause; stop_reason names it.
    class TruncatedMessage:
        content = [type("C", (), {"text": '{"status": "COVERED", "evidence": "a very long quoted'})()]
        stop_reason = "max_tokens"

    class TruncatedMessages:
        def create(self, **kwargs):
            return TruncatedMessage()

    class TruncatedClient:
        messages = TruncatedMessages()

    with pytest.raises(ValueError, match="truncated"):
        judge_coverage("q", "fact", "output", TruncatedClient(), model="m")


def test_judge_coverage_raises_on_unexpected_status():
    client = FakeClaudeClient([json.dumps({"status": "MAYBE", "evidence": None})])
    with pytest.raises(ValueError, match="unexpected status"):
        judge_coverage("q", "fact", "output", client, model="m")


def test_judge_coverage_raises_on_non_string_evidence():
    client = FakeClaudeClient([json.dumps({"status": "OMITTED", "evidence": ["not", "a", "string"]})])
    with pytest.raises(ValueError, match="evidence must be a string or null"):
        judge_coverage("q", "fact", "output", client, model="m")


def test_judge_coverage_raises_on_numeric_evidence():
    client = FakeClaudeClient([json.dumps({"status": "COVERED", "evidence": 42})])
    with pytest.raises(ValueError, match="evidence must be a string or null"):
        judge_coverage("q", "fact", "output", client, model="m")


def test_decompose_source_section_delegates_to_decompose_output_claude():
    payload = json.dumps([{"claim": "policy covers X", "subclaims": ["covers X"]}])
    client = FakeClaudeClient([payload])
    result = decompose_source_section("policy covers X", client, model="m")
    assert result == [{"text": "policy covers X", "subclaims": ["covers X"]}]


def test_check_omissions_raises_without_allow_llm_calls():
    client = FakeClaudeClient([])
    with pytest.raises(ValueError, match="allow_llm_calls"):
        check_omissions_comprehensiveness_qa([], "output", client)
    assert client.messages.responses == []  # never touched -- structural guard, not just a default


def test_check_omissions_flags_section_with_omitted_fact():
    sections = [{"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "policy excludes pre-existing conditions"}]
    responses = [
        json.dumps([{"claim": "policy excludes pre-existing conditions", "subclaims": ["excludes pre-existing conditions"]}]),
        "Does the output mention pre-existing conditions?",
        json.dumps({"status": "OMITTED", "evidence": None}),
    ]
    client = FakeClaudeClient(responses)
    result = check_omissions_comprehensiveness_qa(sections, "irrelevant output", client, allow_llm_calls=True)
    assert result["method"] == "comprehensiveness_qa"
    assert result["validated"] is False
    flagged_ids = [f["section_id"] for f in result["flagged_sections"]]
    assert "s1" in flagged_ids
    s1 = next(f for f in result["flagged_sections"] if f["section_id"] == "s1")
    assert s1["omitted_facts"][0]["fact"] == "excludes pre-existing conditions"
    assert s1["omitted_facts"][0]["question"] == "Does the output mention pre-existing conditions?"


def test_check_omissions_does_not_flag_fully_covered_section():
    sections = [{"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "policy covers medical"}]
    responses = [
        json.dumps([{"claim": "policy covers medical", "subclaims": ["covers medical"]}]),
        "Does the output mention medical cover?",
        json.dumps({"status": "COVERED", "evidence": "medical is covered"}),
    ]
    client = FakeClaudeClient(responses)
    result = check_omissions_comprehensiveness_qa(sections, "medical is covered", client, allow_llm_calls=True)
    assert result["flagged_sections"] == []
    assert result["global_score"] == 0.0


def test_check_omissions_section_with_no_subclaims_is_never_flagged():
    sections = [{"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": ""}]
    responses = [json.dumps([])]  # decompose returns zero claims
    client = FakeClaudeClient(responses)
    result = check_omissions_comprehensiveness_qa(sections, "output", client, allow_llm_calls=True)
    assert result["flagged_sections"] == []
    assert result["global_score"] == 0.0


def test_check_omissions_multi_subclaim_partial_omission_score():
    sections = [{"id": "s1", "page": 1, "char_start": 0, "char_end": 0, "text": "two facts here"}]
    responses = [
        json.dumps([{"claim": "two facts here", "subclaims": ["fact A", "fact B"]}]),
        "Q about A?", json.dumps({"status": "COVERED", "evidence": "A is here"}),
        "Q about B?", json.dumps({"status": "OMITTED", "evidence": None}),
    ]
    client = FakeClaudeClient(responses)
    result = check_omissions_comprehensiveness_qa(sections, "A is here", client, allow_llm_calls=True)
    s1 = result["flagged_sections"][0]
    assert s1["score"] == 0.5
    assert len(s1["omitted_facts"]) == 1
    assert s1["omitted_facts"][0]["fact"] == "fact B"


def test_check_omissions_hyperparameters_record_single_model_key():
    result = check_omissions_comprehensiveness_qa([], "output", FakeClaudeClient([]), allow_llm_calls=True, model="test-model")
    assert result["hyperparameters"] == {"model": "test-model", "flag_threshold": 0.0}
