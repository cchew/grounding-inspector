import asyncio

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai.model import ModelOutput
from inspect_ai.model._model import ModelName
from inspect_ai.solver import TaskState

from grounding.inspect_demo import FIXTURE_IDS, _load_samples, replay_fixture_output


def test_load_samples_returns_one_per_fixture():
    samples = _load_samples()
    assert len(samples) == len(FIXTURE_IDS) == 5


def test_each_sample_carries_nonempty_input_and_sections():
    for sample in _load_samples():
        assert isinstance(sample.input, str) and len(sample.input) > 0
        assert "sections" in sample.metadata
        assert len(sample.metadata["sections"]) > 0


def test_replay_fixture_output_copies_input_without_calling_generate():
    state = TaskState(
        model=ModelName(model="fake/model"), sample_id=0, epoch=0,
        input="claim text here", messages=[],
        output=ModelOutput.from_content(model="fake/model", content=""),
    )

    async def fake_generate(state):
        raise AssertionError("replay solver must not call generate() -- no live model call")

    result = asyncio.run(replay_fixture_output()(state, fake_generate))
    assert result.output.completion == "claim text here"
