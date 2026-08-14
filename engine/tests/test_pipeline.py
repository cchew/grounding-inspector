# engine/tests/test_pipeline.py
import json

from grounding.pipeline import label_claims
from grounding.localise import best_span

SECTIONS = [
    {"id": "s1", "page": 1, "char_start": 0, "char_end": 50,
     "text": "Camera $4,000; Laptop Computer $4,000; Tablet $3,000."},
]


def always_true(subclaim, chunks):
    return True, 0.9, 0


def test_numeric_mismatch_downgrades_grounded_to_unsupported():
    # Claim text shares enough vocabulary with the section ("laptop", "computer")
    # for best_span()'s token-overlap threshold to find a match even though the
    # mismatched number itself ($5 vs $4/$3) contributes no shared token -- a
    # claim using only "laptops... $5,000" without "Computer" scores 0.125,
    # just under best_span()'s 0.15 threshold, and no span is found at all.
    decomposed = [{"text": "Laptop Computer is covered for up to $5,000.", "subclaims": ["laptop computer covered to $5,000"]}]
    claims = label_claims(decomposed, "Camera $4,000; Laptop Computer $4,000; Tablet $3,000.", SECTIONS, always_true)
    assert claims[0]["label"] == "unsupported"
    assert "$5,000" in claims[0]["rationale"]
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


def test_paraphrase_near_decoy_resolves_to_correct_section():
    """Reproduces FUTURE.md's exact failure mode: a claim paraphrased from
    the true source section (low keyword overlap) sitting near a decoy
    section (high keyword overlap, not actually the support). The verifier's
    chunk index must win over best_span()'s keyword heuristic."""
    filler = "x" * 990  # push the decoy+source sections past chunk 0's 1000-char boundary
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
    # sanity check the fixture: decoy must straddle the chunk-0/chunk-1 boundary
    # at char 1000, otherwise this test isn't exercising the failure mode.
    assert decoy_start < 1000 <= decoy_start + len(decoy)

    naive_span = best_span(claim, sections)
    assert naive_span["id"] == "decoyB"  # confirms the keyword-overlap heuristic alone gets this wrong

    def verifier_fn(subclaim, chunks):
        source_chunk_idx = next(i for i, c in enumerate(chunks) if source in c)
        return True, 0.95, source_chunk_idx

    claims = label_claims(decomposed, full_text, sections, verifier_fn)
    assert claims[0]["evidence_span_ids"] == ["sourceA"]


from grounding.provenance import ProvenanceRecorder


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
    assert trace["entity"]["c1_verdict"]["numeric_check_applied"] is False

    generated_by = {r["prov:entity"]: r["prov:activity"] for r in trace["wasGeneratedBy"].values()}
    assert generated_by["c1_verdict"] == "verify_c1"
    assert generated_by["c1_verify_signal"] == "verify_c1"


def test_recorder_derives_evidence_span_from_verify_signal_not_used_by_verify():
    # The causality fix from the spec: the evidence span isn't known until
    # after the verify loop's results are in hand, so it must never appear
    # in Verify's own `used` set -- only as wasDerivedFrom the verify_signal.
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
    assert ("verify_c1", "c1") in used_pairs  # the claim itself IS used
    assert ("verify_c1", "source_doc") in used_pairs
