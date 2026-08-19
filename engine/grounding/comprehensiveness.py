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
