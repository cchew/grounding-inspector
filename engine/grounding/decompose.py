import json

DECOMPOSE_PROMPT = (
    "PROMPT v1 (fixed; changing this changes scores — see spec decomposer caveat).\n"
    "Split the text into displayed claims (one per assertion the reader sees). For each, "
    "list its atomic, independently checkable sub-claims. Return ONLY JSON: "
    '[{"claim": "...", "subclaims": ["...", "..."]}].\n\nTEXT:\n'
)


def decompose_output(text: str, client, model: str) -> list[dict]:
    """Ollama-backed decomposer."""
    resp = client.chat(model=model, messages=[{"role": "user", "content": DECOMPOSE_PROMPT + text}])
    try:
        data = json.loads(resp["message"]["content"])
        return [{"text": d["claim"], "subclaims": list(d["subclaims"])} for d in data]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"decompose_output: could not parse LLM response: {exc}") from exc


def decompose_output_claude(text: str, client, model: str = "claude-haiku-4-5-20251001") -> list[dict]:
    """Claude-backed decomposer. Strips markdown code fences before parsing."""
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": DECOMPOSE_PROMPT + text}],
    )
    if not msg.content:
        raise ValueError("decompose_output_claude: received empty content from Claude")
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
        return [{"text": d["claim"], "subclaims": list(d["subclaims"])} for d in data]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"decompose_output_claude: could not parse response: {exc}") from exc


def build_client():
    """Ollama client."""
    import ollama
    return ollama


def build_claude_client():
    """Anthropic client. Reads ANTHROPIC_API_KEY from environment."""
    import anthropic
    return anthropic.Anthropic()
