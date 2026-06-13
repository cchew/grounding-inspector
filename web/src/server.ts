import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const fixturesDir = join(here, "..", "..", "fixtures");

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

app.get("/api/fixtures/:id", async (c) => {
  const id = c.req.param("id");
  if (!/^[\w-]+$/.test(id)) return c.json({ error: "not found" }, 404);
  try {
    const raw = await readFile(join(fixturesDir, `${id}.json`), "utf8");
    return c.json(JSON.parse(raw));
  } catch (err: unknown) {
    const isNotFound = (err as NodeJS.ErrnoException).code === "ENOENT";
    return isNotFound
      ? c.json({ error: "not found" }, 404)
      : c.json({ error: "internal" }, 500);
  }
});

app.get("/*", serveStatic({ root: join(here, "..", "dist") }));

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env["PORT"] ?? 3000);
  serve({ fetch: app.fetch, port });
  console.log(`Grounding Inspector server running on http://localhost:${port}`);
}
