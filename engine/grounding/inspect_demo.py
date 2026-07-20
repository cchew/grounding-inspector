import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput
from inspect_ai.solver import Generate, TaskState, solver

from grounding.inspect_scorer import grounded_claim_scorer

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
FIXTURE_IDS = ["travel-pds-01", "travel-pds-02", "travel-pds-03", "covermore-pds-01", "budgetdirect-pds-01"]


def _load_samples() -> list[Sample]:
    samples = []
    for fixture_id in FIXTURE_IDS:
        fixture = json.loads((FIXTURES_DIR / f"{fixture_id}.json").read_text())
        samples.append(Sample(
            input=fixture["ai_output"],
            target="",
            metadata={"sections": fixture["source"]["sections"]},
        ))
    return samples


@solver
def replay_fixture_output():
    """Copies the fixture's precomputed ai_output into state.output -- no
    live model call. GI's fixtures are precomputed offline; this solver
    exists only to satisfy Inspect's solver -> scorer flow honestly, rather
    than pretending a model generated this text during the eval run."""
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.output = ModelOutput.from_content(model="fixture-replay", content=state.input_text)
        return state

    return solve


@task
def grounding_inspector_demo() -> Task:
    return Task(
        dataset=_load_samples(),
        solver=replay_fixture_output(),
        scorer=grounded_claim_scorer(),
    )
