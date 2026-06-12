import json, pathlib, pytest
from grounding.schema import load_schema, validate_fixture

ROOT = pathlib.Path(__file__).resolve().parents[2]

def test_handauthored_fixture_is_valid():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    validate_fixture(fx)  # must not raise

def test_bad_label_rejected():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["claims"][0]["label"] = "maybe"
    with pytest.raises(Exception):
        validate_fixture(fx)
