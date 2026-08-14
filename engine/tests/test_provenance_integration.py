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
    # Deterministic stand-in for MiniCheck: every subclaim supported, chunk 0
    # (travel-pds-01's full_text is well under 1000 chars -- one chunk).
    return True, 0.9, 0


def test_full_trace_reproduces_worked_example_relations(tmp_path):
    source, decomposed = _load_travel_pds_01()
    sections = source["sections"]
    full_text = " ".join(s["text"] for s in sections)

    recorder = ProvenanceRecorder("travel-pds-01")
    with recorder.activity("decompose", "travel-pds-01", "llama3") as decompose_act:
        recorder.record_used(decompose_act, "source_doc")
        recorder.record_used(decompose_act, "ai_output")
    for i in range(len(decomposed)):
        recorder.record_generated(decompose_act, f"c{i+1}_claim")

    claims = label_claims(
        decomposed, full_text, sections, _stub_verifier,
        recorder=recorder, verifier_model="flan-t5-large",
    )
    for c in claims:
        recorder.record_derived("scorecard", [f"{c['id']}_verdict"])

    out = tmp_path / "travel-pds-01.prov.json"
    recorder.serialize(out)
    trace = json.loads(out.read_text())

    # travel-pds-01's real c2 claim ("Overseas medical is covered up to
    # $10,000,000.") resolves to evidence span s4_2 -- confirmed against the
    # committed fixture.
    c2 = next(c for c in claims if c["text"] == "Overseas medical is covered up to $10,000,000.")
    assert c2["evidence_span_ids"] == ["s4_2"]

    assert "decompose_travel-pds-01" in trace["activity"]
    assert "verify_c2" in trace["activity"]
    assert "llama3" in trace["agent"]
    assert "flan-t5-large" in trace["agent"]
    for entity_id in ["c2_claim", "c2_verdict", "c2_verify_signal", "evidence_span_s4_2", "scorecard"]:
        assert entity_id in trace["entity"]

    generated_by = {r["prov:entity"]: r["prov:activity"] for r in trace["wasGeneratedBy"].values()}
    assert generated_by["c2_claim"] == "decompose_travel-pds-01"
    assert generated_by["c2_verdict"] == "verify_c2"
    assert generated_by["c2_verify_signal"] == "verify_c2"

    # A dict keyed by generatedEntity would silently collapse this: c2 and c3
    # both resolve to section s4_2 with this test's crude stub verifier (every
    # subclaim "supported" in chunk 0, disambiguated by best_span's keyword
    # fallback within that one chunk) -- so evidence_span_s4_2 legitimately
    # gets TWO wasDerivedFrom edges, one per claim. Multiple valid derivations
    # for one entity is correct PROV, not a bug -- assert via set-of-tuples,
    # not a dict that can only keep the last-inserted value per key.
    derived_pairs = {(r["prov:generatedEntity"], r["prov:usedEntity"]) for r in trace["wasDerivedFrom"].values()}
    assert ("evidence_span_s4_2", "c2_verify_signal") in derived_pairs
    assert ("scorecard", "c2_verdict") in derived_pairs

    used_pairs = {(r["prov:activity"], r["prov:entity"]) for r in trace["used"].values()}
    assert ("verify_c2", "evidence_span_s4_2") not in used_pairs

    # round-trip validity via prov's own reader, not just "a file was written"
    ProvDocument.deserialize(source=str(out), format="json")


def test_recorder_none_still_works_for_non_fixture_callers():
    # inspect_scorer.py-style call: 4 positional args, no recorder. Must be
    # completely unaffected by this plan.
    source, decomposed = _load_travel_pds_01()
    sections = source["sections"]
    full_text = " ".join(s["text"] for s in sections)
    claims = label_claims(decomposed, full_text, sections, _stub_verifier)
    assert len(claims) == len(decomposed)
