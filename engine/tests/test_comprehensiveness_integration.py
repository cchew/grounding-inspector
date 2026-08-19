"""
Opt-in integration test: makes REAL Claude API calls (real cost, real
latency). Skipped by default -- run explicitly with:
    RUN_LLM_INTEGRATION_TESTS=1 pytest tests/test_comprehensiveness_integration.py -v
Requires ANTHROPIC_API_KEY to be set. No recall/precision numbers are
asserted here (no ground-truth labels exist) -- this only confirms the
real pipeline runs end-to-end and returns a well-shaped result.
"""
import json
import os
import pathlib
import pytest

from grounding.comprehensiveness import check_omissions_comprehensiveness_qa
from grounding.decompose import build_claude_client

ROOT = pathlib.Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LLM_INTEGRATION_TESTS"),
    reason="opt-in only -- makes real, billed Claude API calls; set RUN_LLM_INTEGRATION_TESTS=1 to run",
)


def test_real_fixture_produces_well_shaped_result():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    client = build_claude_client()
    # First section only -- keeps a deliberately-run integration test's cost small.
    sections = fx["source"]["sections"][:1]
    result = check_omissions_comprehensiveness_qa(sections, fx["ai_output"], client, allow_llm_calls=True)
    assert result["method"] == "comprehensiveness_qa"
    assert result["validated"] is False
    assert isinstance(result["global_score"], float)
    for flagged in result["flagged_sections"]:
        assert "omitted_facts" in flagged
