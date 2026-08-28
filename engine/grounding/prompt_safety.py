"""Neutralise XML tag delimiters inside untrusted spans of a prompt.

The live-path prompts put untrusted text inside <candidate_text>, <claim> and
<document_context> tags in the user turn, with the instructions in `system`.
That split only holds if the untrusted text cannot close its own wrapper: a
payload containing `</candidate_text>` would end the data span early and leave
everything after it at user-turn top level, which the system prompts designate
as the trusted/instruction channel.

The regex is deliberately narrow rather than a blanket `<` -> `&lt;`: ordinary
prose (including unrelated angle brackets and other XML) stays byte-identical,
so this does not shift decomposer/verifier scores on normal input.
"""
import re

_TAG_BREAK = re.compile(r"<\s*/?\s*(candidate_text|claim|document_context)\s*>", re.I)


def neutralise(text: str) -> str:
    """Escape the leading `<` of any wrapper-tag sequence in untrusted text."""
    return _TAG_BREAK.sub(lambda m: m.group(0).replace("<", "&lt;", 1), text)
