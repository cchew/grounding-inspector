import json

from grounding.pipeline import label_claims
from grounding.localise import best_span
from grounding.provenance import ProvenanceRecorder

SECTIONS = [
    {"id": "s1", "page": 1, "char_start": 0, "char_end": 50,
     "text": "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."},
]


def always_true(subclaim, chunks):
    return True, 0.9, 0


def test_numeric_mismatch_downgrades_grounded_to_unsupported():
    decomposed = [{"text": "Laptop Computer is covered for up to $5,000.", "subclaims": ["laptop computer covered to $5,000"]}]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "unsupported"
    assert "$5,000" in claims[0]["rationale"]
    assert "exact" in claims[0]["rationale"]
    assert "automated numeric check" in claims[0]["rationale"]


def test_no_numeric_mismatch_keeps_grounded_label_and_empty_rationale():
    decomposed = [{"text": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]}]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "grounded"
    assert claims[0]["rationale"] == ""


def test_mixed_subclaims_with_numeric_mismatch_stays_partial():
    decomposed = [{
        "text": "Laptop Computer is covered, for up to $5,000.",
        "subclaims": ["laptop computer is covered", "the limit is $5,000"],
    }]
    def half_true(subclaim, chunks):
        return ("covered" in subclaim), 0.9, 0
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, half_true)
    assert claims[0]["label"] == "partial"
    assert "$5,000" in claims[0]["rationale"]


def test_partial_without_numeric_issue_gets_a_plain_rationale():
    decomposed = [{
        "text": "Laptops are covered and there is free roadside assistance.",
        "subclaims": ["laptops are covered", "there is free roadside assistance"],
    }]

    def half_true(subclaim, chunks):
        return ("laptop" in subclaim), 0.9, 0

    claims = label_claims(
        decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, half_true,
    )
    assert claims[0]["label"] == "partial"
    assert "supported by the" in claims[0]["rationale"]
    assert "numeric" not in claims[0]["rationale"]


def test_percentage_claim_mismatch_downgrades_with_rounded_policy():
    sections = [
        {"id": "s2", "page": 1, "char_start": 0, "char_end": 40,
         "text": "The co-payment rate is 10.0% of the claim amount."},
    ]
    decomposed = [{"text": "The co-payment is 15%.", "subclaims": ["co-payment is 15%"]}]
    claims = label_claims(decomposed, "The co-payment rate is 10.0% of the claim amount.", sections, always_true)
    assert claims[0]["label"] == "unsupported"
    assert "15%" in claims[0]["rationale"]
    assert "rounded" in claims[0]["rationale"]


def test_multiple_numeric_spans_in_claim_leaves_label_and_rationale_untouched():
    decomposed = [{
        "text": "Cameras are covered for $4,000 or $3,000 depending on plan.",
        "subclaims": ["cameras covered for $4,000 or $3,000 depending on plan"],
    }]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "grounded"
    assert claims[0]["rationale"] == ""


def test_paraphrase_near_decoy_resolves_to_correct_section():
    filler = "x" * 990
    decoy = "Coverage for delayed baggage lasts five days from the date of delay unless a claim is not lodged."
    source = "Baggage delay compensation applies once the interruption continues for five days or more before resolution."
    sections = [
        {"id": "filler", "page": 1, "text": filler},
        {"id": "decoyB", "page": 2, "text": decoy},
        {"id": "sourceA", "page": 3, "text": source},
    ]
    full_text = "".join(s["text"] for s in sections)
    claim = "Delayed baggage is compensated for a duration of five days or longer."
    decomposed = [{"text": claim, "subclaims": [claim]}]

    decoy_start = len(filler)
    assert decoy_start < 1000 <= decoy_start + len(decoy)

    naive_span = best_span(claim, sections)
    assert naive_span["id"] == "decoyB"

    def verifier_fn(subclaim, chunks):
        source_chunk_idx = next(i for i, c in enumerate(chunks) if source in c)
        return True, 0.95, source_chunk_idx

    claims = label_claims(decomposed, full_text, sections, verifier_fn)
    assert claims[0]["evidence_span_ids"] == ["sourceA"]


def test_recorder_none_leaves_output_unchanged():
    decomposed = [{"text": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]}]
    doc = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    without_recorder = label_claims(decomposed, doc, SECTIONS, always_true)
    with_recorder = label_claims(decomposed, doc, SECTIONS, always_true, recorder=ProvenanceRecorder("fx"), verifier_model="flan-t5-large")
    assert with_recorder == without_recorder


def test_recorder_captures_verify_activity_and_verdict_and_signal():
    decomposed = [{"text": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]}]
    doc = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    recorder = ProvenanceRecorder("fx")
    claims = label_claims(decomposed, doc, SECTIONS, always_true, recorder=recorder, verifier_model="flan-t5-large")
    assert claims[0]["label"] == "grounded"

    trace = json.loads(recorder.doc.serialize(format="json"))
    assert "verify_c1" in trace["activity"]
    assert "flan-t5-large" in trace["agent"]
    assert trace["entity"]["c1_verdict"]["label"] == "grounded"
    assert trace["entity"]["c1_verdict"]["numeric_check_applied"] is True
    assert trace["entity"]["c1_verdict"]["numeric_mismatch_found"] is False
    assert "subclaim_results" in trace["entity"]["c1_verify_signal"]

    generated_by = {r["prov:entity"]: r["prov:activity"] for r in trace["wasGeneratedBy"].values()}
    assert generated_by["c1_verdict"] == "verify_c1"
    assert generated_by["c1_verify_signal"] == "verify_c1"


def test_recorder_derives_evidence_span_from_verify_signal_not_used_by_verify():
    decomposed = [{"text": "Cameras are covered for up to $4,000.", "subclaims": ["cameras covered to $4,000"]}]
    doc = "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."
    recorder = ProvenanceRecorder("fx")
    claims = label_claims(decomposed, doc, SECTIONS, always_true, recorder=recorder, verifier_model="flan-t5-large")
    assert claims[0]["evidence_span_ids"] == ["s1"]

    trace = json.loads(recorder.doc.serialize(format="json"))
    derived = {r["prov:generatedEntity"]: r["prov:usedEntity"] for r in trace["wasDerivedFrom"].values()}
    assert derived["evidence_span_s1"] == "c1_verify_signal"

    used_pairs = {(r["prov:activity"], r["prov:entity"]) for r in trace["used"].values()}
    assert ("verify_c1", "evidence_span_s1") not in used_pairs
    assert ("verify_c1", "c1_claim") in used_pairs
    assert ("verify_c1", "source_doc") in used_pairs
