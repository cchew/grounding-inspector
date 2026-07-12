import re
from grounding.versioning import pipeline_commit, source_sha256

def test_pipeline_commit_returns_short_sha_or_unknown():
    result = pipeline_commit()
    assert result == "unknown" or re.fullmatch(r"[0-9a-f]{7,10}", result)

def test_source_sha256_is_deterministic_and_order_sensitive():
    sections_a = [{"text": "foo"}, {"text": "bar"}]
    sections_b = [{"text": "foo"}, {"text": "bar"}]
    sections_c = [{"text": "bar"}, {"text": "foo"}]
    assert source_sha256(sections_a) == source_sha256(sections_b)
    assert source_sha256(sections_a) != source_sha256(sections_c)

def test_source_sha256_returns_hex_digest():
    result = source_sha256([{"text": "x"}])
    assert re.fullmatch(r"[0-9a-f]{64}", result)
