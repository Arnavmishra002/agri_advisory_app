# Web Login & Authentication — Tasks

## Task List

- [x] 1. Backend: Create AuthViewSet with OTP + register + me endpoints
- [x] 2. Backend: Add OTP rate limiter instance and wire URL routes
- [x] 3. Frontend: Add auth modal HTML to index.html + navbar login button
- [x] 4. Frontend: Create auth.js module (KM_Auth object, all methods)
- [x] 5. Frontend: Update app.js to inject Bearer token in API calls
- [x] 6. Frontend: Add auth CSS to styles.css (modal, OTP boxes, navbar pill)
- [x] 7. Frontend: Add 20 auth_* keys to i18n.js for all 22 languages
- [x] 8. Tests: CI smoke test — verify /api/users/otp/request/ + /me/ importable
- [-] 9. Commit + push + rebuild Docker

---

## Task 1: Backend — AuthViewSet

**File:** `backend/advisory/api/viewsets/auth_viewset.py` (CREATE)

Create a new file with a fully functional `AuthViewSet` class:

```python
"""
KrishiMitra — Authentication ViewSet
=====================================
Handles OTP login (farmer-friendly), password login passthrough,
user registration, /me profile endpoint, and logout.

Endpoints (all under /api/users/):
  POST otp/request/  — send 6-digit OTP to mobile number
  POST otp/verify/   — verify OTP, return JWT tokens
  POST register/     — create account + auto-login
  GET  me/           — return current user + FarmerProfile
  POST logout/       — client-side (token is stateless; this is a no-op
                        that returns 200 so the frontend can clear storage)
"""
import logging
import random
import re
import os

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ...rate_limiters import SharedRateLimiter

logger = logging.getLogger(__name__)
User = get_user_model()

# OTP rate limiter: 3 requests per phone per hour
otp_rate_limiter = SharedRateLimiter(
    key_prefix="otp",
    capacity=3,
    fill_rate=3 / 3600,  # 3 tokens per hour
)

_PHONE_RE = re.compile(r"^\+?91?[6-9]\d{9}$")


def _normalise_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}"


def _send_otp_sms(phone: str, otp: str) -> bool:
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER", "")
    if not (twilio_sid and twilio_token and twilio_from):
        logger.info("OTP for %s: %s (Twilio not configured — dev mode)", phone, otp)
        return False
    try:
        import urllib.parse, urllib.request, base64
        url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
        data = urllib.parse.urlencode({
            "To": phone,
            "From": twilio_from,
            "Body": f"KrishiMitra OTP: {otp}. Valid 10 minutes. Do not share.",
        }).encode()
        creds = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
        req = urllib.request.Request(url, data=data,
            headers={"Authorization": f"Basic {creds}"}, method="POST")
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception as exc:
        logger.warning("Twilio SMS failed: %s", exc)
        return False


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(methods=["POST"], detail=False, url_path="otp/request")
    def otp_request(self, request): ...

    @action(methods=["POST"], detail=False, url_path="otp/verify")
    def otp_verify(self, request): ...

    @action(methods=["POST"], detail=False, url_path="register")
    def register(self, request): ...

    @action(methods=["GET"], detail=False, url_path="me")
    def me(self, request): ...

    @action(methods=["POST"], detail=False, url_path="logout")
    def logout(self, request): ...
```

---

## Task 2: Backend — Wire Routes + Replace UserViewSet Stub

**File:** `backend/advisory/api/urls.py` (UPDATE)

Add to imports:
```python
from .viewsets.auth_viewset import AuthViewSet
```

Add to router registrations (replace the existing `users` line if present):
```python
router.register(r"users", AuthViewSet, basename="users")
```

**File:** `backend/advisory/api/viewsets/misc.py` (UPDATE)

Remove the stub `UserViewSet` class entirely (replaced by AuthViewSet).
Remove it from `__init__.py` exports too.

**File:** `backend/advisory/api/viewsets/__init__.py` (UPDATE)

Remove `UserViewSet` import, add:
```python
from .auth_viewset import AuthViewSet
```

---

## Task 3: Frontend — Auth Modal HTML in index.html

Add to `<head>`: no extra dependencies (Bootstrap 5 modal already loaded).

Add `<script src="/js/auth.js"></script>` before closing `</body>`.

**Navbar change:** Add login button after the dark mode toggle:
```html
<!-- Login button (logged-out state) -->
<button class="btn btn-login-pill" id="navLoginBtn"
  onclick="KM_Auth.openModal('phone')"
  aria-label="Login">
  <i class="fas fa-user-circle"></i>
  <span data-i18n="auth_login">लॉगिन</span>
</button>
<!-- User pill (logged-in state, hidden initially) -->
<div class="navbar-user-pill d-none" id="navUserPill">
  <span id="navUserName"></span>
  <div class="dropdown">
    <button class="btn btn-sm" data-bs-toggle="dropdown">▾</button>
    <ul class="dropdown-menu dropdown-menu-end">
      <li><a class="dropdown-item" href="#" onclick="KM_Auth.openModal('profile')">
        <i class="fas fa-user me-2"></i><span data-i18n="nav_profile">प्रोफ़ाइल</span></a></li>
      <li><hr class="dropdown-divider"></li>
      <li><a class="dropdown-item text-danger" href="#"
        onclick="KM_Auth.logout(); return false;">
        <i class="fas fa-sign-out-alt me-2"></i><span data-i18n="auth_logout">लॉगआउट</span></a></li>
    </ul>
  </div>
</div>
```

