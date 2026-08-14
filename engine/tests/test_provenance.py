import json

from prov.model import ProvDocument

from grounding.provenance import ProvenanceRecorder


def test_activity_records_start_and_end_time_and_associates_agent():
    rec = ProvenanceRecorder("fx1")
    with rec.activity("decompose", "fx1", "llama3") as act:
        pass
    doc = json.loads(rec.doc.serialize(format="json"))
    assert "decompose_fx1" in doc["activity"]
    assert "prov:startTime" in doc["activity"]["decompose_fx1"]
    assert "prov:endTime" in doc["activity"]["decompose_fx1"]
    assert "llama3" in doc["agent"]
    assoc = list(doc["wasAssociatedWith"].values())[0]
    assert assoc == {"prov:activity": "decompose_fx1", "prov:agent": "llama3"}


def test_agent_is_memoised_not_duplicated_across_activities():
    rec = ProvenanceRecorder("fx1")
    with rec.activity("verify", "c1", "flan-t5-large") as act1:
        pass
    with rec.activity("verify", "c2", "flan-t5-large") as act2:
        pass
    doc = json.loads(rec.doc.serialize(format="json"))
    assert list(doc["agent"].keys()) == ["flan-t5-large"]
    assert len(doc["wasAssociatedWith"]) == 2  # both activities still individually associated


def test_entity_is_memoised_not_duplicated_across_calls():
    rec = ProvenanceRecorder("fx1")
    with rec.activity("verify", "c1", "flan-t5-large") as act:
        rec.record_used(act, "source_doc")
        rec.record_used(act, "source_doc")  # same entity referenced twice
    doc = json.loads(rec.doc.serialize(format="json"))
    assert list(doc["entity"].keys()) == ["source_doc"]


def test_record_generated_sets_entity_attributes():
    rec = ProvenanceRecorder("fx1")
    with rec.activity("verify", "c1", "flan-t5-large") as act:
        rec.record_generated(act, "c1_verdict", {"label": "grounded"})
    doc = json.loads(rec.doc.serialize(format="json"))
    assert doc["entity"]["c1_verdict"]["label"] == "grounded"
    gen = list(doc["wasGeneratedBy"].values())[0]
    assert gen == {"prov:entity": "c1_verdict", "prov:activity": "verify_c1"}


def test_record_derived_creates_wasderivedfrom_with_no_activity():
    rec = ProvenanceRecorder("fx1")
    rec.record_derived("evidence_span_s1", ["c1_verify_signal"])
    doc = json.loads(rec.doc.serialize(format="json"))
    derived = list(doc["wasDerivedFrom"].values())[0]
    assert derived == {"prov:generatedEntity": "evidence_span_s1", "prov:usedEntity": "c1_verify_signal"}


def test_serialize_writes_a_file_that_round_trips_via_provs_own_reader(tmp_path):
    rec = ProvenanceRecorder("fx1")
    with rec.activity("decompose", "fx1", "llama3") as act:
        rec.record_used(act, "source_doc")
        rec.record_generated(act, "c1_claim")
    out = tmp_path / "fx1.prov.json"
    rec.serialize(out)
    assert out.exists()
    reloaded = ProvDocument.deserialize(source=str(out), format="json")
    # 7 records: ProvActivity, ProvAgent, ProvAssociation (wasAssociatedWith),
    # 2x ProvEntity (source_doc, c1_claim), ProvUsage (used), ProvGeneration
    # (wasGeneratedBy) -- verified directly against the real library, not
    # assumed (relation records count separately from the entities/activities
    # they connect).
    assert len(reloaded.get_records()) == 7


def test_declare_entity_sets_attrs_without_any_relation():
    rec = ProvenanceRecorder("fx1")
    rec.declare_entity("source_doc", {"source_sha256": "abc123"})
    doc = json.loads(rec.doc.serialize(format="json"))
    assert doc["entity"]["source_doc"]["source_sha256"] == "abc123"
    assert doc.get("used", {}) == {}
    assert doc.get("wasGeneratedBy", {}) == {}
