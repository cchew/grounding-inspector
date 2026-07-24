---
marp: true
theme: default
size: 16:9
paginate: true
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400&display=swap');

:root {
  --color-background: #ffffff;
  --color-foreground: #1c1c1c;
  --color-heading: #111111;
  --color-muted: #888888;
  --color-rule: #e8e8e8;
  --color-accent: #0066cc;
  --font-default: 'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Consolas', monospace;
}

section {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-default);
  font-weight: 300;
  box-sizing: border-box;
  padding: 64px 80px 56px;
  font-size: 22px;
  line-height: 1.75;
}

section::after {
  font-size: 13px;
  color: var(--color-muted);
  font-family: var(--font-default);
  font-weight: 300;
}

h1, h2, h3 {
  font-family: var(--font-default);
  margin: 0;
  padding: 0;
  color: var(--color-heading);
}

h1 {
  font-size: 54px;
  font-weight: 300;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

h2 {
  font-size: 36px;
  font-weight: 400;
  letter-spacing: -0.01em;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-rule);
}

h3 {
  font-size: 21px;
  font-weight: 500;
  color: var(--color-accent);
  margin-top: 28px;
  margin-bottom: 8px;
}

ul, ol {
  padding-left: 24px;
  margin: 0;
}

li {
  margin-bottom: 10px;
  color: var(--color-foreground);
}

li strong {
  font-weight: 500;
  color: var(--color-heading);
}

p {
  margin: 0 0 14px;
}

code {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background-color: #f4f4f4;
  color: #333;
  padding: 2px 7px;
  border-radius: 3px;
}

pre {
  background-color: #f6f8fa;
  border: 1px solid var(--color-rule);
  border-radius: 4px;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 24px;
  line-height: 1.5;
}

pre code {
  background: none;
  padding: 0;
  border-radius: 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88em;
  font-weight: 300;
  margin-top: 8px;
}

th {
  font-weight: 500;
  font-size: 0.85em;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 14px;
  border-bottom: 1px solid var(--color-rule);
  text-align: left;
}

td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-rule);
  vertical-align: top;
}

/* Title / lead slide */
section.lead {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 80px;
  border-left: 3px solid var(--color-heading);
}

section.lead h1 {
  font-size: 58px;
  font-weight: 300;
  letter-spacing: -0.03em;
  margin-bottom: 24px;
  line-height: 1.15;
}

section.lead p {
  font-size: 20px;
  color: var(--color-muted);
  font-weight: 300;
  margin: 0;
  line-height: 1.6;
}

/* Section break slides */
section.break {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 80px;
  background-color: var(--color-heading);
  color: #ffffff;
}

section.break h1 {
  font-size: 48px;
  font-weight: 300;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
}

section.break p {
  font-size: 20px;
  color: rgba(255,255,255,0.55);
  margin: 0;
}

/* Appendix */
section.appendix h2 {
  color: var(--color-muted);
  font-size: 28px;
  border-bottom-color: #eeeeee;
}

/* Inline note / callout */
.note {
  border-left: 2px solid var(--color-rule);
  padding-left: 20px;
  color: var(--color-muted);
  font-size: 0.9em;
  margin-top: 20px;
}

/* Definition callout */
.def {
  border-left: 3px solid var(--color-accent);
  padding: 10px 18px;
  background: #f0f6ff;
  border-radius: 0 4px 4px 0;
  margin: 16px 0;
  font-size: 0.88em;
  color: var(--color-foreground);
}
</style>

<!-- _class: lead -->
<!-- _paginate: false -->

# Checking AI Claims Against Evidence

<br/>
One click. Every claim checked. No re-reading required.

Ching Chew · July 2026

<br/>

github.com/cchew/grounding-inspector

<!-- note:
Pre-show: deployed app open on the Budget Direct fixture, scorecard visible, help modal closed.

Open with the hook, don't put it on a slide:
"At the last few AI presentations I've been to, someone in Q&A always asks a version of the same question: we're told we can use AI, but we're still accountable for what it says. How do we do that without re-reading the 200-page report ourselves?"

Let the room sit with it for a second before moving to the next slide.
-->

---

## The Accountability Paradox

- You're told you can use AI
- You're still accountable for what it says
- The report is 200 pages; you have an afternoon
<br/>

**How do you check the parts that matter without reading everything?**

<!-- note:
Don't answer it. Let it sit. Everyone in the room has hit this, whether they call it that or not.

