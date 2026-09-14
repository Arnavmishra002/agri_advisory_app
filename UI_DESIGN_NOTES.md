# Farmer Workspace Design Notes

Implemented in the existing Vite HTML/CSS/JavaScript application, not a mock-up.

## Changes

- Compact location-first header replaces oversized promotional presentation.
- Task navigation and service descriptions explain useful actions, without
  claiming that unavailable integrations are online. Unbound green status dots removed.
- Existing Font Awesome icons replace emoji-only service icons. No component framework added.
- White/off-white surfaces, restrained green actions and amber attention color;
  existing self-hosted fonts retained. No Google Fonts request or CSP relaxation.
- Semantic main/skip link, localized names, visible keyboard focus, labelled
  service cards, Escape focus return, and RTL mobile navbar fixes.
- Crop form retains unknown soil/irrigation instead of silently selecting defaults.
  General guidance and district-reference provenance appear before ranking results.
  Ranking points are not described as probability.
- Profile save feedback depends on successful server response. Reload restores
  owned data; logout clears it. Failed entries stay visible for retry.
- OTP acceptance, unavailable SMS, expiry and request timeout have distinct safe
  paths. Code entry is not shown when no SMS was accepted.
- Service descriptions/actions and general calendar gained hi/en translation
  keys. Other languages remain explicitly beta. Calendar is labelled general reference.
- Duplicated authentication CSS block consolidated. Chat negative margins and
  global icon-only button sizing were repaired instead of hiding overflow.

## Screenshots

- `audit/remediation/after/1440-home.png`
- `audit/remediation/after/320-crop-recommendations.png`
- `audit/remediation/after/360-ai-assistant.png`
- `audit/remediation/after/768-market-prices.png`
- `audit/remediation/real-backend/logout.png`

All 8 captured views and measurements: `audit/remediation/after/screens.json`.
Historical snapshots are retained in `audit/remediation/baseline/`.

## Design limitations still open

This is not a completed design-system rewrite. Legacy inline result styles,
some emoji navigation, untranslated service/error/footer copy, and inconsistent
secondary touch sizes still need a systematic follow-up. The project target is
44x44px for primary touch controls; no WCAG conformance claim is made.
Local engineering inspection is not validation by actual farmers. Test the next
candidate with Hindi/Hinglish/English users, assistive technology, enlarged text,
low-end devices and weak networks before widening access.
