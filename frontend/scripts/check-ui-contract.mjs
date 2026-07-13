import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const app = readFileSync(new URL('../public/js/app.js', import.meta.url), 'utf8');
const auth = readFileSync(new URL('../public/js/auth.js', import.meta.url), 'utf8');
const i18n = readFileSync(new URL('../public/js/i18n.js', import.meta.url), 'utf8');
const allScripts = `${app}\n${auth}\n${i18n}\n${html}`;
const failures = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
check(duplicateIds.length === 0, `Duplicate element IDs: ${duplicateIds.join(', ')}`);

const serviceNames = [...new Set(
  [...html.matchAll(/showService\('([^']+)'\)/g)].map(match => match[1]),
)];
for (const service of serviceNames) {
  check(
    service === 'home' || ids.includes(`${service}-content`),
    `showService('${service}') has no matching #${service}-content panel`,
  );
}
check(serviceNames.length >= 8, `Expected home plus seven service routes, found ${serviceNames.length}`);

const directHandlers = [...new Set(
  [...html.matchAll(/\bonclick="([A-Za-z_$][\w$]*)\s*\(/g)].map(match => match[1]),
)];
for (const handler of directHandlers) {
  const declared = new RegExp(`(?:function\\s+${handler}\\s*\\(|window\\.${handler}\\s*=)`).test(allScripts);
  check(declared, `Inline handler ${handler}() is not declared`);
}

const requiredIds = [
  'locationSearchInput', 'cropAnalyzeBtn', 'mandiSelector', 'diagnosisRunBtn',
  'fieldAnalyzeBtn', 'messageInput', 'chatSendBtn', 'chatClearBtn', 'authModal',
];
for (const id of requiredIds) check(ids.includes(id), `Required control #${id} is missing`);
for (const id of ['voiceBtn', 'chatClearBtn', 'chatSendBtn']) {
  check(
    new RegExp(`<button[^>]*id="${id}"[^>]*aria-label="[^"]+"`).test(html),
    `Icon control #${id} must have an accessible name`,
  );
}

check(!/\balert\s*\(/.test(app), 'Farmer UI must use inline/toast feedback instead of alert()');
check(!app.includes('&_t=${Date.now()}'), 'Strict API queries must not include the unsupported _t field');
check(html.includes('data-count="202"'), 'Home crop count must match the 202-profile database');
check(!html.includes('MSP 2024-25'), 'Home must not display stale MSP-year copy');
check(!/python manage\.py|DATA_GOV_IN_API_KEY|Server restart/.test(app), 'Farmer-facing JavaScript contains operator-only setup instructions');
check(
  app.includes('if (Number.isFinite(currentLocationAccuracy)) requestBody.accuracy'),
  'Chat requests must omit an unknown GPS accuracy instead of sending null',
);
check(
  app.includes('history: priorHistory'),
  'Chat requests must send prior turns without duplicating the current query',
);

if (failures.length) {
  console.error('UI contract check failed:');
  failures.forEach(failure => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`UI contract passed: ${ids.length} unique IDs, ${serviceNames.length - 1} services, ${directHandlers.length} handlers.`);
