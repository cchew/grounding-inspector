# Grounding Inspector: Live-Check Close-Out / Hardening (Cycle 3) — Design

**Date:** 2026-08-28
**Status:** Draft, pending review before implementation planning
**Predecessors:** cycle 1 (core live-check path, `2026-08-26-live-check-core-path.md`), cycle 2 (security hardening, `2026-08-28-live-check-security-hardening.md`). Both shipped and deployed; `v0.3.0` tagged and pushed.

## Purpose

The public live-check path (`POST /check` on Modal, upload view on Netlify) is live end-to-end with no email gate. A three-lens review (end user, UX, ML) plus one real happy-path probe against the deployed backend surfaced a set of defects that are individually small but collectively keep the tool from being safe to leave running unattended: dead-end navigation, an unvalidated score presented with no visible caveat, no progress feedback on an 18s+ request, and a click-to-locate interaction that does nothing for the two most likely upload types.

This cycle closes those out plus the cheap residuals parked from the cycle-2 reviews. It deliberately builds **no new subsystem** — no async job queue, no BYO-key path, no retention. Those remain separate future cycles.

## Real probe result (2026-08-28, informs this design)

One live check against `https://ching-automation--grounding-inspector-live-api.modal.run/check`: 815-char TXT, 5 claims, `text/plain` upload. HTTP 200 in **18.3s**. Verdicts were accurate (2 grounded, 1 partial correctly catching an overstatement, 2 unsupported). Two things were visibly wrong in the response:

- Every grounded/partial claim returned `evidence_span_ids: ["s1"]` with `quote` = the first 80 chars of the document (`"Section 4 - Overseas medical and hospital\nOverseas medical and hospital expenses"`), regardless of the claim. The TXT ingestion path produces exactly one section, so localisation is degenerate.
- `partial` claim `c3` returned `rationale: ""` — the least self-explanatory label with no explanation.

The verification engine is trustworthy on this evidence. The presentation layer around it is not.

## Scope

**In:** P0 items A–D and cheap P1 items 1–7 below, plus the docs/housekeeping pass.

**Out, stated explicitly:**

- **Async submit/poll pattern.** Sync request/response is kept. Latency is addressed with a client-side timeout and honest copy only. A real multi-page PDS may still time out; the async rebuild is a later cycle.
- **Haiku evidence-span self-report.** The "Localise/Verifier Disconnect — Haiku half" (`FUTURE.md`) stays deferred; it needs its own design decision (self-report span vs. re-architecture to per-chunk scoring). This cycle mitigates the symptom (section split + an "approximate location" hedge on live results), not the cause.
- **Responsive `Inspector` two-pane**, keyboard operability of claim/omission rows, `aria-live` announcements, and a gated real-backend Playwright run. All P2, next cycle. There are zero `@media` queries in `web/src` today; fixing that is a layout pass of its own.
- **A distinct "contradicts source" label.** The three-label taxonomy (`grounded`/`partial`/`unsupported`) is unchanged. The reliability banner wording will make clear that `unsupported` means "no support found", not "verified false".

## Design

Repo paths are relative to `projects/grounding-inspector/repo/`. Build via subagent-driven-development on `main` (no worktree, per repo precedent), TDD per task.

---

### P0-A. Navigation + result lifecycle

**Current state.** `web/src/App.vue:10` holds `const mode = ref<"upload" | "browse">("upload")`. `switchToBrowse()` (`App.vue:31-37`) sets `mode.value = "browse"` and there is no function anywhere that sets it back. In browse mode the header renders only the fixture buttons (`App.vue:93-100`) and a "Take the tour" link. After a live check, `Inspector` renders with `liveResult` (`App.vue:108`) and there is no control to clear it. Both states are escapable only by a full page reload, which discards the pasted AI output.

**Change.**

- Add a persistent header control, visible in **every** state, offering both destinations: "Check a document" and "Browse samples" (rendered as two buttons or a segmented control; the active one is marked and inert).
- "Check a document" from any state: `mode.value = "upload"`, `liveResult.value = null`. Leave `selectedId` / `fixture` untouched so returning to "Browse samples" restores the last-viewed sample without a re-fetch.
- "Browse samples" keeps its current behaviour (`switchToBrowse`), which already defaults `selectedId` to the first fixture when none is selected.
- The existing inline "No document handy? Try a sample fixture instead." link in `UploadView.vue:65-67` stays as a secondary affordance on the upload view.

