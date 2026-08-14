"""
Build fixtures from synthetic PDS sources.
Run once with Ollama + MiniCheck available; commit the output.

Usage:
    cd engine
    source .venv/bin/activate
    python notebook/build_fixtures.py
"""
import json
import pathlib

from grounding.decompose import build_client, decompose_output
from grounding.verify import build_scorer, make_minicheck_verifier
from grounding.pipeline import label_claims
from grounding.fixturegen import build_fixture
from grounding.provenance import ProvenanceRecorder
from grounding.versioning import pipeline_commit, source_sha256

ROOT = pathlib.Path(__file__).resolve().parents[2]

DECOMPOSE_MODEL = "llama3"
VERIFIER_MODEL = "flan-t5-large"

SOURCES = {
    "travel-pds-01": {
        "source_file": ROOT / "fixtures" / "travel-pds-01.json",
        "frozen_decomp": ROOT / "fixtures" / "frozen" / "travel-pds-01.decomp.json",
    },
    "travel-pds-02": {
        "source_file": ROOT / "fixtures" / "travel-pds-02.json",
        "frozen_decomp": ROOT / "fixtures" / "frozen" / "travel-pds-02.decomp.json",
    },
    "travel-pds-03": {
        "source_file": ROOT / "fixtures" / "travel-pds-03.json",
        "frozen_decomp": ROOT / "fixtures" / "frozen" / "travel-pds-03.decomp.json",
    },
}

SCORECARD_PLACEHOLDER = {
    "recall": 0.0, "recall_ci": [0.0, 0.0], "false_negatives": 0, "n_positive": 0,
    "citation_precision": None, "cohen_kappa": None,
    "validated_on": "placeholder — replaced after Phase 3 RAGTruth run",
    "domain_note": "benchmark distribution; NOT measured on PDS",
}


def run():
    client = build_client()
    scorer = build_scorer(VERIFIER_MODEL)
    verifier_fn = make_minicheck_verifier(scorer)

    for fid, paths in SOURCES.items():
        existing = json.loads(paths["source_file"].read_text())
        ai_output = existing["ai_output"]
        source = existing["source"]
        sections = source["sections"]
        full_text = " ".join(s["text"] for s in sections)

        recorder = ProvenanceRecorder(fid)
        recorder.declare_entity("source_doc", {"source_sha256": source_sha256(sections)})

        # Decompose (run once, freeze output)
        frozen_path = paths["frozen_decomp"]
        with recorder.activity("decompose", fid, DECOMPOSE_MODEL) as decompose_act:
            recorder.record_used(decompose_act, "source_doc")
            recorder.record_used(decompose_act, "ai_output")
            if frozen_path.exists():
                print(f"[{fid}] using frozen decomposition")
                decomposed = json.loads(frozen_path.read_text())
            else:
                print(f"[{fid}] decomposing via Ollama...")
                decomposed = decompose_output(ai_output, client=client, model=DECOMPOSE_MODEL)
                frozen_path.parent.mkdir(parents=True, exist_ok=True)
                frozen_path.write_text(json.dumps(decomposed, indent=2))
                print(f"[{fid}] frozen to {frozen_path}")
        for i in range(len(decomposed)):
            recorder.record_generated(decompose_act, f"c{i+1}_claim")

        # Verify claims
        print(f"[{fid}] verifying {len(decomposed)} claims...")
        claims = label_claims(
            decomposed, full_text, sections, verifier_fn,
            recorder=recorder, verifier_model=VERIFIER_MODEL,
        )

        # Build and write fixture -- before serializing the PROV trace, so a
        # schema-validation failure (build_fixture raises) never leaves an
        # orphan trace describing a fixture that was never actually written.
        fx = build_fixture(fid, source, ai_output, claims, SCORECARD_PLACEHOLDER)
        out_path = ROOT / "fixtures" / f"{fid}.json"
        out_path.write_text(json.dumps(fx, indent=2))
        print(f"[{fid}] wrote {out_path}")

        recorder.declare_entity("scorecard", {"pipeline_commit": pipeline_commit()})
        for c in claims:
            recorder.record_derived("scorecard", [f"{c['id']}_verdict"])
        prov_path = ROOT / "fixtures" / "prov" / f"{fid}.prov.json"
        prov_path.parent.mkdir(parents=True, exist_ok=True)
        recorder.serialize(prov_path)
        print(f"[{fid}] wrote {prov_path}")


if __name__ == "__main__":
    run()
