import asyncio
import json

import pytest

pytest.importorskip("inspect_ai")  # this test file needs the ad-hoc install from Step 1

from inspect_ai.model import ModelOutput
from inspect_ai.model._model import ModelName
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

from grounding.metrics import groundedness
import grounding.inspect_scorer as scorer_module


class FakeDecomposeClient:
    """Mirrors engine/tests/test_decompose.py's FakeClient pattern."""

    def __init__(self, payload):
        self.payload = payload

    def chat(self, model, messages):
        return {"message": {"content": self.payload}}


def _build_state(ai_output: str, sections: list[dict]) -> TaskState:
    return TaskState(
        model=ModelName(model="fake/model"),
        sample_id=0,
        epoch=0,
        input=ai_output,
        messages=[],
        output=ModelOutput.from_content(model="fake/model", content=ai_output),
        metadata={"sections": sections},
    )


def test_grounded_claim_scorer_matches_independent_groundedness_call(monkeypatch):
    sections = [{
        "id": "s1", "page": 1, "char_start": 0, "char_end": 54,
        "text": "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.",
    }]
    ai_output = "Cameras are covered for up to $4,000. Laptops are covered for up to $9,000."

    decompose_payload = json.dumps([
        {"claim": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]},
        {"claim": "Laptops are covered for up to $9,000.", "subclaims": ["laptops covered to $9,000"]},
    ])
    monkeypatch.setattr(scorer_module, "build_client", lambda: FakeDecomposeClient(decompose_payload))
    monkeypatch.setattr(scorer_module, "build_scorer", lambda: None)
    # Deterministic stand-in verifier: only the "cameras" subclaim is supported,
    # so claim 1 -> grounded, claim 2 -> unsupported (no evidence for laptops here).
    monkeypatch.setattr(
        scorer_module, "make_minicheck_verifier",
        lambda scorer: (lambda sc, chunks: "cameras" in sc),
    )

    state = _build_state(ai_output, sections)
    scored = scorer_module.grounded_claim_scorer()
    result = asyncio.run(scored(state, Target("")))

    expected = groundedness(["grounded", "unsupported"])
    assert result.value == pytest.approx(expected["score"] / 100)
    assert result.answer == "1/2 grounded"
    assert len(result.metadata["claims"]) == 2
    assert result.metadata["claims"][0]["label"] == "grounded"
    assert result.metadata["claims"][1]["label"] == "unsupported"


def test_grounded_claim_scorer_routes_haiku_verifier_when_requested(monkeypatch):
    sections = [{"id": "s1", "page": 1, "char_start": 0, "char_end": 20, "text": "Anything covered."}]
    monkeypatch.setattr(scorer_module, "build_client", lambda: FakeDecomposeClient(
        json.dumps([{"claim": "A claim.", "subclaims": ["a claim"]}])
    ))
    called = {}
    monkeypatch.setattr(scorer_module, "make_claude_verifier", lambda: called.setdefault("used", True) and (lambda sc, chunks: True))

    state = _build_state("A claim.", sections)
    scored = scorer_module.grounded_claim_scorer(verifier="haiku")
    asyncio.run(scored(state, Target("")))

    assert called.get("used") is True
