import { describe, it, expect } from "vitest";
import { app } from "../src/server";

describe("server", () => {
  it("serves a known fixture as valid JSON", async () => {
    const res = await app.request("/api/fixtures/travel-pds-01");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.fixture_id).toBe("travel-pds-01");
    expect(Array.isArray(body.claims)).toBe(true);
  });

  it("404s an unknown fixture", async () => {
    const res = await app.request("/api/fixtures/nope");
    expect(res.status).toBe(404);
  });
});
