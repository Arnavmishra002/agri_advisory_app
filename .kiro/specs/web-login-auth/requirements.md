# Web Login & Authentication — Requirements

## Overview

Add a login/register system to the KrishiMitra web frontend so farmers can save their profile, chat history, and preferences across sessions. The system must be farmer-friendly — most users are rural, Hindi-speaking, and mobile-first.

The backend already provides:
- `User` model with farmer/admin/officer roles
- JWT endpoints: `POST /api/token/` and `POST /api/token/refresh/`
- `FarmerProfile` linked by session_id or phone_number
- `django-simplejwt` installed and wired
- `POST /api/users/register/` (to be verified/created)

---

## Requirements

### REQ-1: Authentication Methods

#### REQ-1.1 Phone Number + OTP
- WHAT: Farmer enters a 10-digit Indian mobile number, receives a 6-digit OTP via SMS
- WHY: Most Indian farmers identify with their phone number, not a username. KCC and PM-Kisan already use phone as identifier
- ACCEPTANCE: OTP sent within 5 seconds, valid for 10 minutes, max 3 attempts before lockout

#### REQ-1.2 Username + Password
- WHAT: Classic email/username + password login for admin/officer roles and tech-savvy farmers
- WHY: Needed for admin panel access and users who prefer traditional login
- ACCEPTANCE: Min 8-char password, username or email accepted in the same field

#### REQ-1.3 Google OAuth (optional — phase 2)
- WHAT: "Sign in with Google" button
- WHY: Reduces friction for urban farmers and extension officers using Gmail
- ACCEPTANCE: Marked as "Coming Soon" in the UI until backend OAuth is wired

#### REQ-1.4 Guest Mode
- WHAT: "Continue as Guest" option — no account required, uses anonymous session_id
- WHY: Forces zero friction for new users. Guest can always upgrade to full account later
- ACCEPTANCE: Guest session persists in localStorage, no data is lost when they sign up later

---

### REQ-2: Registration

#### REQ-2.1 New Farmer Registration
- WHAT: Name, phone number, state/district, primary language preference
- WHY: Minimum viable profile to personalise crop advice from day one
- ACCEPTANCE: All fields optional except phone number. Registration completes in < 3 taps on mobile

#### REQ-2.2 Profile Migration
- WHAT: On first login after being a guest, merge guest session data (chat history, saved location) into the new account
- WHY: Users must not lose data they collected as a guest
- ACCEPTANCE: Guest session_id is linked to the new FarmerProfile on signup

---

### REQ-3: UI / UX

#### REQ-3.1 Login Entry Point
- WHAT: "लॉगिन / Login" button in the navbar (top-right, next to dark mode toggle)
- WHY: Visible on every page without disrupting the current navigation structure
- ACCEPTANCE: Button visible on all viewport sizes. On mobile, appears in the hamburger menu AND as a persistent top-right icon

#### REQ-3.2 Modal Overlay
- WHAT: Login/register opens as a modal overlay — no full page redirect
- WHY: Farmers should not lose their current location/service context (e.g. mid-chat)
- ACCEPTANCE: Modal is dismissible (× button + click outside). Background content is still visible but blurred/dimmed. Works with Bootstrap 5 modal

#### REQ-3.3 Multi-language UI
- WHAT: Login modal text available in all 22 supported languages, following the existing i18n system
- WHY: Consistent with the rest of the app
- ACCEPTANCE: All labels, placeholders, error messages, and buttons use `data-i18n` keys and are translated

#### REQ-3.4 Logged-in State
- WHAT: After login, navbar shows farmer's name/phone (truncated) + a profile icon + logout option
- WHY: User must know they are logged in
- ACCEPTANCE: JWT access token stored in localStorage with key `km_access_token`. Refresh token in httpOnly cookie (or localStorage fallback). Auto-refresh before expiry

#### REQ-3.5 Mobile First
- WHAT: Modal is full-screen on mobile (< 768px), centred floating card on desktop
- WHY: Most KrishiMitra users are on mobile
- ACCEPTANCE: No horizontal scroll, touch-friendly tap targets (min 44px), OTP input auto-focuses next digit box

---

### REQ-4: Security

#### REQ-4.1 Token Storage
- WHAT: Access token in localStorage (`km_access_token`), refresh token in sessionStorage or httpOnly cookie
- ACCEPTANCE: Token never logged to console. Cleared on logout

#### REQ-4.2 Rate Limiting
- WHAT: OTP requests limited to 3 per phone number per hour (backend enforced via existing `SharedRateLimiter`)
- ACCEPTANCE: Backend returns HTTP 429 with a clear message. Frontend shows "बहुत अधिक प्रयास। 1 घंटे बाद कोशिश करें।"

#### REQ-4.3 HTTPS Only
- WHAT: Auth endpoints only callable over HTTPS in production
- ACCEPTANCE: `SECURE_SSL_REDIRECT=True` already set in settings. Frontend `apiFetch()` uses relative paths (no hardcoded http://)

#### REQ-4.4 CSRF
- WHAT: JWT tokens sent as `Authorization: Bearer <token>` header (not cookies) to avoid CSRF
- ACCEPTANCE: `apiPostJson` updated to include `Authorization` header when token is present

---

### REQ-5: Backend API

#### REQ-5.1 OTP Request Endpoint
- `POST /api/users/otp/request/` — body: `{ phone_number: "+919876543210" }`
- Returns: `{ success: true, expires_in: 600 }`
- Implementation: generate 6-digit code, store in cache with TTL 10 min, send via Twilio/MSG91 (configurable)

#### REQ-5.2 OTP Verify + Login Endpoint
- `POST /api/users/otp/verify/` — body: `{ phone_number, otp_code }`
- Returns: `{ access: "...", refresh: "...", user: { id, name, phone, role } }`
- Creates User + FarmerProfile if first time

#### REQ-5.3 Standard JWT Login (existing)
- `POST /api/token/` — body: `{ username, password }` — already works ✅

#### REQ-5.4 Register Endpoint
- `POST /api/users/register/` — body: `{ username, password, phone_number, name, state, language }`
- Returns: `{ access, refresh, user }`

#### REQ-5.5 Profile Endpoint
- `GET /api/users/me/` — returns current user + linked FarmerProfile
- Auth: Bearer token required

---

### REQ-6: Out of Scope (this spec)

- Social login (Google/Facebook) — Phase 2
- Two-factor auth for admin — separate spec
- Password reset via email — Phase 2
- Mobile app (Flutter) auth — already has its own auth flow

---

## Edge Cases

| Scenario | Expected Behaviour |
|---|---|
| OTP entered after 10 min expiry | "OTP समाप्त हो गया। नया OTP भेजें।" with resend button |
| Phone not registered → OTP verify | Auto-create account with phone number as username |
| Token expired mid-session | Silent refresh via `/api/token/refresh/`. If refresh also expired → logout + show modal |
| Guest has 20 messages in chat | On signup, all messages remain visible (linked via session_id) |
| User logs in on mobile then desktop | Both sessions valid (JWT is stateless) |
| Network offline during OTP send | "इंटरनेट कनेक्शन जांचें।" toast message |
| Admin logs in via phone OTP | Admin role granted only if phone matches an admin User record |
