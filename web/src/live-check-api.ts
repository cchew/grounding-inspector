import type { Fixture, LiveCheckApiResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://127.0.0.1:8000";

export async function checkDocument(aiOutput: string, file: File): Promise<Fixture> {
  const form = new FormData();
  form.append("ai_output", aiOutput);
  form.append("reference_file", file);

  const res = await fetch(`${API_BASE}/check`, { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }

  const result = (await res.json()) as LiveCheckApiResponse;
  return {
    fixture_id: "live-check",
    source: { title: file.name, sections: result.source.sections },
    ai_output: result.ai_output,
    claims: result.claims,
    groundedness: result.groundedness,
    live_disclosure:
      `This check used the same Claude verifier (${result.verifier_model}) as Grounding Inspector's other checks. ` +
      "Independent accuracy validation (recall/agreement numbers) exists for the MiniCheck verifier shown in the " +
      "sample fixtures, not yet for this one — treat results as a research signal, not a certified score.",
  };
}
