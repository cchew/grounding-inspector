<script setup lang="ts">
import { ref, onUnmounted } from "vue";
import type { Fixture } from "../types";
import { checkDocument } from "../live-check-api";
import { track } from "../analytics";

const emit = defineEmits<{ result: [Fixture]; browseSample: [] }>();

const aiOutput = ref("");
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const elapsed = ref(0);
let progressTimer: ReturnType<typeof setInterval> | undefined;

onUnmounted(() => clearInterval(progressTimer));

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
}

async function submitCheck() {
  if (!aiOutput.value.trim() || !file.value) {
    error.value = "Paste the AI output and choose a reference document first.";
    return;
  }
  loading.value = true;
  error.value = null;
  elapsed.value = 0;
  progressTimer = setInterval(() => { elapsed.value += 1; }, 1000);
  try {
    const fixture = await checkDocument(aiOutput.value, file.value);
    track("live_check_submitted");
    emit("result", fixture);
    // Clear the draft only on success. <KeepAlive> in App.vue caches this
    // component, so without this a user who reopens "Check a document" and
    // hits submit silently re-runs the identical paid Claude check. The
    // <input type=file> DOM node is preserved by KeepAlive too, so its
    // native .value must be cleared explicitly.
    aiOutput.value = "";
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Check failed. Please try again.";
  } finally {
    loading.value = false;
    clearInterval(progressTimer);
  }
}
</script>

<template>
  <div class="upload-view">
    <label class="field-label" for="ai-output-input">AI output to check</label>
    <textarea
      id="ai-output-input"
      data-testid="ai-output-input"
      v-model="aiOutput"
      class="ai-output-textarea"
      placeholder="Paste the AI-generated text you want to check for grounding..."
      rows="6"
    ></textarea>

    <label class="field-label" for="reference-file-input">Reference document (PDF, DOCX, or TXT)</label>
    <input
      id="reference-file-input"
      ref="fileInput"
      data-testid="reference-file-input"
      type="file"
      accept=".pdf,.docx,.txt"
      @change="onFileChange"
    />

    <button
      data-testid="submit-check"
      class="submit-btn"
      :disabled="loading || !aiOutput.trim() || !file"
      @click="submitCheck"
    >
      {{ loading ? "Checking..." : "Check grounding" }}
    </button>

    <div v-if="loading" data-testid="check-progress" class="check-progress">
      <span class="spinner" aria-hidden="true"></span>
      <span>Checks can take up to a minute on long documents. ({{ elapsed }}s)</span>
    </div>

    <p v-if="error" data-testid="upload-error" class="upload-error">{{ error }}</p>

    <button type="button" class="sample-link" @click="$emit('browseSample')">
      No document handy? Try a sample fixture instead.
    </button>
  </div>
</template>

<style scoped>
.upload-view {
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
  max-width: 640px;
  margin: 0 auto;
  padding: var(--s-5) 0;
}
.field-label {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-ink-2);
}
.ai-output-textarea {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  padding: var(--s-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  resize: vertical;
}
.submit-btn {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  font-weight: 600;
  padding: var(--s-2) var(--s-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-ink);
  background: var(--color-ink);
  color: var(--color-bg);
  cursor: pointer;
  align-self: flex-start;
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.check-progress {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  font-size: 0.75rem;
  color: var(--color-ink-3);
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-ink-3);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
.upload-error {
  color: var(--chip-unsupported-text);
  font-size: 0.875rem;
}
.sample-link {
  align-self: flex-start;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  background: none;
  border: none;
  color: var(--color-ink-2);
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
}
</style>
