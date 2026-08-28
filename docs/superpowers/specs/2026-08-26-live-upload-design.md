# Grounding Inspector: Live Document Upload — Design

**Date:** 2026-08-26
**Status:** Draft, pending user review before implementation planning

## Purpose

GI today is a fully static site: the frontend (Vue/Vite on Netlify) renders pre-generated fixture JSON, and the actual grounding pipeline (`engine/grounding/*.py` — decompose → verify → localise → numeric/omission checks) runs offline, with results committed to the repo as fixtures. There is no live request-handling backend in production.

This feature lets a visitor upload their own AI output + reference document(s) and get a live grounding check, instead of only browsing pre-built fixtures. Framed as a real recurring public tool (not a one-off demo), which raises the bar on reliability, abuse resistance, and privacy handling relative to GI's current static-fixture posture.

**Explicit non-goal, carried from GI's genesis:** this is a research/self-check tool, not an assurance or consulting service. GI's own founding council flagged "evaluate the evaluator" as adjacent to an identity Ching has explicitly declined to take on elsewhere — build the artifact, decline the role. A live public checker makes that line load-bearing in a way the fixture demo never had to be.

## Architecture

- **Backend**: new FastAPI service on Modal, wrapping `engine/grounding/pipeline.py` and related modules directly — no reimplementation in another language. Matches the existing Act Alike deploy pattern (Vue on Netlify + FastAPI on Modal), so the deploy shape is already proven on this stack.
- **Frontend**: existing Vue/Vite app on Netlify gains a "check your document" view, which becomes the *default* landing view. The existing fixture browser becomes a secondary "try a sample" link, not the landing page — matching the reference UX pattern (upload primary, sample subordinate) seen at the [style-manual-check IM2026 entry](https://rjc27-sm.github.io/style-manual-check/im2026/index.html), which also disclosed exactly what gets sent to an external API vs. processed locally — worth mirroring in GI's own disclosure copy.
- **Quota store**: a new table in the existing Neon Postgres instance (already running, backing self-hosted Umami at $0/month) — no new database service.
- **Alerting**: Umami custom events (`umami.track('pipeline-failure', {...})`) for failure-rate visibility in the existing dashboard (pull-based, zero new infra); Resend (free tier, one API key) for real-time email alerts on pipeline failure only (push-based, the one genuinely new piece of infra in this design).

Rendering reuses `Inspector.vue` / `ClaimList.vue` / `OmissionPanel.vue` unchanged — both fixture-browsing and live-check results are the same fixture-shaped JSON contract, so the UI doesn't need to know which mode produced a result.

**Sync-first, async only if needed**: build the backend as a synchronous request/response API first. A full check runs several sequential Claude calls (decompose, verify, localise, numeric, comprehensiveness) and could be slow on a long document — if real-document latency exceeds a reasonable request timeout (~20-30s), upgrade to an async job-queue pattern (submit → poll for result) rather than pre-building that complexity speculatively.

## Data Flow

**Free-tier path (no key entered):**
1. User uploads/pastes AI output + reference doc(s) in the browser.
2. Frontend calls the Modal API. API checks quota in the Neon table, keyed to a **signed device token** (cookie/localStorage, minted on first visit) — not IP. IP-only quota keys break for any shared-NAT network (a whole government department can share one outbound IP), so the device token is the primary key and a much coarser per-IP ceiling (e.g. 50 req/hour) serves only as a backstop against direct API abuse that bypasses the browser entirely.
3. Under cap: API runs the pipeline using the server-side Anthropic key, increments the quota counter, returns the scorecard JSON. Over cap: rejected with an actionable message ("today's free checks are used — add your own API key to continue"), not a bare 429.
4. A per-token burst/concurrency limit (e.g. max 1 in-flight request) guards against a check-then-increment race before the daily counter catches up.

**BYO-key path:**
1. Same upload UI, plus a key input field (session-only — not persisted to localStorage).
2. Key is sent over HTTPS, used for that single pipeline run only, never logged or persisted, discarded immediately after. The daily *cost* quota is skipped entirely (it's the user's own Anthropic spend) — but the per-token burst/concurrency limit still applies. Modal compute is incurred regardless of whose Anthropic key is used, so an unlimited BYO-key path is still an infra-cost DoS vector even at zero Claude spend to you.

**Device-token limitation, stated plainly**: a token is trivially reset (incognito window, clear cookies) — it's a courtesy limit on casual reuse, not a hard abuse barrier. That's an acceptable trade for this feature's actual purpose (let a curious reader try it a few times); the per-IP backstop bounds worst-case scripted abuse. Escalate to email verification or another stronger identity mechanism only if real abuse is observed — no existing email-send or OAuth infrastructure exists anywhere in Ching's stack today, so this would be new infrastructure, not a small addition.

## Security & Abuse Controls

Reviewed against the [OWASP GenAI/LLM Top 10 (2026)](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) and OWASP API Security Top 10 (2023, still current).

- **Prompt injection (LLM01, #1 unchanged)**: GI already hardened `judge_coverage`/`generate_question` (system prompt + XML-tagged untrusted spans) during the comprehensiveness build — but that was for offline, Ching-controlled fixture generation. Every stage touching user text in the live path (`decompose.py`, `verify.py`'s verifier calls, `numeric_check.py`, the comprehensiveness calls) now receives genuinely adversarial public input on *both* the AI-output and reference-doc sides. **Action: audit every live-path LLM call to confirm the same system-prompt/XML-tagged pattern applies uniformly, not just the two functions that originally got it.**
- **Unbounded consumption (LLM06, +4 places this year) / API4:2023**: file-type allowlist (whatever `pipeline.py` can actually parse today — confirm during planning), a hard upload size cap, and a hard cap on decomposed-fact count specifically for `comprehensiveness_qa` (one LLM call per fact — an adversarially long/padded document could otherwise turn one free check into dozens of API calls).
- **Server-side enforcement only**: CORS restricts which browsers call the API, but nothing stops a script hitting the Modal endpoint directly. Quota, size caps, and rate limits must all be enforced server-side — the upload form is UX, not a security boundary.
- **Sensitive information disclosure (LLM02, #2 unchanged) / API1:2023**: application/error logs must never capture raw document text, a BYO API key, **or the server-side Anthropic key** in plaintext — the server-side key backs a public endpoint for the first time here and needs the identical no-logging discipline as BYO keys, not an implicit exemption because it's "yours." If a future "manage your saved checks" view is built on top of opt-in retention, it must authorize by owner (device token), not a guessable ID.
- **Supply chain (LLM04)**: any new PDF/docx parser added for uploads needs the same vetting as any other new dependency — pinned, well-maintained, not obscure, added to `engine/requirements.txt` with a pinned version (not `versioning.py`, which only stamps fixtures with a git SHA/content hash for provenance — it does no dependency pinning).
- **Misinformation (LLM07, +2 places)**: GI's own known-limitation caveats (κ/balanced_accuracy, methodology notes) currently live in the internal HelpModal for fixture browsing. The live-check UI needs the same disclosures surfaced prominently — a first-time visitor checking their own document trusts a live result more literally than a blog/talk reader with full context.
- **Hidden context exposure (LLM08, renamed from System Prompt Leakage)**: pipeline errors returned to the client must be generic, never raw exception text or an echo of internal prompt content.
- **Improper output handling (LLM10, fell to #10)**: verify no Vue component renders AI-output/source-doc/rationale text via `v-html` — text interpolation (auto-escaped) only, everywhere user-controlled text is displayed. A miss here turns an adversarial upload into stored/reflected XSS.
- **Broken authentication (API2:2023)**: device tokens must be signed/unguessable, not sequential. A malformed BYO key fails cleanly, never gets logged.
- **Explicitly not applicable, stated rather than silently skipped**: Excessive Agency (LLM03) — the pipeline is fixed and read-only, no tool-calling; Vector/Embedding Weaknesses (LLM09) — GI's genesis design chose per-section map-reduce scanning over hierarchical RAG, sidestepping most of this category.
- **Forward caveat, not a build item now**: Data/Model Poisoning (LLM05) — if opt-in retention's stated purpose (building a fixture corpus from real usage) is ever acted on, a malicious submitter could deliberately poison that corpus. Relevant only if/when retained data is used for training or calibration.

**What this review is and isn't**: this is a design-time mapping against known risk categories, not a live penetration test. No automated pen-testing tooling is available in this environment. Once built, a manual scoped check against the live endpoint (verbose-error probes, CORS checks, injection payloads, malformed uploads) is feasible as pre-launch due diligence, but a real external pen test (or a much more adversarial pass than a single agent can credibly run) is warranted before wide promotion, given the stated ambition of a real recurring public tool over real documents.

## Privacy, Retention & Legal

- **Consent**: opt-in checkbox for retention, unchecked by default. Unchecking still gets the full check — nothing is kept unless explicitly opted in.
- **Storage**: retained documents live in the same Neon Postgres instance — no second storage system, bounded by the same size caps already required for cost control. Move to object storage only if real usage shows those caps are too tight for legitimate retained documents.
- **Deletion**: self-serve, tied to the same device token used for quota — a "manage your saved checks" view lets a user delete their own retained data without building an accounts system. State a retention ceiling (e.g. purged after 6 months) rather than keeping opted-in data indefinitely.
- **Encryption at rest**: already satisfied by Neon Postgres's defaults — no new work.
- **Not-advice disclaimer**: explicit and visible on the live-check UI itself (not just a README) — this is a research tool, not legal/financial/regulatory advice. Load-bearing given the domain (insurance PDS fixtures, the TGA regulatory-submissions research thread) and GI's own genesis decision to decline the assurance/consulting framing.
- **Lightweight terms**: borrowed near-verbatim from the reference UX pattern — "don't upload classified, sensitive, or personal information," no warranty, use-at-own-risk. A full ToS/privacy-policy page is more than this launch needs; upgrade only if uptake grows.

## Error Handling

- Quota-exceeded: specific, actionable message, never a bare 429.
- Pipeline failure (API error, timeout, malformed upload): generic client-facing message, no raw exception text; logged as an Umami event; triggers a Resend email alert.
- Upload validation: client-side for instant feedback, always re-checked server-side.
- BYO-key errors distinguished: malformed key vs. no credit vs. GI-side failure.
- Partial pipeline completion (e.g. comprehensiveness times out after decompose+verify succeed) returns partial results with a "some checks didn't complete" note, rather than discarding a request that already spent real API cost.

## Testing

- Extends GI's existing three-layer discipline (pytest / vitest / Playwright) — no new framework.
- New surface: quota/device-token logic (increment, burst limit, reset), BYO-key handling (assert the key never appears in logs), upload validation (oversized/wrong-type rejected), and real prompt-injection regression tests — a gap Act Alike's own extension plan left deferred and never built; non-optional here given the live path is genuinely public-facing.
- Live E2E (a real upload through the actual Modal deployment) matches Ching's established convention of pairing auto-run Playwright E2E with cleanup scripts, but each run costs real API money — gate the full-pipeline live E2E to a manual/pre-release trigger, with cheap mocked tests covering CI on every push.

## Open Items for Implementation Planning

- **Not actually open — resolved by review**: there is no document-ingestion layer anywhere in the repo today. `pipeline.py`/`label_claims()` only ever consumes pre-extracted `full_text` + pre-structured `sections` dicts; fixtures are hand-built via `build_fixtures.py`. An upload-parsing layer (even for plain text — extracting `full_text`/`sections` from a raw upload) is from-scratch build scope for cycle 1, not a confirm-and-maybe item.
- Confirm actual per-document latency on a real multi-page document to decide if sync-first is sufficient or the async upgrade is needed immediately.
- Decide the specific free-tier daily cap and per-IP burst ceiling numbers (informed by expected traffic, not fixed in this design).

## Suggested Build Sequencing

This is too large for one implementation plan — matches GI's own established pattern of separate build cycles per feature thread rather than one bundled plan. Suggested split, each its own spec-review-if-needed → plan → build cycle:

1. **Core live-check path**: Modal backend wrapping the existing pipeline, frontend upload/paste view, device-token quota, sync request/response. The MVP — nothing works publicly without this.
2. **Security hardening pass**: the prompt-injection audit across all live-path LLM calls, upload validation, `v-html` audit, server-side-only enforcement of limits. Should land before any public traffic, not after.
3. **BYO-key path**: unlocks usage beyond the free tier.
4. **Opt-in retention**: consent UI, storage, self-serve deletion, retention ceiling.
5. **Alerting**: Umami failure events + Resend email.

(1) and (2) are both prerequisites for any public launch; (3)-(5) can follow once the core path is live and validated. Note: the security section's BYO-key-specific requirements (malformed-key handling, burst limit applying to BYO traffic) are prerequisites *for phase 3 specifically*, not for the initial launch — they don't block (1)/(2) since no BYO-key path exists until phase 3 ships.
