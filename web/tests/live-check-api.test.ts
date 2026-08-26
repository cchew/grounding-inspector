import { describe, it, expect, vi, beforeEach } from "vitest";
import { checkDocument } from "../src/live-check-api";

beforeEach(() => {
  global.fetch = vi.fn();
});

function makeFile(content: string, name = "policy.txt") {
  return new File([content], name, { type: "text/plain" });
}

describe("checkDocument", () => {
  it("posts multipart form data and returns a fixture-shaped result", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ai_output: "Medical is covered up to $10,000.",
            source: { sections: [{ id: "s1", page: 1, char_start: 0, char_end: 10, text: "Medical..." }] },
            claims: [
              { id: "c1", text: "x", label: "grounded", evidence_span_ids: [], quote: null, page: null, rationale: "" },
            ],
            groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
            verifier_model: "claude-haiku-4-5-20251001",
          }),
      } as Response)
    ) as unknown as typeof fetch;

    const result = await checkDocument("Medical is covered up to $10,000.", makeFile("Medical..."));

    expect(result.fixture_id).toBe("live-check");
    expect(result.claims[0].label).toBe("grounded");
    expect(result.live_disclosure).toContain("claude-haiku-4-5-20251001");

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("throws the server's error detail on a non-ok response", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 429,
        json: () => Promise.resolve({ detail: "Today's free checks are used up. Try again tomorrow." }),
      } as Response)
    ) as unknown as typeof fetch;

    await expect(checkDocument("x", makeFile("y"))).rejects.toThrow("free checks are used up");
  });

  it("falls back to a status-code message when the response has no JSON body", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.reject(new Error("no body")) } as Response)
    ) as unknown as typeof fetch;

    await expect(checkDocument("x", makeFile("y"))).rejects.toThrow("HTTP 500");
  });
});
