# Grounding Inspector

A Layer-3 groundedness evaluation tool for LLM outputs. Decomposes AI-generated text into atomic claims, verifies each claim against a source document using [MiniCheck](https://github.com/Liyan06/MiniCheck), and surfaces grounded / partial / unsupported verdicts in a two-pane inspector UI.

Built as a proof-of-concept in the travel insurance domain (Australian PDS documents), but the engine and fixture contract are domain-agnostic.

## What it does

1. **Decompose** — break an AI output into individual atomic claims
2. **Verify** — score each claim against all document chunks using MiniCheck (no retrieval gate; max-pool over the full document). This trades higher cost/latency at longer document lengths for exhaustive recall (no chunk is skipped by a retrieval step) — validated on short-to-medium documents (PDS-length, a few pages); a 100+ page document would need a retrieval pre-filter, which is not yet built or benchmarked.
3. **Label** — aggregate sub-claim scores into `grounded`, `partial`, or `unsupported`
4. **Localise** — map grounded claims back to the source span and page number
5. **Inspect** — browse results in a Vue 3 two-pane viewer (claim list left, source doc right, click-to-highlight)

Two experimental, unvalidated detectors additionally flag source content the output may have *left out* — see [Omission signals](#omission-signals).

## Architecture

```
fixtures/          JSON fixtures (source doc + AI output + labelled claims + scorecard)
contract/          fixture.schema.json — shared JSON Schema between engine and web
engine/
  grounding/       Python pipeline (decompose, verify, label, localise, metrics)
  tests/           pytest unit tests
  notebook/        validation.ipynb — RAGTruth benchmark runner (Ollama-backed)
web/
  src/             Hono API server + Vue 3 frontend
  tests/           Vitest unit tests + Playwright E2E
```

## Fixtures

| ID | Source | Type |
|----|--------|------|
| `travel-pds-01` | SunSafe Travel Insurance PDS (synthetic) | 3 claims — grounded / partial / unsupported |
| `travel-pds-02` | Blue Pacific Travel PDS (synthetic) | cancellation and delay edge cases |
| `travel-pds-03` | Alpine Trek PDS (synthetic) | winter sports / exclusion edge cases |
| `covermore-pds-01` | Cover-More Comprehensive Travel PDS (Oct 2025, real) | Australian PDS real-world fixture |
| `budgetdirect-pds-01` | Budget Direct Comprehensive Travel Insurance PDS (Feb 2025, real) | Australian PDS real-world fixture |

## Getting started

### Engine

Requires Python 3.11+.

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

> **macOS 26 Tahoe (Darwin 25) note:** PyTorch >= 2.4 wheels are not yet published for this platform. `requirements.txt` pins `numpy<2` and `transformers==4.45.2` to maintain compatibility with the highest available torch (2.2.2). Remove those pins once torch 2.4+ ships for your platform.

### MiniCheck model weights

MiniCheck downloads `flan-t5-large` (~300 MB) to `engine/ckpts/` on first use. The `ckpts/` directory is gitignored — weights are never committed. Subsequent runs load from the cache.

### Web

Requires Node 20+.

```bash
cd web
npm install
npm run build          # compile Vue frontend into dist/
npm run serve          # start Hono server on http://localhost:3000
```

Or run frontend in dev mode (with hot reload) against a running server:

```bash
npm run serve &        # API server on :3000
npm run dev            # Vite dev server on :5173
```

### Deployment

`netlify.toml` deploys the built `web/` app statically.

## Verifier modes

The pipeline supports two verifier backends, selectable at runtime:

| Mode | Verifier | Decomposer | Cost | Recall | κ |
|------|----------|------------|------|--------|---|
| `minicheck` (default) | MiniCheck flan-t5-large (local) | Ollama qwen2.5:7b-instruct | free | 0.69 | 0.195 |
| `haiku` | Claude Haiku 4.5 (API) | Claude Haiku 4.5 (API) | ~$0.03/doc | 0.90 | 0.331 |

κ (Cohen's kappa) measures agreement with human judgment beyond chance:
0.195 is "slight agreement" and 0.331 is "fair agreement" per the standard
Landis & Koch scale. Recall is the metric this tool prioritises, since a
missed hallucination (false negative) is costlier than a false alarm for
this tool's intended use.

Both validated on RAGTruth n=300, seed=0.

**Default (MiniCheck)** — no API key required, fully local:
```python
from grounding.validate import run_sample
run_sample(n=300, verifier="minicheck")
```

**Claude Haiku** — set `ANTHROPIC_API_KEY` in `engine/.env` or `repo/.env`:
```python
run_sample(n=300, verifier="haiku")
# or from the command line:
python pilot_claude.py 300
```

To use Haiku in `label_claims` (fixture generation):
```python
from grounding.verify import make_claude_verifier
from grounding.pipeline import label_claims
verifier_fn = make_claude_verifier()
claims = label_claims(decomposed, full_text, sections, verifier_fn)
```

### RAGTruth validation

`engine/notebook/validation.ipynb` re-runs the benchmark. MiniCheck mode requires Ollama (`ollama pull qwen2.5:7b-instruct`); Haiku mode requires `ANTHROPIC_API_KEY`.

```bash
# MiniCheck (local, free, ~30-60 min)
python -c "from grounding.validate import run_sample; print(run_sample(n=300))"

# Claude Haiku (~35 min, ~$6 USD for n=300)
python pilot_claude.py 300
```

## Inspect integration

`engine/grounding` is also wrapped as a custom [UK AISI Inspect](https://github.com/UKGovernmentBEIS/inspect_ai) `Scorer` (`grounded_claim_scorer()` in `engine/grounding/inspect_scorer.py`), giving the pipeline interoperability with Inspect's task runner and eval log. `inspect_ai` is a documented ad-hoc install, not a pinned dependency in `requirements.txt` — it stays out of the engine's default install.

```bash
cd engine
source .venv/bin/activate
pip install inspect_ai
PYTHONPATH=. inspect eval grounding/inspect_demo.py
```

`PYTHONPATH=.` is required — Inspect's task loader doesn't add `engine/` to `sys.path` the way pytest's `conftest.py` does, so the bare command fails with `ModuleNotFoundError: No module named 'grounding'`.

The demo (`engine/grounding/inspect_demo.py`) wraps the 5 existing fixtures as `Sample`s. Its solver copies each fixture's precomputed `ai_output` into `state.output` (no live model call — the fixtures are precomputed offline); the scorer then re-decomposes and re-verifies live against local Ollama + MiniCheck on every run (it never replays a fixture's precomputed `claims`). Verified run: 5 samples, mean 0.352, stderr 0.121.

`grounded_claim_scorer(verifier="minicheck")` (default) routes to the same local, free verifier path as the rest of the pipeline; `verifier="haiku"` swaps in `make_claude_verifier()` — decomposition still runs locally via Ollama either way.

## Omission signals

Groundedness answers "is what the output says supported?". It says nothing about what the output left out. Two experimental omission detectors address that, and a fixture can carry either, both, or neither in its optional `omissions[]` array — one entry per method, rendered as its own panel in the inspector.

| Method | How it works | Cost | Flags a section when |
|--------|--------------|------|----------------------|
| `embedkde` | Embeds source and output tokens with a pretrained FastText model, PCA-reduces, and scores each source token by KDE density ratio against the output distribution | free, local (downloads a ~1GB gensim model on first run) | its top token score exceeds mean + 1.5σ across scored sections |
| `comprehensiveness_qa` | Decomposes each source section into subclaims, generates a closed question per subclaim, then asks the model whether the output answers it | real Claude API calls (Sonnet) per subclaim — real cost and latency | any one subclaim is judged `OMITTED` (`flag_threshold=0.0`) |

**Both are unvalidated.** No ground-truth omission labels exist for these fixtures, so neither has a measured recall or precision. Every entry carries `"validated": false` and a `caveat` string that the UI renders next to the panel rather than hiding in the JSON. Treat a flagged span as a prompt to read the source, not a finding. Note also that an AI summary is far shorter than its source and will legitimately omit most source facts by construction — a high `comprehensiveness_qa` flag rate reflects that, not necessarily a detector fault.

`global_score` is **not comparable across methods**: `embedkde`'s is an unbounded density ratio, `comprehensiveness_qa`'s is a 0-1 fraction of subclaims omitted. Never rank or threshold fixtures on it across methods.

### Running the detectors

`comprehensiveness_qa` is the only thing in this repo that spends real API money, so it is opt-in at two independent layers:

1. **Method flag** — `add_omissions.py` defaults to `embedkde` only. No LLM call fires unless `comprehensiveness_qa` is named explicitly.
2. **Structural guard** — `check_omissions_comprehensiveness_qa()` raises unless called with `allow_llm_calls=True`, so importing and calling it directly cannot incur spend by accident.

```bash
cd engine
source .venv/bin/activate

python notebook/add_omissions.py                                    # embedkde only, free (default)
python notebook/add_omissions.py --methods embedkde comprehensiveness_qa   # billed
```

Requires `ANTHROPIC_API_KEY` in `engine/.env` or `repo/.env` for the billed path. The run regenerates all five fixtures in memory and only writes once every fixture succeeds, so a mid-run API failure leaves the committed fixtures untouched rather than half-updated. Non-omissions fields are asserted byte-for-byte unchanged before any write.

## Fixture contract

Each fixture is a JSON file conforming to `contract/fixture.schema.json`. Key fields:

- `source.sections[]` — document chunks with `id`, `page`, `char_start`, `char_end`, `text`
- `ai_output` — the LLM-generated text under evaluation
- `claims[]` — labelled claims with `label` (`grounded` | `partial` | `unsupported`), `evidence_span_ids`, `quote`, `page`, `rationale`
- `groundedness` — aggregate score (0–100) and counts
- `scorecard` — recall, CI, false negatives, and domain note
- `omissions[]` — optional; one entry per detector (`embedkde` | `comprehensiveness_qa`), each with `global_score`, `flagged_sections[]`, `hyperparameters`, `validated`, and `caveat`. The schema branches on `method`: `flagged_sections[]` carries `top_tokens` for `embedkde` and `omitted_facts` for `comprehensiveness_qa`, and cross-method shapes are rejected

## License

MIT
