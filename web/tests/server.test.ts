import { describe, it, expect } from "vitest";
import { app } from "../src/server";
import Ajv from "ajv";
import { readFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const schemaPath = join(here, "..", "..", "contract", "fixture.schema.json");

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

  it("lists available fixture IDs", async () => {
    const res = await app.request("/api/fixtures");
    expect(res.status).toBe(200);
    const ids = await res.json();
    expect(Array.isArray(ids)).toBe(true);
    expect(ids).toContain("travel-pds-01");
  });
});

describe("fixture schema validation", () => {
  it("all committed fixtures pass schema validation via the HTTP route", async () => {
    const schema = JSON.parse(await readFile(schemaPath, "utf8"));
    const ajv = new Ajv();
    const validate = ajv.compile(schema);
    const res = await app.request("/fixtures/index.json");
    const ids: string[] = await res.json();
    for (const id of ids) {
      const fxRes = await app.request(`/fixtures/${id}.json`);
      const fixture = await fxRes.json();
      expect(validate(fixture), `${id}: ${JSON.stringify(validate.errors)}`).toBe(true);
    }
  });

  it("a fixture missing required fields fails validation", async () => {
    const schema = JSON.parse(await readFile(schemaPath, "utf8"));
    const ajv = new Ajv();
    const validate = ajv.compile(schema);
    const malformed = { fixture_id: "x" }; // missing source, ai_output, claims, etc.
    expect(validate(malformed)).toBe(false);
  });
});
