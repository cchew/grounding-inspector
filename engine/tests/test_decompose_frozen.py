import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_frozen(fixture_id: str) -> list:
    path = ROOT / "fixtures" / "frozen" / f"{fixture_id}.decomp.json"
    return json.loads(path.read_text())


def test_frozen_travel_pds_01_well_formed():
    frozen = _load_frozen("travel-pds-01")
    assert len(frozen) > 0
    assert all("text" in c and "subclaims" in c for c in frozen)
    assert all(isinstance(c["subclaims"], list) and len(c["subclaims"]) > 0 for c in frozen)


def test_frozen_travel_pds_02_well_formed():
    frozen = _load_frozen("travel-pds-02")
    assert len(frozen) > 0
    assert all("text" in c and "subclaims" in c for c in frozen)


def test_frozen_travel_pds_03_well_formed():
    frozen = _load_frozen("travel-pds-03")
    assert len(frozen) > 0
    assert all("text" in c and "subclaims" in c for c in frozen)
