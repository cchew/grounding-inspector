<script setup lang="ts">
import { computed } from "vue";
import type { Fixture, Label } from "../types";

const props = defineProps<{ fixture: Fixture; open: boolean }>();
defineEmits<{ close: [] }>();

function exampleFor(label: Label) {
  return props.fixture.claims.find((c) => c.label === label) ?? null;
}
const groundedExample = computed(() => exampleFor("grounded"));
const partialExample = computed(() => exampleFor("partial"));
const unsupportedExample = computed(() => exampleFor("unsupported"));
</script>

<template>
  <div v-if="open" data-testid="help-modal" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-panel" role="dialog" aria-modal="true" aria-label="How Grounding Inspector works">
      <button data-testid="help-close" class="modal-close" @click="$emit('close')" aria-label="Close">✕</button>

      <section class="modal-section">
        <h2>What this measures</h2>
        <p>AI-generated text can state things that sound plausible but aren't actually backed by the source document it's supposed to be summarising. Grounding Inspector checks each claim in an AI output against the source document, and shows you which claims are backed by evidence, which are partially backed, and which have no supporting evidence at all.</p>
      </section>

      <section class="modal-section">
        <h2>Verdict legend</h2>
        <dl class="legend-list">
          <div class="legend-row">
            <dt><span class="label-chip grounded">✓ grounded</span></dt>
            <dd>
              Every part of the claim is directly stated in the source.
              <template v-if="groundedExample"><br><em>Example from this fixture:</em> "{{ groundedExample.text }}"</template>
            </dd>
          </div>
          <div class="legend-row">
            <dt><span class="label-chip partial">~ partial</span></dt>
            <dd>
              Some but not all of the claim is supported — a detail is wrong, omitted, or overstated.
              <template v-if="partialExample"><br><em>Example from this fixture:</em> "{{ partialExample.text }}"</template>
            </dd>
          </div>
          <div class="legend-row">
            <dt><span class="label-chip unsupported">✗ unsupported</span></dt>
            <dd>
              No matching evidence was found in the source document.
              <template v-if="unsupportedExample"><br><em>Example from this fixture:</em> "{{ unsupportedExample.text }}"</template>
            </dd>
          </div>
        </dl>
      </section>

      <section class="modal-section">
        <h2>How the score is calculated</h2>
        <p>Each claim is weighted: grounded = 1 point, partial = 0.5 points, unsupported = 0 points. The score is the average across all claims in the output, out of 100.</p>
      </section>

      <section class="modal-section">
        <h2>Verifier comparison</h2>
        <table class="verifier-table" data-testid="verifier-table">
          <thead><tr><th>Mode</th><th>Cost</th><th>Recall</th><th>Agreement (κ)</th></tr></thead>
          <tbody>
            <tr>
              <td>MiniCheck (default)</td>
              <td>Free, local</td>
              <td>0.69 (CI 0.59–0.78)</td>
              <td>0.195 — "slight agreement" (Landis &amp; Koch)</td>
            </tr>
            <tr>
              <td>Claude Haiku</td>
              <td>~$0.03/doc</td>
              <td>0.90 (CI 0.82–0.95)</td>
              <td>0.331 — "fair agreement" (Landis &amp; Koch)</td>
            </tr>
          </tbody>
        </table>
        <p class="modal-note">Recall is prioritised over agreement because a missed hallucination (false negative) is costlier than a false alarm for this tool's intended use.</p>
      </section>

      <section class="modal-section">
        <h2>Known limitations</h2>
        <ul>
          <li><strong>Document length.</strong> This tool checks every claim against the entire document rather than retrieving relevant sections first, so it doesn't miss evidence a retrieval step might filter out — but cost and latency grow with document length. Validated on short-to-medium documents; very long documents (100+ pages) would need a retrieval pre-filter, not yet built.</li>
          <li><strong>Domain.</strong> The recall/agreement numbers above are measured on RAGTruth, a general summarisation benchmark — not on insurance, legal, or regulatory text. The travel-insurance fixtures shown here are illustrative, not a validated domain.</li>
          <li><strong>Numbers.</strong> A deterministic check flags when a claim states a figure that doesn't appear anywhere in its matched evidence. This runs alongside the main verifier for the fixtures shown here; it is not part of the RAGTruth-validated pipeline above.</li>
          <li><strong>Fixture provenance.</strong> The AI-generated text in the three synthetic fixtures was produced from a documented prompt (see the repository README); the two real fixtures use unmodified excerpts from published PDS documents.</li>
        </ul>
      </section>

      <section class="modal-section">
        <h2>Scope</h2>
        <p class="scope-declaration" data-testid="scope-declaration">Unsupported claims have not been verified as false. Claims are evaluated only against the provided source document(s). Claims that are true but absent from the source will be classified as unsupported.</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: var(--s-5);
}

.modal-panel {
  position: relative;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md, 0 4px 24px rgba(0,0,0,0.2));
  max-width: 640px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: var(--s-6) var(--s-5);
}

.modal-close {
  position: absolute;
  top: var(--s-4);
  right: var(--s-4);
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-ink-3);
  cursor: pointer;
}

.modal-section { margin-bottom: var(--s-5); }
.modal-section h2 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: var(--s-2);
  color: var(--color-ink);
}
.modal-section p, .modal-section li {
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--color-ink-2);
}
.modal-section ul { padding-left: var(--s-4); }
.modal-section li { margin-bottom: var(--s-2); }

.legend-list { display: flex; flex-direction: column; gap: var(--s-3); }
.legend-row { display: flex; flex-direction: column; gap: var(--s-1); }
.legend-row dd { font-size: 0.8125rem; color: var(--color-ink-2); }
.legend-row em { color: var(--color-ink-3); font-style: italic; }

.label-chip {
  font-size: 0.75rem;
  font-weight: 500;
  padding: var(--s-1) var(--s-3);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  display: inline-block;
}
.label-chip.grounded  { background: var(--chip-grounded-bg);    color: var(--chip-grounded-text);    border-color: var(--chip-grounded-border); }
.label-chip.partial   { background: var(--chip-partial-bg);     color: var(--chip-partial-text);     border-color: var(--chip-partial-border); }
.label-chip.unsupported { background: var(--chip-unsupported-bg); color: var(--chip-unsupported-text); border-color: var(--chip-unsupported-border); }

.verifier-table { width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-bottom: var(--s-2); }
.verifier-table th, .verifier-table td { text-align: left; padding: var(--s-2) var(--s-3); border-bottom: 1px solid var(--color-border-light); }
.verifier-table th { color: var(--color-ink-3); font-weight: 600; text-transform: uppercase; font-size: 0.6875rem; letter-spacing: 0.06em; }

.modal-note { font-size: 0.75rem; color: var(--color-ink-3); font-style: italic; }

.scope-declaration {
  font-size: 0.75rem;
  color: var(--chip-partial-text);
  background: var(--chip-partial-bg);
  border: 1px solid var(--chip-partial-border);
  border-radius: var(--radius-sm);
  padding: var(--s-3);
}
</style>
