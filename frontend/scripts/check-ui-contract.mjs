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
  'fieldAnalyzeBtn', 'messageInput', 'chatSendBtn', 'chatNewBtn', 'chatHistoryBtn',
  'chatHistoryDialog', 'chatHistoryList', 'authModal',
];
for (const id of requiredIds) check(ids.includes(id), `Required control #${id} is missing`);
for (const id of ['voiceBtn', 'chatNewBtn', 'chatHistoryBtn', 'chatSendBtn']) {
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
check(!/22\s*(?:भाषाएं|भारतीय भाषाएं|languages?)/i.test(html), 'Farmer UI must not advertise unverified language-count claims');
check(!/Local KrishiMitra LLM|Local LLM|RAG|Gemini fallback/.test(html), 'Farmer UI must not expose internal AI implementation labels');
check(!app.includes('AI/Data Quality:'), 'Chat source badge must use farmer-facing trust wording');
check(!app.includes("let currentLocation = 'Delhi'"), 'Frontend must not assume Delhi before the farmer confirms a location');
check(!html.includes('class="location-name">Delhi</span>'), 'Location bar must not display a fabricated default city');
check(
  !app.includes('updateLocation(\n                    query,\n                    currentLatitude'),
  'Failed text geocoding must not relabel stale coordinates as the typed location',
);
check(
  app.includes('location_confirmed: hasConfirmedLocation()'),
  'Chat requests must explicitly distinguish confirmed and unknown locations',
);
check(
  app.includes('function apiLocationSource()') &&
    app.includes('location_source: apiLocationSource()'),
  'JSON chat/diagnostics/field payloads must not send the internal unconfirmed location source',
);
check(
  app.includes("source === 'text_query_ungeocoded'") && app.includes("source === 'default_fallback'"),
  'Manual location search must reject unverified backend fallbacks',
);
check(
  !app.includes('currentMandi = nearestName'),
  'Nearest mandi may be highlighted but must not hide state live rows through automatic selection',
);
check(
  /<option value="150" selected>150 km<\/option>/.test(html) &&
    /<option value="state">पूरा राज्य<\/option>/.test(html),
  'Mandi selector must default to nearby 150 km, not the whole-state registry',
);
check(
  app.includes('updateMandiSelectionStatus(data)') &&
    app.includes('data.mandi_no_live_rows === true'),
  'Selected-mandi loading state must finish with an honest official-row status',
);
check(
  app.includes('show-state-market-prices') && app.includes("selectMandi('')"),
  'An unavailable exact mandi must offer a clearly separate official state benchmark',
);
check(
  !app.includes('आधिकारिक लाइव मंडी फीड अभी इस सर्वर पर जुड़ी नहीं है'),
  'Missing exact-mandi rows must not be mislabeled as a disconnected official feed',
);
check(
  app.includes('startLocationIfAlreadyAllowed') && app.includes('window.isSecureContext'),
  'GPS startup must respect browser permission and secure-context requirements',
);
check(
  app.includes('if (Number.isFinite(currentLocationAccuracy)) requestBody.accuracy'),
  'Chat requests must omit an unknown GPS accuracy instead of sending null',
);
check(
  app.includes('history: priorHistory'),
  'Chat requests must send prior turns without duplicating the current query',
);
check(
  auth.indexOf('this._resetAuthUi();') < auth.indexOf('this.switchTab(tab);'),
  'Opening auth must clear stale registration/login fields before selecting a tab',
);
check(
  auth.includes("el.style.display = msg ? 'block' : 'none'"),
  'Auth inline errors/success messages must override CSS display:none when populated',
);
check(
  auth.includes("addEventListener('hidden.bs.modal'") &&
    !auth.includes("addEventListener('shown.bs.modal'"),
  'Auth fields must reset on close without a shown-event race that erases farmer input',
);
check(
  auth.includes("window.showService('ai-assistant')"),
  'Profile action must navigate to the existing AI assistant/profile panel',
);
check(
  auth.includes("sessionStorage.getItem(SS_REFRESH)") &&
    auth.includes("sessionStorage.setItem(SS_REFRESH, data.refresh)"),
  'Refresh token must be stored only for the current browser session',
);
check(
  app.includes("window.crypto.randomUUID") &&
    app.includes("lastDiagnosticSessionId = diagnosticSessionId") &&
    app.includes("...KM_Auth.getAuthHeaders()"),
  'Each diagnosis and owned feedback must use a fresh ID plus authenticated headers',
);
check(
  !auth.includes("localStorage.setItem(LS_REFRESH") &&
    auth.includes("localStorage.removeItem(LEGACY_LS_REFRESH)"),
  'Persistent legacy refresh tokens must be removed from localStorage',
);
check(
  app.includes("GUEST_CHAT_OWNER") && app.includes("km:auth-changed") &&
    app.includes("guestSessionMigrated === true"),
  'Chat history must be isolated by guest/user identity and migrate only with signed backend proof',
);
check(
  app.includes("CHAT_HISTORY_SCHEMA_VERSION") &&
    app.includes("km_chat_history_${CHAT_HISTORY_SCHEMA_VERSION}_${token}"),
  'Chat history keys must be schema-versioned so stale local AI responses do not reappear after safety changes',
);
check(
  app.includes("deleteArchivedChat") && app.includes("chat-history-delete"),
  'Chat history must support deleting an individual archived conversation',
);
check(
  app.includes("OFFLINE_CACHE_PREFIX") && app.includes("_saveOfflineResult") &&
    app.includes("_loadOfflineResult") && app.includes("cached_stale"),
  'Weather, official mandi, and crop results must have location-specific labeled offline caches',
);
check(
  !html.includes("openModal('profile')"),
  'Profile action must not pass an unsupported auth modal tab',
);
check(
  html.includes('clearCropRecommendationSearch()') &&
    app.includes('function clearCropRecommendationSearch()') &&
    app.includes('window.clearCropRecommendationSearch = clearCropRecommendationSearch'),
  'Crop recommendations must have a visible reset path that clears a selected crop filter',
);
for (const id of [
  'tabBtnPhone', 'tabBtnPassword', 'tabBtnRegister', 'btnSendOtp',
  'btnVerifyOtp', 'btnResendOtp', 'btnLoginPassword', 'btnRegister',
]) {
  check(
    new RegExp(`<button[^>]*type="button"[^>]*id="${id}"`).test(html),
    `Auth control #${id} must be a non-submit button`,
  );
}

if (failures.length) {
  console.error('UI contract check failed:');
  failures.forEach(failure => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`UI contract passed: ${ids.length} unique IDs, ${serviceNames.length - 1} services, ${directHandlers.length} handlers.`);
