// Copies the browser libraries from node_modules into public/vendor so the
// site is fully self-hosted (ffmpeg.wasm workers must be same-origin).
import { cpSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const nm = join(root, "node_modules");
const out = join(root, "public", "vendor");

const copies = [
  ["@ffmpeg/ffmpeg/dist/esm", "ffmpeg"],
  ["@ffmpeg/core/dist/esm", "ffmpeg-core"],
  ["@ffmpeg/core-mt/dist/esm", "ffmpeg-core-mt"],
  ["@jsquash/webp", "jsquash-webp"],
  ["wasm-feature-detect/dist/esm", "wasm-feature-detect"],
  ["jszip/dist/jszip.min.js", "jszip.min.js"],
  ["pica/dist/pica.min.js", "pica.min.js"],
  ["utif/UTIF.js", "UTIF.js"],
];

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
for (const [from, to] of copies) {
  const src = join(nm, from);
  if (!existsSync(src)) throw new Error(`missing ${src} — run npm install`);
  cpSync(src, join(out, to), {
    recursive: true,
    filter: (p) => !/\.(map|d\.ts|d\.mts|md)$/.test(p) && !/[\\/]codec[\\/]dec([\\/]|$)/.test(p),
  });
  console.log(`vendor: ${from} -> ${to}`);
}
