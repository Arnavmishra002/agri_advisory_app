import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const scope = { document: { readyState: 'loading', addEventListener() {} } };
scope.window = scope;
vm.runInNewContext(readFileSync('public/js/i18n.js', 'utf8'), scope);
const coverage = scope.getTranslationCoverage();
const html = readFileSync('index.html', 'utf8');
const required = [...new Set([...html.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g)].map(m => m[1]))];
for (const code of ['hi', 'en']) {
  const missing = coverage.find(l => l.code === code).missing;
  assert.deepEqual(required.filter(key => missing.includes(key) || scope.t(key, code) === key), [], `${code}: missing required keys`);
}
assert.ok(scope.SUPPORTED_LANGUAGES.some(l => l.code === 'brx'));
assert.ok(!scope.SUPPORTED_LANGUAGES.some(l => l.code === 'bo'));
assert.equal(scope.t('nav_home', 'sat'), scope.t('nav_home', 'en'), 'Ol Chiki option must not silently fall back to Devanagari');
console.log(JSON.stringify({ requiredKeys: required.length, coverage }, null, 2));