**Files.** `web/src/App.vue` (template + one new handler). `UploadView.vue` unchanged.

**Tests.** `web/tests/e2e-live-check.spec.ts`: (a) sample link → browse → header "Check a document" → upload view visible again; (b) mocked live result → "Check a document" → `UploadView` visible and `liveResult`-driven `Inspector` gone; (c) both nav controls present in upload, live-result, and browse states. Update `web/tests/App.test.ts` for the new header control.

---

### P0-B. Live-result reliability banner (OWASP LLM07)

**Current state.** `web/src/live-check-api.ts:23-27` already builds a `live_disclosure` string on the returned `Fixture`. It is rendered **only** inside `HelpModal.vue:94` ("Known limitations" list, section 6 of 7), which the user must click "?" to open. `Inspector.vue` never references `live_disclosure` (confirmed: only `App.vue`, `HelpModal.vue`, `live-check-api.ts`, `types.ts` mention it). The scorecard's large `NN/100` (`Inspector.vue:51-54`) renders for a live result with no visible caveat. The `low-n-note` (`Inspector.vue:49`) shows only when `claims.length < 5` and speaks to sample size, not verifier reliability.

**Change.**

- In `Inspector.vue`, when `props.fixture.live_disclosure` is set, render a non-dismissable caveat band immediately above or inside the output scorecard. Visual treatment matches the existing `.omissions-panel-heading` "experimental, unvalidated" note (dashed/muted, `--color-ink-3`), not an error style.
- Copy (final wording to be set in the plan, this is the intent): "This result comes from a verifier configuration (Claude Haiku reading the whole document) that has no independent accuracy measurement. The published recall / agreement figures cover a different verifier on the sample fixtures. Treat this as a research signal, not a validated score." Link "how this works" to the Help modal.
- Reuse the `live_disclosure` string; do not duplicate the text in the component. If the copy above supersedes the current `live-check-api.ts` string, update it there so the modal and the band stay identical.

**Files.** `web/src/components/Inspector.vue` (conditional band + scoped style). `web/src/live-check-api.ts` (copy only, if changed).

**Tests.** `web/tests/inspector.test.ts`: band renders iff `live_disclosure` is set; absent for a normal fixture. `web/tests/e2e-live-check.spec.ts`: after a mocked live result the band text is visible without opening Help.

---

### P0-C. Progress + timeout on the check request

**Current state.** `web/src/live-check-api.ts:10` issues a bare `fetch` with no timeout. `UploadView.vue` toggles a `loading` boolean that only swaps the button label to "Checking..." (`UploadView.vue:59-61`). The real probe took 18.3s for a trivial input; a 40-page PDS at 30+ subclaims with full-document context per verify call is plausibly 60–120s. There is no spinner, no elapsed indicator, no upper bound, and no timeout message.

**Change.**

- `live-check-api.ts`: wrap the `fetch` in an `AbortController` with a timeout (default 90_000 ms; name the constant). On abort, throw `Error` with a specific message: "The check is taking longer than expected. Try a shorter passage or a smaller document." Distinguish this from a network error and from an HTTP error body.
- `UploadView.vue`: while `loading`, show a spinner and the line "Checks can take up to a minute on long documents." plus an elapsed-seconds counter (`setInterval`, cleared on settle/unmount).
- On any failure, retain both inputs: the textarea already survives (`v-model`); keep `file.value` set rather than relying on the native input, and surface the existing filename so the user can resubmit without re-selecting.

**Files.** `web/src/live-check-api.ts`, `web/src/components/UploadView.vue`.

**Tests.** `web/tests/live-check-api.test.ts`: a slow/never-resolving mocked fetch triggers the abort path with the timeout message; an HTTP 502 body still surfaces its `detail`. `web/tests/UploadView.test.ts`: spinner + copy present while loading; after an error, `aiOutput` and the chosen file are both still populated.

---

### P0-D. Section-split TXT and DOCX in ingestion

**Current state.** `engine/grounding/ingest.py:43-47` (`extract_plain_text`) and `ingest.py:33-40` (`extract_docx`) each return a single-element list — one section covering the entire document, `id="s1"`, `page=1`. `extract_pdf` (`ingest.py:20-30`) already produces one section per non-blank page. With one section, `pipeline.label_claims` (`pipeline.py:54-64`) resolves every grounded/partial claim to that single section and `quote = span["text"][:80]` (`pipeline.py:89`) is always the document's first 80 characters. The two-pane click-to-locate interaction — GI's core UX — does nothing useful for TXT or DOCX.

