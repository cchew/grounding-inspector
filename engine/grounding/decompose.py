import json

DECOMPOSE_PROMPT = (
    "PROMPT v1 (fixed; changing this changes scores — see spec decomposer caveat).\n"
    "Split the text into displayed claims (one per assertion the reader sees). For each, "
    "list its atomic, independently checkable sub-claims. Return ONLY JSON: "
    '[{"claim": "...", "subclaims": ["...", "..."]}].\n\nTEXT:\n'
)

def decompose_output(text: str, client, model: str) -> list[dict]:
    resp = client.chat(model=model, messages=[{"role": "user", "content": DECOMPOSE_PROMPT + text}])
    data = json.loads(resp["message"]["content"])
    return [{"text": d["claim"], "subclaims": list(d["subclaims"])} for d in data]

def build_client():
    import ollama
    return ollama
