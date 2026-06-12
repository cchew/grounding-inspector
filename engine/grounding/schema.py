import json, pathlib, functools
from jsonschema import validate, Draft7Validator

_SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[2] / "contract" / "fixture.schema.json"

@functools.lru_cache(maxsize=None)
def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())

def validate_fixture(fixture: dict) -> None:
    Draft7Validator.check_schema(load_schema())
    validate(instance=fixture, schema=load_schema())
