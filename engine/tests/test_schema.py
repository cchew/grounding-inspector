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
    fx.pop("omissions", None)
    validate_fixture(fx)  # must not raise -- omissions is optional, not required


def test_comprehensiveness_qa_omission_is_valid():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["omissions"] = [{
        "method": "comprehensiveness_qa",
        "global_score": 0.33,
        "flagged_sections": [{
            "section_id": "s9", "score": 0.33,
            "omitted_facts": [{
                "fact": "policy excludes pre-existing conditions",
                "question": "Does the policy exclude pre-existing conditions?",
                "evidence": None,
            }],
        }],
        "hyperparameters": {"model": "claude-sonnet-4-5-20250929", "flag_threshold": 0.0},
        "validated": False,
        "caveat": "unvalidated",
    }]
    validate_fixture(fx)  # must not raise


def test_comprehensiveness_qa_rejects_top_tokens_field():
    # The exact bug the build-2 spec review caught: a malformed cross-method
    # entry (comprehensiveness_qa carrying build 1's top_tokens shape instead
    # of omitted_facts) must be rejected, not silently accepted.
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["omissions"] = [{
        "method": "comprehensiveness_qa",
        "global_score": 0.33,
        "flagged_sections": [{"section_id": "s9", "score": 0.33, "top_tokens": ["wrong", "shape"]}],
        "hyperparameters": {"model": "x", "flag_threshold": 0.0},
        "validated": False,
        "caveat": "unvalidated",
    }]
    with pytest.raises(Exception):
        validate_fixture(fx)


def test_embedkde_omission_still_valid_after_schema_restructure():
    # Regression: build 1's shape must be unaffected by the if/then split.
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


def test_both_methods_present_in_one_fixture_is_valid():
    fx = json.loads((ROOT / "fixtures" / "travel-pds-01.json").read_text())
    fx["omissions"] = [
        {"method": "embedkde", "global_score": 0.5, "flagged_sections": [],
         "hyperparameters": {}, "validated": False, "caveat": "x"},
        {"method": "comprehensiveness_qa", "global_score": 0.2, "flagged_sections": [],
         "hyperparameters": {"model": "x", "flag_threshold": 0.0}, "validated": False, "caveat": "y"},
    ]
    validate_fixture(fx)
