import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

const BANNED = [/\bv-html\b/, /\.innerHTML\s*=/, /\.outerHTML\s*=/, /insertAdjacentHTML/, /document\.write\(/];

describe("no raw HTML injection in the frontend", () => {
  const files = walk(join(__dirname, "..", "src"))
    .filter((f) => /\.(vue|ts|tsx|js)$/.test(f) && !/\.vue\.js$/.test(f));

  it("has source files to scan", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  for (const file of files) {
    it(`renders user text safely in ${file.split("/src/")[1]}`, () => {
      const text = readFileSync(file, "utf8");
      for (const pattern of BANNED) {
        expect(pattern.test(text), `${file} matches ${pattern}`).toBe(false);
      }
    });
  }
});
