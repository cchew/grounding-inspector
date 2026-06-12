from grounding.metrics import groundedness
from grounding.schema import validate_fixture

def build_fixture(fixture_id: str, source: dict, ai_output: str,
                  claims: list[dict], scorecard: dict) -> dict:
    fixture = {
        "fixture_id": fixture_id,
        "source": source,
        "ai_output": ai_output,
        "claims": claims,
        "groundedness": groundedness([c["label"] for c in claims]),
        "scorecard": scorecard,
    }
    validate_fixture(fixture)  # fail loudly before write (spec error-handling)
    return fixture