**Change.**

- `extract_plain_text`: split the text on runs of two or more newlines (`re.split(r"\n\s*\n+", text)`), strip each block, drop empties, emit one section per block with `id` `s1`, `s2`, … and `page=1`. A document with no blank-line breaks still yields a single section (behaviour unchanged for that input).
- `extract_docx`: build the same blocks from `doc.paragraphs`. Group consecutive non-empty paragraphs; a blank paragraph (or a heading-styled paragraph, if cheap to detect via `p.style.name`) starts a new section. If heading detection adds meaningful complexity, fall back to blank-paragraph grouping only and note it. `page=1` for all (DOCX has no pagination without rendering).
- Keep `char_start=0`, `char_end=len(text)` per section (these fields are page-relative and only consumed defensively — `localise.section_char_ranges` locates sections by substring search, `localise.py:26-33`).
- The existing `MAX_EXTRACTED_CHARS = 60_000` total check (`ingest.py:82-84`) and the empty-result guard (`ingest.py:85-86`) are unchanged and now sum across sections.
- No heading-aware sectioning beyond the optional DOCX style check; richer structure detection is a later refinement.

**Downstream.** `span_from_chunk_index` and `best_span` already handle multi-section input. `live.py`'s `full_text` join is changed in P1-4 below. No API-layer change.

**Files.** `engine/grounding/ingest.py`; `engine/tests/test_ingest.py`.

**Tests.** `test_ingest.py`: a three-paragraph TXT → three sections with sequential ids; a single-paragraph TXT → one section; a DOCX with blank-line-separated blocks → multiple sections; the `MAX_EXTRACTED_CHARS` total still trips across sections; a whitespace-only document still raises.

---

### P1 — cheap residuals (already scoped in `FUTURE.md` "Cycle 3 backlog")

**1. `verify.py` verdict parse → exact match.**
`verify.py:60` is `return msg.content[0].text.strip().upper().startswith("SUPPORTED")`. With `max_tokens=10` a reply beginning "SUPPORTED, because…" is truncated and still matches. Change to `== "SUPPORTED"` (fail-closed direction unchanged: anything else → unsupported). Update `engine/tests/test_verify.py` and any `test_prompt_injection.py` case asserting the loose form.

**2. `_VERIFY_SYSTEM` version marker.**
`decompose.py:5-6` opens with `"PROMPT v3 (fixed; changing this changes scores …)"`. `verify.py:3-12` (`_VERIFY_SYSTEM`) has no equivalent, so its cycle-2 wording change is untracked. Prepend `"VERIFY PROMPT v2 (fixed; changing this changes scores)."` and add a test asserting the marker string is present (mirrors the decompose structural check). Adding the marker is itself a prompt edit — acceptable and now recorded.

**3. `_TAG_BREAK` tag-name guard test.**
`prompt_safety.py:16` hard-codes `_TAG_BREAK = re.compile(r"<\s*/?\s*(candidate_text|claim|document_context)\s*>", re.I)`. The wrapper tags are constructed in `decompose._wrap` (`<candidate_text>`) and `verify.verify_subclaim_claude` (`<claim>`, `<document_context>`). Add a test that extracts the tag names literally used in those prompt f-strings and asserts each appears in the `_TAG_BREAK` alternation, so a future fourth wrapper tag that is not added to the regex fails CI. Test-only, zero runtime change.

**4. `live.py` full-text join.**
`live.py:49` is `full_text = "".join(s["text"] for s in sections)` — adjacent PDF pages (and, after P0-D, adjacent TXT/DOCX blocks) concatenate with no separator, creating false token adjacency at boundaries and feeding `chunk_document`'s fixed 1000-char windows a corrupted stream. Change to `"\n\n".join(...)`. Verify `localise.section_char_ranges` still resolves every section (it searches for `s["text"]` verbatim with a moving cursor, so an inserted separator between sections is fine). Fix any test asserting the old concatenation.

**5. `_looks_like_text` encoding tolerance.**
`ingest.py:50-58` decodes as UTF-8 with `errors="replace"` and rejects when the `�` ratio exceeds 10%. A UTF-16 (BOM) or Latin-1 text file — common from Windows editors — is rejected despite being valid text. Change: sniff a UTF-16 BOM (`\xff\xfe` / `\xfe\xff`) and decode accordingly; if UTF-8 fails the ratio test, retry as Latin-1 and accept when the result is predominantly printable; reject only genuinely binary input. `extract_reference_document` must decode with the detected encoding, not a hard-coded `utf-8` (`ingest.py:78`). Tests: UTF-16 BOM file and a Latin-1 accented file both accepted; a random-bytes `.txt` still rejected.

