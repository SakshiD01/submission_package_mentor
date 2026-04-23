#!/usr/bin/env node
/**
 * Smoke test: resolve and evaluate `app.js` and its static import graph under Node.
 * Does not run the browser boot path (DOMContentLoaded is registered but not fired).
 *
 * Usage:
 *   - Repo root (parent of `brexit_ml/`):  node brexit_ml/ui/scripts/smoke-load-app.mjs
 *   - Package dir (`brexit_ml/`):           node ui/scripts/smoke-load-app.mjs
 *   - Inside `brexit_ml/ui/`:               node scripts/smoke-load-app.mjs
 */

import { fileURLToPath, pathToFileURL } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.join(__dirname, "..", "app.js");
const appUrl = pathToFileURL(appPath).href;

if (typeof globalThis.window === "undefined") {
  globalThis.window = globalThis;
}

if (typeof globalThis.document === "undefined") {
  globalThis.document = {
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
    getElementById() {
      return null;
    },
    body: {
      append() {},
      contains() {
        return false;
      },
    },
  };
}

await import(appUrl);
console.log("smoke-load-app: app.js and imports loaded OK");
