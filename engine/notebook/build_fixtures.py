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
from grounding.verify import build_scorer
from grounding.pipeline import label_claims
from grounding.fixturegen import build_fixture

ROOT = pathlib.Path(__file__).resolve().parents[2]

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
    client = build_client()   # ollama
    scorer = build_scorer()   # MiniCheck flan-t5-large

    for fid, paths in SOURCES.items():
        existing = json.loads(paths["source_file"].read_text())
        ai_output = existing["ai_output"]
        source = existing["source"]
        sections = source["sections"]
        full_text = " ".join(s["text"] for s in sections)

        # Decompose (run once, freeze output)
        frozen_path = paths["frozen_decomp"]
        if frozen_path.exists():
            print(f"[{fid}] using frozen decomposition")
            decomposed = json.loads(frozen_path.read_text())
        else:
            print(f"[{fid}] decomposing via Ollama...")
            decomposed = decompose_output(ai_output, client=client, model="llama3")
            frozen_path.parent.mkdir(parents=True, exist_ok=True)
            frozen_path.write_text(json.dumps(decomposed, indent=2))
            print(f"[{fid}] frozen to {frozen_path}")

        # Verify claims
        print(f"[{fid}] verifying {len(decomposed)} claims...")
        claims = label_claims(decomposed, full_text, sections, scorer)

        # Build and write fixture
        fx = build_fixture(fid, source, ai_output, claims, SCORECARD_PLACEHOLDER)
        out_path = ROOT / "fixtures" / f"{fid}.json"
        out_path.write_text(json.dumps(fx, indent=2))
        print(f"[{fid}] wrote {out_path}")


if __name__ == "__main__":
    run()