For execs: this is the governance gap they're already worried about: staff using Copilot/Claude with no way to verify output.
For devs: this is the eval gap: "I built a RAG pipeline" isn't the same as "I measured whether it's right."
-->

---

## Before / After

![bg left:50% contain](screenshots/two-pane-viewer.png)

**Before:** a paragraph of AI-generated text. Plausible. Confident. No way to tell which parts are backed by the source.

**After:** the same output, claim by claim (grounded, partial or unsupported). Click any claim to see its evidence.

<!-- note:
Let the screenshot do most of the work. Don't over-narrate this one.
The "before" is any AI summary tool your audience already uses: Copilot, ChatGPT, an internal RAG bot.
-->

---

<!-- _class: break -->
<!-- _paginate: false -->

# Live Demo

Budget Direct PDS Fixture

<!-- note:
1. Open the fixture: Budget Direct Comprehensive Travel Insurance PDS
2. Show the scorecard: 63/100, 2 grounded, 1 partial, 1 unsupported
3. Click the unsupported claim: "COVID-19 cancellations covered on the same basis as any other unforeseen event"
4. Point out: no matching span, evidence note explains the pandemic-exclusion clause contradicts it
5. Click a grounded claim for contrast; quote highlights directly in the source pane
6. This is decompose → verify → localise, running live, not precomputed for the demo
-->

---

## How It Works

![w:900](diagrams/component-flow.svg)

<div class="def"><strong>Entailment (NLI)</strong>: does the source text entail the claim, contradict it or say nothing about it? This is what the verifier scores, not "does this sound plausible."</div>

No retrieval step narrows the document first: every claim is checked against the whole source.

<!-- note:
For execs: "it reads the whole document, not just the bit a search index thinks is relevant."
For devs: MiniCheck (flan-t5-large) scores each atomic claim against every chunk, max-pooled. No retrieval gate: the recall trade-off is explicit, not accidental.
Teams/ADO Wiki adaptation: this pattern doesn't touch a chat platform at all; it evaluates a document pair, so the "trigger" is whatever produced the AI output (a Copilot session export, an internal RAG bot's answer log, an email).
-->

---

## Key Technical Decisions

### Decompose-then-verify, not hierarchical RAG
- Retrieval fetches the best chunk; grounding has to check every claim against everything
- A missed retrieval hit reads as "unsupported" for the wrong reason

### MiniCheck (local, free) vs Claude Haiku (cloud, paid)
- Same interface, swappable at runtime
- Validation run: $0 vs ~A$9 for n=300 documents

### Numeric-consistency as a deterministic pre-pass
- NLI can't do arithmetic: a transposed number can still look "entailed"
- Caught by a separate, deterministic check, not folded into the verifier

<!-- note:
For devs: decision 1 is the one worth defending in Q&A: "why not just use a vector DB?" The answer is recall, not laziness.
For execs: decision 3 is the governance-relevant one: a known, named blind spot with a documented fix, not a silent gap.
-->

---

## What It Measures

| Mode | Cost | Recall | Agreement (κ) |
|---|---|---|---|
| MiniCheck (default) | Free | 0.69 | 0.195 |
| Claude Haiku | ~A$0.05/doc | 0.90 | 0.331 |

<div class="def"><strong>Cohen's kappa (κ)</strong>: agreement with human judgment, corrected for chance, not raw accuracy. 0.195 is "slight agreement," 0.331 is "fair agreement" on the standard scale.</div>
<div class="def"><strong>RAGTruth</strong>: a published benchmark of labelled hallucinations in AI summaries (n=300 sampled here), not a number this project invented or self-labelled.</div>

**With those numbers in hand, the reading burden shrinks from the whole document to the flagged claims.**

<!-- note:
This is the evidence behind the earlier claim that this beats "I read it and it seemed fine"; that alternative has no error rate at all, because nobody measured it.
For execs: recall (not kappa) is the number that matters operationally: a missed hallucination costs more than a false alarm here.
-->

---

## SOTA: Why Not Just Use X

- **UK AISI's Inspect harness**: Grounding Inspector ships as a custom Inspect `Scorer`; it extends Inspect rather than competing with it
- **Numeric transposition**: open, field-wide gap; reference architecture: Proof-Carrying Numbers (arXiv:2509.06902)
- **Entity/citation substitution**: same structural cause as the numeric gap; reference architecture: HalluGraph (arXiv:2512.01659)
<br/>

