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

def test_fixture_with_omissions_is_valid():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["omissions"] = [{
        "method": "embedkde",
        "global_score": 0.5,
        "flagged_sections": [{"section_id": "s9", "score": 0.5, "top_tokens": ["exclusions"]}],
        "hyperparameters": {"pca_components": 16, "kde_bandwidth": 1.0, "threshold_std": 1.5},
        "validated": False,
        "caveat": "unvalidated",
    }]
    validate_fixture(fx)  # must not raise


def test_omissions_rejects_unknown_method():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["omissions"] = [{
        "method": "not-a-real-method",
        "global_score": 0.5, "flagged_sections": [],
        "hyperparameters": {}, "validated": False, "caveat": "x",
    }]
    with pytest.raises(Exception):
        validate_fixture(fx)


def test_fixture_without_omissions_field_still_valid():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    assert "omissions" not in fx
    validate_fixture(fx)  # must not raise -- omissions is optional, not required
