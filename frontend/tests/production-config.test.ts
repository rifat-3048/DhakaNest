import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";


const source = readFileSync(
  new URL("../src/lib/api-config.ts", import.meta.url),
  "utf8",
);

test("production API configuration requires an explicit public backend URL", () => {
  assert.match(source, /NODE_ENV === ['"]production['"]/);
  assert.match(source, /NEXT_PUBLIC_API_BASE_URL is required/);
});

test("localhost is retained only as the development fallback", () => {
  const guardPosition = source.indexOf("NODE_ENV === 'production'");
  const fallbackPosition = source.indexOf("http://127.0.0.1:8000");
  assert.ok(guardPosition >= 0);
  assert.ok(fallbackPosition > guardPosition);
});
