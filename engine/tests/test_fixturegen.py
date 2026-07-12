from grounding.fixturegen import build_fixture
from grounding.schema import validate_fixture

SOURCE = {"title": "T", "sections": [
    {"id": "s4_2", "page": 12, "char_start": 0, "char_end": 10, "text": "covered up to $10,000,000"},
]}
CLAIMS = [
    {"id": "c1", "text": "value for money", "label": "unsupported",
     "evidence_span_ids": [], "quote": None, "page": None, "rationale": "no such judgment"},
    {"id": "c2", "text": "medical covered to $10m", "label": "grounded",
     "evidence_span_ids": ["s4_2"], "quote": "covered up to $10,000,000", "page": 12, "rationale": "stated"},
]
SCORECARD = {"recall": 0.9, "recall_ci": [0.8, 0.96], "false_negatives": 2, "n_positive": 20,
             "citation_precision": None, "cohen_kappa": 0.7,
             "validated_on": "RAGTruth (sampled, n=300)", "domain_note": "benchmark distribution; NOT measured on PDS",
             "pipeline_commit": "abc1234", "verifier_model": "flan-t5-large", "source_sha256": "0" * 64}

def test_build_fixture_is_schema_valid():
    fx = build_fixture("travel-pds-02", SOURCE, "ai text", CLAIMS, SCORECARD)
    validate_fixture(fx)
    assert fx["groundedness"] == {"score": 50, "n_grounded": 1, "n_partial": 0, "n_unsupported": 1}
