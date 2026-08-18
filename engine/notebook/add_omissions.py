"""
Add EmbedKDECheck omission signals to all existing fixtures.
This is a pure addition -- ai_output/claims/groundedness/scorecard are
read and rewritten byte-for-byte unchanged; only the omissions field
is populated.

Downloads a ~1GB pretrained FastText model on first run (gensim caches
it locally after that -- subsequent runs are fast).

Usage:
    cd engine
    source .venv/bin/activate
    python notebook/add_omissions.py
"""
import json
import pathlib

from grounding.omission import check_omissions_embedkde
from grounding.omission_embed import make_fasttext_embedder
from grounding.schema import validate_fixture

ROOT = pathlib.Path(__file__).resolve().parents[2]

FIXTURE_IDS = [
    "travel-pds-01", "travel-pds-02", "travel-pds-03",
    "covermore-pds-01", "budgetdirect-pds-01",
]


def run():
    print("Loading pretrained FastText model (first run downloads ~1GB)...")
    embedder = make_fasttext_embedder()

    for fid in FIXTURE_IDS:
        path = ROOT / "fixtures" / f"{fid}.json"
        fixture = json.loads(path.read_text())
        # Snapshot everything EXCEPT omissions, so the guard below compares
        # like with like on a re-run (an earlier run leaves an omissions
        # field behind; including it here would make the assert fire on any
        # second invocation, regardless of whether anything else changed).
        before_without_omissions = dict(fixture)
        before_without_omissions.pop("omissions", None)
        before = json.dumps(before_without_omissions, sort_keys=True)

        omission_result = check_omissions_embedkde(
            fixture["source"]["sections"], fixture["ai_output"], embedder,
        )
        fixture["omissions"] = [omission_result]

        # Confirm nothing else in the fixture changed before writing.
        after_without_omissions = dict(fixture)
        del after_without_omissions["omissions"]
        assert json.dumps(after_without_omissions, sort_keys=True) == before, (
            f"{fid}: non-omissions fields changed -- aborting write"
        )

        validate_fixture(fixture)  # fail loudly before write
        path.write_text(json.dumps(fixture, indent=2))
        n_flagged = len(omission_result["flagged_sections"])
        print(f"[{fid}] wrote omissions: global_score={omission_result['global_score']:.3f}, "
              f"{n_flagged} section(s) flagged")


if __name__ == "__main__":
    run()