**Both gaps are named here, not hidden.**

<!-- note:
Anticipates the question before it's asked. If someone in Q&A knows Inspect, this earns credibility rather than looking unaware of it.
Entity/citation substitution: an NLI verifier tolerates a swapped name or citation if the sentence shape still matches; same failure mode as the numeric gap, different span type.
-->

---

<!-- _class: break -->
<!-- _paginate: false -->

# Live Demo

The Numeric-Mismatch Catch

<!-- note:
Faster. Audience already understands the flow.
Show a claim where the stated dollar figure doesn't appear anywhere in the matched evidence.
Point out: this isn't the NLI verifier catching it; it's the separate deterministic numeric check, labelled honestly as an "automated numeric check" rationale, not dressed up as model reasoning.
-->

---

## Lessons Learnt

- κ=0.195 is an honest ceiling, not a marketing number
- MiniCheck doesn't do arithmetic: numeric-consistency is a bolt-on, not built in
- Entity/citation substitution is unsolved here too: same as the numeric gap, field-wide (see SOTA)
- Validated on RAGTruth's general-summarisation distribution, not measured on insurance/legal/regulatory text specifically

<!-- note:
"I'm showing you a pattern and being straight about where it ends."
For execs: this is what a defensible governance story looks like: known limits, named, with a documented fix path, not a claim of perfection.
-->

---

## The Bigger Pattern

![w:750](diagrams/pattern-flow.svg)

The same decompose-then-verify shape applies to:

- Regulatory submissions (TGA AusPARs, similar disclosure corpora)
- Legislative and policy text
- Contract and compliance review

<!-- note:
"So what" moment for executives: any long-document-plus-AI-output pairing in your own department fits this shape.
Seed the question: where in your team's workflow does an AI already summarise something someone else has to sign off on?
-->

---

## Conclusion

"The first principle is that you must not fool yourself, and you are the easiest person to fool."
- Richard Feynman
<br/>
- An honestly-measured verifier beats an unmeasured "it seemed fine"
- The ceiling is real. Say so. Ship it anyway.
<br/>
- Thank you for your time
- Feedback and comments: DM me via Teams or LinkedIn

<!-- note:
The Feynman line is doing the real work of this talk: the whole build is an argument against fooling yourself about output quality.
-->

---

<!-- _class: appendix -->
<!-- _paginate: false -->

## Appendix A: Audit Readiness

Three additions before a scorecard is defensible in an APS governance context (AI Impact Assessment, ANAO audit, Ministerial inquiry):

- **Version pinning**: log the engine version, MiniCheck model version and source document hash into every scorecard. Without it, a scorecard isn't reproducible.
- **Pre-stated pass/fail threshold**: a `min_grounded_pct` field, set before the test run. Post-hoc thresholds aren't defensible in an audit.
- **Scope declaration**: every report states plainly that unsupported claims have not been verified as false, only unverified against the given source.

<!-- note:
Cover only if time permits or directly asked: this is the SES/EL2 audience's slide, not the core dev talk.

The IMDA Model AI Governance Framework for Agentic AI (Jan 2026) names explainability and auditability as governance requirements. Decompose-then-verify satisfies both by construction: small, auditable verification units and an interpretable verifier judgment. This wasn't built to the framework; it happens to fit because it's what defensible engineering looks like anyway. Full paragraph in the blog post if asked for a citable source.
-->

---

<!-- _class: appendix -->
<!-- _paginate: false -->

## Appendix B: Verifier Benchmarking Detail

| Metric | MiniCheck | Claude Haiku |
|---|---|---|
| Recall | 0.69 (CI 0.59-0.78) | 0.90 (CI 0.82-0.95) |
| Cohen's κ | 0.195 | 0.331 |
| Balanced accuracy | 0.612 | n/a |
| False negatives | 31 / 100 positives | n/a |
| Decomposer | Ollama qwen2.5:7b-instruct | Claude Haiku 4.5 |
| Cost | Free, local | ~A$0.05/doc |

Both validated on RAGTruth, n=300, seed=0.

<!-- note:
Recall is the metric this tool prioritises: a missed hallucination (false negative) is costlier than a false alarm for this tool's intended use.
Balanced accuracy and false-negative counts are reported for MiniCheck only in the current benchmark run.
-->
