import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import Ajv from "ajv";

const here = dirname(fileURLToPath(import.meta.url));
const fixturesDir = join(here, "..", "..", "fixtures");
const schemaPath = join(here, "..", "..", "contract", "fixture.schema.json");

const ajv = new Ajv();
let validateFixture: ReturnType<Ajv["compile"]> | null = null;
async function getValidator() {
  if (!validateFixture) {
    const schema = JSON.parse(await readFile(schemaPath, "utf8"));
    validateFixture = ajv.compile(schema);
  }
  return validateFixture;
}

export const app = new Hono();

app.get("/api/fixtures", async (c) => {
  try {
    const files = await readdir(fixturesDir);
    const ids = files
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.replace(".json", ""))
      .sort();
    return c.json(ids);
  } catch {
    return c.json([], 200);
  }
});

async function readAndValidateFixture(id: string) {
  const raw = await readFile(join(fixturesDir, `${id}.json`), "utf8");
  const parsed = JSON.parse(raw);
  const validate = await getValidator();
  if (!validate(parsed)) {
    throw new Error(`fixture ${id} failed schema validation: ${JSON.stringify(validate.errors)}`);
  }
  return parsed;
}

app.get("/api/fixtures/:id", async (c) => {
  const id = c.req.param("id");
  if (!/^[\w-]+$/.test(id)) return c.json({ error: "not found" }, 404);
  try {
    return c.json(await readAndValidateFixture(id));
  } catch (err: unknown) {
    const isNotFound = (err as NodeJS.ErrnoException).code === "ENOENT";
    if (isNotFound) return c.json({ error: "not found" }, 404);
    console.error(err);
    return c.json({ error: "internal" }, 500);
  }
});

// Static-mode compatibility: serve fixtures at /fixtures/ for Netlify parity
app.get("/fixtures/index.json", async (c) => {
  try {
    const files = await readdir(fixturesDir);
    const ids = files.filter((f) => f.endsWith(".json")).map((f) => f.replace(".json", "")).sort();
    return c.json(ids);
  } catch {
    return c.json([], 200);
  }
});

app.get("/fixtures/:id{[\\w-]+\\.json}", async (c) => {
  const id = c.req.param("id").replace(".json", "");
  if (!/^[\w-]+$/.test(id)) return c.json({ error: "not found" }, 404);
  try {
    return c.json(await readAndValidateFixture(id));
  } catch (err: unknown) {
    const isNotFound = (err as NodeJS.ErrnoException).code === "ENOENT";
    if (isNotFound) return c.json({ error: "not found" }, 404);
    console.error(err);
    return c.json({ error: "internal" }, 500);
  }
});

app.get("/*", serveStatic({ root: join(here, "..", "dist") }));

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env["PORT"] ?? 3000);
  serve({ fetch: app.fetch, port });
  console.log(`Grounding Inspector server running on http://localhost:${port}`);
}
