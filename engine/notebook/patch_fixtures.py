"""
Surgical fixture patch: add version-pinning metadata to all 5 fixtures'
scorecards, and regenerate rationale for the 3 confirmed numeric-mismatch
claims (Cover-More c2/c4, Synthetic 03 c2). All other claims/labels are
left untouched -- see the spec's Task 6 rationale for why this is surgical,
not a full pipeline regeneration.

Usage:
    cd engine
    source .venv/bin/activate
    python notebook/patch_fixtures.py
"""
import json
import pathlib

from grounding.numeric_check import numeric_mismatch
from grounding.versioning import pipeline_commit, source_sha256

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "fixtures"

# (fixture_id, claim_id) -> the verifier_model that produced this fixture's
# original scorecard numbers (from repo/README.md's verifier table).
NUMERIC_FIX_TARGETS = {
    ("covermore-pds-01", "c2"),
    ("covermore-pds-01", "c4"),
    ("travel-pds-03", "c2"),
}

ALL_FIXTURE_IDS = [
    "travel-pds-01", "travel-pds-02", "travel-pds-03",
    "covermore-pds-01", "budgetdirect-pds-01",
]


def patch_fixture(fixture_id: str) -> None:
    path = FIXTURES_DIR / f"{fixture_id}.json"
    fixture = json.loads(path.read_text())
    sections_by_id = {s["id"]: s["text"] for s in fixture["source"]["sections"]}

    for claim in fixture["claims"]:
        key = (fixture_id, claim["id"])
        if key not in NUMERIC_FIX_TARGETS:
            continue
        evidence_text = "".join(sections_by_id[sid] for sid in claim["evidence_span_ids"])
        mismatch_value = numeric_mismatch(claim["text"], evidence_text)
        if mismatch_value is None:
            raise RuntimeError(
                f"{fixture_id}/{claim['id']}: expected a numeric mismatch to be "
                f"detected (confirmed during planning) but numeric_mismatch() "
                f"returned None -- investigate before proceeding."
            )
        claim["rationale"] = (
            f"Claim states ${mismatch_value:,.0f}; this figure does not appear "
            f"in the matched evidence (automated numeric check)."
        )
        print(f"[{fixture_id}] {claim['id']}: rationale updated -> {claim['rationale']!r}")

    fixture["scorecard"]["pipeline_commit"] = pipeline_commit()
    fixture["scorecard"]["verifier_model"] = "flan-t5-large"
    fixture["scorecard"]["source_sha256"] = source_sha256(fixture["source"]["sections"])

    path.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"[{fixture_id}] wrote {path}")


if __name__ == "__main__":
    for fid in ALL_FIXTURE_IDS:
        patch_fixture(fid)
