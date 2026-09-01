# Web Login & Authentication — Design

## Architecture Overview

```
Frontend (Vanilla JS + Bootstrap 5)     Backend (Django + DRF)
────────────────────────────────────    ─────────────────────────────────
frontend/public/js/auth.js (NEW)         advisory/api/viewsets/auth_viewset.py (NEW)
  └─ KM_Auth object                       ├─ POST /api/users/otp/request/
      ├─ init()                            ├─ POST /api/users/otp/verify/
      ├─ openModal(tab)                    ├─ POST /api/users/register/
      ├─ requestOtp()                      ├─ GET  /api/users/me/
      ├─ verifyOtp()                       └─ POST /api/users/logout/
      ├─ loginPassword()
      ├─ register()                       advisory/api/urls.py (UPDATED)
      ├─ logout()                          └─ register auth_viewset routes
      ├─ refreshToken()
      ├─ getAuthHeaders()                 advisory/rate_limiters.py (UPDATED)
      └─ _updateNavbar()                   └─ otp_rate_limiter (new instance)

frontend/index.html (UPDATED)
  ├─ #authModal — Bootstrap 5 modal
  ├─ navbar login button
  └─ <script src="/js/auth.js">

frontend/css/styles.css (UPDATED)
  └─ auth modal + otp + navbar pill styles

frontend/public/js/i18n.js (UPDATED)
  └─ 20 new auth_* i18n keys

frontend/public/js/app.js (UPDATED)
  └─ inject Bearer token in apiPostJson/apiFetch
```

## Token Storage

| Token        | Storage      | Key                 | TTL    |
|---|---|---|---|
| Access token | localStorage | km_access_token     | 60 min |
| Refresh token| localStorage | km_refresh_token    | 7 days |
| User info    | localStorage | km_user             | 7 days |

Auto-refresh: setTimeout at 55 min. If refresh expired → silent logout + open modal.

## Modal State Machine

```
CLOSED
  └─► PHONE_INPUT  →  OTP_INPUT  →  LOGGED_IN
  └─► PASSWORD_INPUT             →  LOGGED_IN
  └─► REGISTER_FORM              →  LOGGED_IN
```

Three tabs inside one Bootstrap 5 #authModal:
- Tab 1 "📱 OTP" — default, farmer-friendly
- Tab 2 "🔒 Password" — admin/officer
- Tab 3 "✨ Register" — new user signup

## OTP Backend Flow

```
POST /api/users/otp/request/  { phone_number: "+919..." }
  → validate Indian mobile (10 digits, optional +91)
  → otp_rate_limiter.is_allowed(phone_number)  [3 req/hr per number]
  → OTP = random 6-digit string
  → cache.set("otp:{phone_number}", OTP, timeout=600)
  → if TWILIO_ACCOUNT_SID: send SMS via Twilio
  → else: log OTP to Django console (dev mode)
  → if DEBUG: include dev_otp in response
  → return { success: true, expires_in: 600 }

POST /api/users/otp/verify/  { phone_number, otp_code, session_id? }
  → stored = cache.get("otp:{phone_number}")
  → if stored != otp_code: return 400 INVALID_OTP
  → cache.delete("otp:{phone_number}")  [one-time use]
  → User.objects.get_or_create(username=phone_number)
  → FarmerProfile.objects.get_or_create(phone_number=phone_number)
  → if session_id provided: link FarmerProfile.session_id = session_id
  → refresh = RefreshToken.for_user(user)
  → return { access, refresh, user: {id, name, phone, role} }
```

## New Backend File: advisory/api/viewsets/auth_viewset.py

```python
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

Register as: `router.register(r"users", AuthViewSet, basename="users")`
(replaces the existing stub UserViewSet in misc.py)

## Frontend Module: auth.js

```javascript
const KM_Auth = {
  _user: null,
  _accessToken: null,
  _refreshTimer: null,

  init()            // restore from localStorage, update navbar
  openModal(tab)    // tab: 'phone'|'password'|'register'
  closeModal()
  requestOtp()      // validate phone → API → show OTP step
  verifyOtp()       // verify 6 digits → store tokens → update navbar
  loginPassword()   // POST /api/token/ → store tokens → update navbar
  register()        // POST /api/users/register/ → auto-login
  logout()          // clear localStorage → reset navbar
  refreshToken()    // POST /api/token/refresh/ → update access token
  getAuthHeaders()  // returns {Authorization: 'Bearer ...'} or {}
  isLoggedIn()      // bool
  _updateNavbar()   // login button ↔ user pill
  _scheduleRefresh()// setTimeout 55 min
}
window.KM_Auth = KM_Auth;
```

## CSS Additions

- `.auth-modal-overlay` — full-screen mobile, centred card ≥768px
- `.auth-tab-btn` — tab switcher with active state
- `.otp-input-group` — 6 digit boxes (40×52px each), auto-advance on input
- `.auth-error-msg` — red inline error (no alert() ever used)
- `.auth-success-msg` — green confirmation
- `.navbar-user-pill` — "👤 Ramesh" pill with logout dropdown
- `.auth-loading-spinner` — button-level spinner during API calls

## i18n Keys Added (22 languages)

```
auth_login, auth_register, auth_logout,
auth_phone_label, auth_otp_label, auth_send_otp, auth_verify_otp,
auth_password_label, auth_username_label, auth_name_label,
auth_state_label, auth_guest_continue, auth_welcome_back,
auth_error_invalid_otp, auth_error_expired_otp,
auth_error_rate_limit, auth_error_network,
auth_resend_otp, auth_resend_countdown, auth_or_divider
```

## Integration with app.js

1. `apiPostJson(path, body)` — add `...KM_Auth.getAuthHeaders()` to fetch headers
2. `_upsertFarmerProfile()` — add `user_id: KM_Auth._user?.id` to payload
3. Chat `sendChatMessage()` — attach `user_id` for session personalisation

## Security Notes

- OTP never echoed in production responses (DEBUG guard)
- Access token never logged to console
- `Authorization` header only sent to same-origin API paths
- Rate limiter uses phone number as client_id (not IP) for OTP endpoint
- Logout deletes both tokens from localStorage immediately
