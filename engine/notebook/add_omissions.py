"""
Add omission signals to all existing fixtures. Pure addition -- ai_output/
claims/groundedness/scorecard are read and rewritten byte-for-byte
unchanged; only the omissions field is populated.

embedkde: downloads a ~1GB pretrained FastText model on first run (gensim
caches it locally after that). Free, local, zero marginal API cost.

comprehensiveness_qa: makes real Claude API calls (decompose + question-gen
+ judge, per source subclaim) -- real cost and latency. Opt-in only: pass
--methods embedkde comprehensiveness_qa, or call run(methods=(...)) directly.
Default is embedkde only -- no LLM call fires without explicitly asking.

Usage:
    cd engine
    source .venv/bin/activate
    python notebook/add_omissions.py                                    # embedkde only (default)
    python notebook/add_omissions.py --methods embedkde comprehensiveness_qa
"""
import argparse
import json
import pathlib

from grounding.comprehensiveness import check_omissions_comprehensiveness_qa
from grounding.decompose import build_claude_client
from grounding.omission import check_omissions_embedkde
from grounding.omission_embed import make_fasttext_embedder
from grounding.schema import validate_fixture

ROOT = pathlib.Path(__file__).resolve().parents[2]

FIXTURE_IDS = [
    "travel-pds-01", "travel-pds-02", "travel-pds-03",
    "covermore-pds-01", "budgetdirect-pds-01",
]


def regenerate_fixture(fixture: dict, methods: tuple[str, ...], embedder=None, client=None) -> dict:
    """Pure: takes a fixture dict, returns a new dict with `omissions`
    populated for the requested methods. Raises AssertionError if the
    non-omissions fields would change (byte-for-byte guard) -- caller
    decides what to do with that; this function never touches disk."""
    before_without_omissions = dict(fixture)
    before_without_omissions.pop("omissions", None)
    before = json.dumps(before_without_omissions, sort_keys=True)

    omissions = []
    if "embedkde" in methods:
        omissions.append(check_omissions_embedkde(fixture["source"]["sections"], fixture["ai_output"], embedder))
    if "comprehensiveness_qa" in methods:
        omissions.append(check_omissions_comprehensiveness_qa(
            fixture["source"]["sections"], fixture["ai_output"], client, allow_llm_calls=True,
        ))

    updated = dict(fixture)
    updated["omissions"] = omissions

    after_without_omissions = dict(updated)
    del after_without_omissions["omissions"]
    assert json.dumps(after_without_omissions, sort_keys=True) == before, \
        f"{fixture.get('fixture_id', '?')}: non-omissions fields changed -- aborting write"

    validate_fixture(updated)  # fail loudly before write
    return updated


def run(methods: tuple[str, ...] = ("embedkde",)):
    embedder = make_fasttext_embedder() if "embedkde" in methods else None
    client = build_claude_client() if "comprehensiveness_qa" in methods else None
    if "embedkde" in methods:
        print("Loading pretrained FastText model (first run downloads ~1GB)...")

    for fid in FIXTURE_IDS:
        path = ROOT / "fixtures" / f"{fid}.json"
        fixture = json.loads(path.read_text())
        updated = regenerate_fixture(fixture, methods, embedder=embedder, client=client)
        path.write_text(json.dumps(updated, indent=2))
        for result in updated["omissions"]:
            n_flagged = len(result["flagged_sections"])
            print(f"[{fid}] {result['method']}: global_score={result['global_score']:.3f}, "
                  f"{n_flagged} section(s) flagged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", default=["embedkde"],
                         choices=["embedkde", "comprehensiveness_qa"])
    args = parser.parse_args()
    run(methods=tuple(args.methods))
