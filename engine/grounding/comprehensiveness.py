import json

from grounding.decompose import decompose_output_claude

_QUESTION_PROMPT = (
    "PROMPT v1 (fixed; changing this changes recall -- treat like DECOMPOSE_PROMPT).\n"
    "Given a single factual claim, write ONE closed factual question whose answer "
    "would confirm or deny that a document states this fact. Return ONLY the "
    "question text, no preamble.\n\nCLAIM:\n"
)


def generate_question(subclaim: str, client, model: str) -> str:
    """New prompt. Plain-text response (single question), no JSON needed."""
    msg = client.messages.create(
        model=model, max_tokens=200,
        messages=[{"role": "user", "content": _QUESTION_PROMPT + subclaim}],
    )
    if not msg.content:
        raise ValueError("generate_question: received empty content from Claude")
    return msg.content[0].text.strip()


_JUDGE_PROMPT = (
    "PROMPT v1 (fixed; changing this changes recall).\n"
    "Given a QUESTION, the SOURCE FACT it was generated from, and a CANDIDATE "
    "DOCUMENT, determine whether the candidate document states or implies an "
    "answer consistent with the source fact. Return ONLY JSON: "
    '{"status": "COVERED"|"OMITTED", "evidence": "<quoted span or null>"}.\n\n'
)


def judge_coverage(question: str, source_fact: str, ai_output: str, client, model: str) -> dict:
    """New prompt. JSON response, parsed with the same markdown-fence-stripping
    decompose_output_claude already uses. Raises ValueError on parse failure
    (fail loudly, no silent fallback -- matches decompose_output_claude)."""
    prompt = (
        _JUDGE_PROMPT
        + f"QUESTION: {question}\n\nSOURCE FACT: {source_fact}\n\nCANDIDATE DOCUMENT:\n{ai_output}"
    )
    msg = client.messages.create(model=model, max_tokens=300, messages=[{"role": "user", "content": prompt}])
    if not msg.content:
        raise ValueError("judge_coverage: received empty content from Claude")
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
        status = data["status"]
        if status not in ("COVERED", "OMITTED"):
            raise ValueError(f"judge_coverage: unexpected status {status!r}")
        return {"status": status, "evidence": data.get("evidence")}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"judge_coverage: could not parse response: {exc}") from exc
