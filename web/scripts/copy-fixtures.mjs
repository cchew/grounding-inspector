import { readdir, copyFile, writeFile, mkdir } from "fs/promises";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "fixtures");
const dst = join(here, "..", "public", "fixtures");

await mkdir(dst, { recursive: true });
const files = (await readdir(src)).filter((f) => f.endsWith(".json")).sort();
for (const f of files) await copyFile(join(src, f), join(dst, f));
await writeFile(join(dst, "index.json"), JSON.stringify(files.map((f) => f.replace(".json", "")), null, 2) + "\n");
console.log(`copy-fixtures: ${files.length} fixtures → public/fixtures/`);