**Auth Modal** (add before `</body>`):
Full Bootstrap 5 modal with 3 tabs:
- Phone OTP tab (default)
- Password login tab
- Register tab

OTP tab includes: phone input → "OTP भेजें" button → OTP step (6 digit boxes + resend countdown).

---

## Task 4: Frontend — Create auth.js

**File:** `frontend/public/js/auth.js` (CREATE)

Full `KM_Auth` object as designed. Key implementation details:
- OTP digit boxes: `oninput` auto-advances to next input, `onkeydown` backspace goes to previous
- Token stored in localStorage, never in cookies
- `refreshToken()` uses `POST /api/token/refresh/`
- `_scheduleRefresh()` sets setTimeout for 55 minutes
- `init()` called at bottom of file: checks localStorage, restores session
- All API errors shown inline via `.auth-error-msg` elements (no `alert()`)
- Guest "Continue as Guest" closes modal without storing any token

---

## Task 5: Frontend — Update app.js

**In `apiPostJson(path, body)`** — add auth headers:
```javascript
async function apiPostJson(path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (window.KM_Auth && KM_Auth.isLoggedIn()) {
    Object.assign(headers, KM_Auth.getAuthHeaders());
  }
  const response = await fetch(apiFetch(path), {
    method: 'POST', headers, body: JSON.stringify(body),
  });
  // ... rest unchanged
}
```

**In `_upsertFarmerProfile()`** — add user_id:
```javascript
if (window.KM_Auth && KM_Auth._user) {
  payload.user_id = KM_Auth._user.id;
}
```

---

## Task 6: Frontend — Add Auth CSS to styles.css

Add styles for:
- `.btn-login-pill` — green pill button in navbar
- `#authModal .modal-dialog` — full-screen mobile, 480px max-width desktop
- `.auth-tab-btn` — tab switcher with active state
- `.otp-input-group input` — 40×52px boxes, 2px border, auto-advance visual
- `.auth-error-msg` — red, small, inline
- `.auth-success-msg` — green, small, inline
- `.navbar-user-pill` — flex row with user icon + name + dropdown trigger

---

## Task 7: Frontend — Add i18n Keys

**File:** `frontend/public/js/i18n.js` (UPDATE)

Add the 20 `auth_*` keys to all 22 language objects. Minimum required translations:
- Hindi (hi) — full translations
- English (en) — full translations
- All other 20 languages — transliterate or use English fallback where needed

Keys: `auth_login`, `auth_register`, `auth_logout`, `auth_phone_label`,
`auth_otp_label`, `auth_send_otp`, `auth_verify_otp`, `auth_password_label`,
`auth_username_label`, `auth_name_label`, `auth_state_label`,
`auth_guest_continue`, `auth_welcome_back`, `auth_error_invalid_otp`,
`auth_error_expired_otp`, `auth_error_rate_limit`, `auth_error_network`,
`auth_resend_otp`, `auth_resend_countdown`, `auth_or_divider`

---

## Task 8: CI Update

**File:** `.github/workflows/ci.yml` (UPDATE)

Add to the "Service imports" step:
```python
from advisory.api.viewsets.auth_viewset import AuthViewSet, otp_rate_limiter
assert hasattr(AuthViewSet, 'otp_request'), 'otp_request action missing'
assert hasattr(AuthViewSet, 'otp_verify'), 'otp_verify action missing'
assert hasattr(AuthViewSet, 'me'), 'me action missing'
print('✅ AuthViewSet imported and actions verified')
```

Add to "All API routes registered" step — add `users` to required routes list.

---

## Task 9: Commit + Push + Docker Rebuild

```bash
cd /Users/arnavmishra/ai/agri_advisory_app
git add backend/advisory/api/viewsets/auth_viewset.py \
        backend/advisory/api/viewsets/__init__.py \
        backend/advisory/api/urls.py \
        backend/advisory/api/viewsets/misc.py \
        frontend/index.html \
        frontend/public/js/auth.js \
        frontend/public/js/app.js \
        frontend/public/js/i18n.js \
        frontend/css/styles.css \
        .github/workflows/ci.yml \
        .kiro/specs/web-login-auth/
git commit -m "feat: web login — OTP + password auth, JWT, farmer profile migration

Backend:
- AuthViewSet: POST /api/users/otp/request/, otp/verify/, register/, me/, logout/
- OTP rate limiter: 3/hr per phone via SharedRateLimiter
- Auto FarmerProfile create on OTP verify + guest session migration
- Twilio SMS integration (falls back to console log in dev)

Frontend:
- auth.js: KM_Auth module (OTP flow, password login, register, token refresh)
- index.html: Bootstrap 5 auth modal (3 tabs: OTP, Password, Register)
- Navbar: login pill + logged-in user pill with logout dropdown
- app.js: inject Authorization header in all API calls
- styles.css: modal, OTP digit boxes, navbar pill
- i18n.js: 20 auth_* keys for all 22 languages

Closes: web-login-auth spec"
git push origin main
```
