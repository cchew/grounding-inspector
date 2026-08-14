import json
import pathlib

from prov.model import ProvDocument

from grounding.pipeline import label_claims
from grounding.provenance import ProvenanceRecorder

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_travel_pds_01():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    decomposed = json.loads((ROOT / "fixtures" / "frozen" / "travel-pds-01.decomp.json").read_text())
    return fx["source"], decomposed


def _stub_verifier(subclaim, chunks):
    return True, 0.9, 0


def test_full_trace_reproduces_worked_example_relations(tmp_path):
    source, decomposed = _load_travel_pds_01()
    sections = source["sections"]
    full_text = " ".join(s["text"] for s in sections)

    recorder = ProvenanceRecorder("travel-pds-01")
    recorder.declare_entity("source_doc", {"source_sha256": "test-sha256"})
    with recorder.activity("decompose", "travel-pds-01", "llama3") as decompose_act:
        recorder.record_used(decompose_act, "source_doc")
        recorder.record_used(decompose_act, "ai_output")
    for i in range(len(decomposed)):
        recorder.record_generated(decompose_act, f"c{i+1}_claim")

    claims = label_claims(
        decomposed, full_text, sections, _stub_verifier,
        recorder=recorder, verifier_model="flan-t5-large",
    )
    recorder.declare_entity("scorecard", {"pipeline_commit": "test-commit"})
    for c in claims:
        recorder.record_derived("scorecard", [f"{c['id']}_verdict"])

    out = tmp_path / "travel-pds-01.prov.json"
    recorder.serialize(out)
    trace = json.loads(out.read_text())

    c2 = next(c for c in claims if c["text"] == "Overseas medical is covered up to $10,000,000.")
    assert c2["evidence_span_ids"] == ["s4_2"]

    assert "decompose_travel-pds-01" in trace["activity"]
    assert "verify_c2" in trace["activity"]
    assert "llama3" in trace["agent"]
    assert "flan-t5-large" in trace["agent"]
    for entity_id in ["c2_claim", "c2_verdict", "c2_verify_signal", "evidence_span_s4_2", "scorecard"]:
        assert entity_id in trace["entity"]
    assert trace["entity"]["source_doc"]["source_sha256"] == "test-sha256"
    assert trace["entity"]["scorecard"]["pipeline_commit"] == "test-commit"

    generated_by = {r["prov:entity"]: r["prov:activity"] for r in trace["wasGeneratedBy"].values()}
    assert generated_by["c2_claim"] == "decompose_travel-pds-01"
    assert generated_by["c2_verdict"] == "verify_c2"
    assert generated_by["c2_verify_signal"] == "verify_c2"

    # the lineage chain: verify must use the SAME claim entity decompose generated,
    # not a differently-named node -- otherwise the verdict is unreachable from the
    # decomposer Agent, defeating the entire point of an identity-traceability trail.
    used_pairs = {(r["prov:activity"], r["prov:entity"]) for r in trace["used"].values()}
    assert ("verify_c2", "c2_claim") in used_pairs

    derived_pairs = {(r["prov:generatedEntity"], r["prov:usedEntity"]) for r in trace["wasDerivedFrom"].values()}
    assert ("evidence_span_s4_2", "c2_verify_signal") in derived_pairs
    assert ("scorecard", "c2_verdict") in derived_pairs

    assert ("verify_c2", "evidence_span_s4_2") not in used_pairs

    ProvDocument.deserialize(source=str(out), format="json")


def test_recorder_none_still_works_for_non_fixture_callers():
    source, decomposed = _load_travel_pds_01()
    sections = source["sections"]
    full_text = " ".join(s["text"] for s in sections)
    claims = label_claims(decomposed, full_text, sections, _stub_verifier)
    assert len(claims) == len(decomposed)