**6. `partial` rationale on the live path.**
`pipeline.label_claims` sets `rationale = ""` (`pipeline.py:65`) and only fills it on a `Contradicted` numeric result (`pipeline.py:71`). A `partial` verdict from mixed subclaim results ships with no explanation. When `label == "partial"` and no numeric rationale was set, populate a short factual line, e.g. "Some checkable parts of this claim were supported by the source and some were not." Keep the numeric rationale when present (it already wins). `SourceDoc.vue:30-32` already renders `rationale` as an "Evidence note". Tests in `engine/tests/test_pipeline.py`.

**7. Omission-parity note on live results.**
`run_live_check` returns no `omissions` (`live.py:63-68`), so the "Possible Omissions" panel is absent for live checks with no explanation. In `Inspector.vue`, when `live_disclosure` is set and `fixture.omissions` is empty, render one muted line: "Omission analysis runs on the sample fixtures only." Test in `web/tests/inspector.test.ts`.

---

### Docs / housekeeping

- `projects/grounding-inspector/FUTURE.md`: move items 1–8 of the "Cycle 3 backlog" to done/superseded as this cycle lands them; correct the stale "Git push of `1ed711f..eec8f02` to origin is still a separate decision" and "still untracked from cycle 1" bullets — both are done (`main` is level with `origin/main`, `v0.3.0` tagged, cycle-1 plan/spec committed at `35cc09f`). Items deliberately **not** taken this cycle (`MAX_CONTEXT_CHAR_BUDGET` cost reconciliation, decomposer-call-before-guards, `logger.exception` message rendering, plan/spec self-review amendments) stay listed with a note that cycle 3 skipped them.
- `README.md`: state that TXT and DOCX uploads are now split into sections on blank-line boundaries; state that the live path returns no scorecard by design.
- Version: bump `web/package.json` `0.3.0` → `0.4.0` and the README version references; annotated `v0.4.0` tag, `v`-prefixed, per repo tag convention. Capture the prior tag SHA before any retag.

## Testing

Extends the existing three-layer discipline — `pytest` (engine), `vitest` + `@playwright/test` mocked (web). No new framework. Engine currently 218 pytest / 12 skipped; web 52 vitest; all green at `v0.3.0`. Every task is CI-safe with mocked clients — no task needs real API spend.

## Build sequencing

Independent, any order: P0-A, P0-B, P0-D, P1-1, P1-2, P1-3, P1-5.
P0-C touches `live-check-api.ts` + `UploadView.vue` together — one task.
P1-4 (`live.py` join) and P1-6 (`pipeline.py` rationale) both touch the engine pipeline path — sequence or hand to one agent.
P1-7 depends on P0-B (same `Inspector.vue` conditional block).
Docs/version bump last.

Final whole-branch review (Opus) + at most one fix wave, per this repo's subagent-driven-development rule. Then, checkpoint-gated (shared Modal + Neon): `modal deploy` and a real happy-path probe mirroring the 2026-08-28 probe (clean TXT, clean multi-page PDF, one oversized/wrong-type upload), plus `/docs` still 404 and CORS still scoped. Confirm the section split produces claim-relevant quotes on the live TXT probe.

## Open questions for the plan author

1. **DOCX heading detection (P0-D).** Use `p.style.name.startswith("Heading")` to start sections, or blank-paragraph grouping only? Recommendation: try the style check; if it complicates the split, ship blank-paragraph grouping and note the limitation.
2. **Timeout value (P0-C).** 90s client-side. Modal's own request timeout is not pinned in `modal_app.py` as read — confirm the platform default exceeds 90s so the client aborts first with the friendly message rather than the connection dropping. If Modal cuts sooner, set the client timeout just under it.
3. **Reliability-banner copy (P0-B).** Final wording, and whether it also appears (smaller) on the upload view before a check, or only on the result. Recommendation: result only — the upload view's job is to get input, and the Help button is present there.
4. **`live_disclosure` as the single source of copy.** If P0-B rewrites the text, it lives in `live-check-api.ts` and the component reads it. Confirm no test asserts the current exact string beyond a substring match.
