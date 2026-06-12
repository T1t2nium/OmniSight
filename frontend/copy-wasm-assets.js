/**
 * Copies VAD model + ONNX Runtime WASM files from node_modules to public/.
 *
 * This enables self-hosted (offline) loading of the Silero VAD model.
 * Run automatically after `npm install` via the postinstall hook.
 */

import { copyFileSync, mkdirSync, existsSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC = resolve(__dirname, 'public');
const NM = resolve(__dirname, 'node_modules');

const ASSETS = [
  '@ricky0123/vad-web/dist/silero_vad_v5.onnx',
  '@ricky0123/vad-web/dist/vad.worklet.bundle.min.js',
  'onnxruntime-web/dist/ort-wasm-simd-threaded.wasm',
  'onnxruntime-web/dist/ort-wasm-simd-threaded.mjs',
  'onnxruntime-web/dist/ort.all.min.js',
];

// Ensure public/ exists
mkdirSync(PUBLIC, { recursive: true });

let copied = 0;
for (const asset of ASSETS) {
  const src = resolve(NM, asset);
  const dest = resolve(PUBLIC, basename(asset));

  if (!existsSync(src)) {
    console.warn(`[copy-wasm-assets] SKIP (not found): ${asset}`);
    continue;
  }

  copyFileSync(src, dest);
  copied++;
  console.log(`[copy-wasm-assets] Copied: ${basename(asset)}`);
}

console.log(`[copy-wasm-assets] Done — ${copied}/${ASSETS.length} assets copied`);
