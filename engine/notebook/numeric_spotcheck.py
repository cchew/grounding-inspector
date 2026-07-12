# engine/notebook/numeric_spotcheck.py
"""
Spot-check whether the current default verifier (flan-t5-large) and
Bespoke-MiniCheck-7B correctly flag known numeric mismatches, using
subclaims and source text already committed to fixtures/frozen/ and
fixtures/covermore-pds-01.json.

Usage:
    cd engine
    source .venv/bin/activate
    python notebook/numeric_spotcheck.py

If the Bespoke-MiniCheck-7B section raises an ImportError or fails to load,
see the spec (docs/superpowers/specs/2026-07-11-grounding-inspector-dhda-readiness-design.md,
section 1) for the Colab CLI fallback. CONFIRM WITH CHING BEFORE RUNNING
ANYTHING ON COLAB -- it may incur cost.
"""
import json
import pathlib

from grounding.verify import build_scorer, verify_subclaim

ROOT = pathlib.Path(__file__).resolve().parents[2]

SOURCE_CHUNK = (
    "International Benefits Table — Luggage and Travel Documents "
    "(Comprehensive Plan): Total limit $15,000. Per-item limits: Phone or "
    "Smart Watch $1,500; Camera or Video Camera $4,000; Laptop Computer "
    "$4,000; Tablet Computer $3,000; Drone $1,200; Jewellery, watch or any "
    "other item $1,200; Delayed Luggage Allowance $1,100."
)

CASES = [
    {"id": "c1-total", "subclaim": "The total luggage coverage limit is $20,000.",
     "true_value": "15,000", "claimed_value": "20,000"},
    {"id": "c2-laptop", "subclaim": "The per-item limit for laptops is $5,000.",
     "true_value": "4,000", "claimed_value": "5,000"},
    {"id": "c4-jewellery", "subclaim": "The per-item limit for jewellery and watches is $2,000.",
     "true_value": "1,200", "claimed_value": "2,000"},
]


def run(model_name: str) -> list[dict]:
    print(f"\n=== {model_name} ===")
    scorer = build_scorer(model_name=model_name)
    results = []
    for case in CASES:
        supported, prob = verify_subclaim(case["subclaim"], [SOURCE_CHUNK], scorer)
        caught = not supported
        results.append({
            **case, "model": model_name, "predicted_supported": supported,
            "prob": prob, "caught_mismatch": caught,
        })
        status = "CAUGHT" if caught else "MISSED"
        print(f"  {case['id']}: predicted_supported={supported} prob={prob:.3f} "
              f"({status} the {case['claimed_value']} vs {case['true_value']} mismatch)")
    return results


if __name__ == "__main__":
    all_results = {"flan-t5-large": run("flan-t5-large")}
    try:
        all_results["Bespoke-MiniCheck-7B"] = run("Bespoke-MiniCheck-7B")
    except Exception as exc:
        print(f"\nBespoke-MiniCheck-7B failed to load locally: {exc}")
        print("See the spec's Colab CLI fallback section before concluding this path is dead.")
        print("CONFIRM WITH CHING BEFORE RUNNING ANYTHING ON COLAB (possible cost).")

    out_path = ROOT / "engine" / "notebook" / "numeric_spotcheck_results.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults written to {out_path}")
