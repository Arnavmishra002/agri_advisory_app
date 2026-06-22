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
  POST logout/       — client-side (token is stateless; returns 200 so
                        the frontend can clear storage cleanly)

OTP Flow:
  1. POST otp/request/ → generate 6-digit code → cache with 10min TTL → SMS via Twilio
  2. POST otp/verify/  → check cache → delete on success → get_or_create User+FarmerProfile → JWT

Security:
  - OTP rate limited: 3 requests per phone number per hour
  - OTP is one-time-use (deleted from cache on verify)
  - OTP never echoed in production (DEBUG guard)
  - Phone normalised to +91XXXXXXXXXX format
"""
import logging
import random
import re
import os
import base64
import urllib.parse
import urllib.request as _urllib_request

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from ...rate_limiters import SharedRateLimiter

logger = logging.getLogger(__name__)
User = get_user_model()

# ── OTP rate limiter: max 3 OTP requests per phone per hour ──────────────────
# Uses phone number as client_id (not IP) so rate limit is per-user not per-network.
otp_rate_limiter = SharedRateLimiter(
    key_prefix="otp",
    capacity=3,
    fill_rate=3 / 3600,  # refill 3 tokens over 1 hour (steady state = 3/hr)
)

# Indian mobile number: optional +, optional 91, then 6-9 followed by 9 digits
_PHONE_RE = re.compile(r"^\+?91?[6-9]\d{9}$")


def _normalise_phone(raw: str) -> str:
    """Normalise any Indian mobile format to E.164: +91XXXXXXXXXX"""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}"


def _send_otp_sms(phone: str, otp: str) -> bool:
    """
    Send OTP via Twilio SMS. Falls back to console log when Twilio is not configured.
    Returns True if SMS was sent, False if fallback (dev mode).
    """
    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from  = os.getenv("TWILIO_FROM_NUMBER", "")

    if not (twilio_sid and twilio_token and twilio_from):
        logger.info("📱 OTP for %s: %s  (Twilio not configured — dev console fallback)", phone, otp)
        return False  # dev mode

    try:
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
        body = urllib.parse.urlencode({
            "To":   phone,
            "From": twilio_from,
            "Body": (
                f"KrishiMitra OTP: {otp}\n"
                f"Valid for 10 minutes. Do not share this code.\n"
                f"— KrishiMitra AI"
            ),
        }).encode()
        creds = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
        req = _urllib_request.Request(
            url, data=body,
            headers={"Authorization": f"Basic {creds}"},
            method="POST",
        )
        with _urllib_request.urlopen(req, timeout=8):
            logger.info("📱 OTP SMS sent to %s", phone)
            return True
    except Exception as exc:
        logger.warning("Twilio SMS failed for %s: %s — falling back to console", phone, exc)
        logger.info("📱 OTP for %s: %s  (SMS failed — dev console fallback)", phone, otp)
        return False


# ─────────────────────────────────────────────────────────────────────────────
class AuthViewSet(viewsets.ViewSet):
    """
    Authentication endpoints for KrishiMitra web + mobile clients.
    All endpoints are under /api/users/ prefix.
    """
    permission_classes = [AllowAny]

    # ── POST /api/users/otp/request/ ─────────────────────────────────────────
    @action(methods=["POST"], detail=False, url_path="otp/request")
    def otp_request(self, request):
        """
        Step 1 of OTP login: send a 6-digit OTP to the farmer's mobile number.

        Request body: { "phone_number": "9876543210" }
        Response:     { "success": true, "expires_in": 600, "sms_sent": bool }
        Dev mode only: { ..., "dev_otp": "123456" }
        """
        phone_raw = (request.data.get("phone_number") or "").strip()
        if not phone_raw:
            return Response(
                {"error": "phone_number is required", "error_code": "MISSING_PHONE"},
                status=400,
            )

        phone = _normalise_phone(phone_raw)
        if not _PHONE_RE.match(phone):
            return Response(
                {"error": "Invalid Indian mobile number. Use 10-digit format.", "error_code": "INVALID_PHONE"},
                status=400,
            )

        # Rate limiting: 3 OTPs per phone per hour
        if not otp_rate_limiter.is_allowed(phone):
            return Response(
                {
                    "error": "Too many OTP requests. Please wait 1 hour before trying again.",
                    "error_code": "RATE_LIMITED",
                    "error_hi": "बहुत अधिक प्रयास। 1 घंटे बाद कोशिश करें।",
                },
                status=429,
            )

        # Generate and cache OTP
        otp = f"{random.randint(100000, 999999)}"
        cache.set(f"otp:{phone}", otp, timeout=600)  # 10 minutes

        # Send SMS
        sms_sent = _send_otp_sms(phone, otp)

        resp: dict = {"success": True, "expires_in": 600, "sms_sent": sms_sent}

        # In DEBUG mode, include the OTP in the response for easier dev/testing
        if os.getenv("DEBUG", "False").lower() == "true":
            resp["dev_otp"] = otp

        return Response(resp)

    # ── POST /api/users/otp/verify/ ──────────────────────────────────────────
    @action(methods=["POST"], detail=False, url_path="otp/verify")
    def otp_verify(self, request):
        """
        Step 2 of OTP login: verify the 6-digit OTP and issue JWT tokens.
        Creates User + FarmerProfile if this is the farmer's first login.
        Migrates guest session data if session_id is provided.

        Request body: {
            "phone_number": "9876543210",
            "otp_code": "123456",
            "session_id": "sess_xxxx"  (optional — for guest session migration)
        }
        Response: { "access": "...", "refresh": "...", "user": {...} }
        """
        phone_raw  = (request.data.get("phone_number") or "").strip()
        otp_code   = (request.data.get("otp_code") or "").strip()
        session_id = (request.data.get("session_id") or "").strip()

        if not phone_raw or not otp_code:
            return Response(
                {"error": "phone_number and otp_code are required", "error_code": "MISSING_FIELDS"},
                status=400,
            )

        phone = _normalise_phone(phone_raw)

        # Check OTP from cache
        stored_otp = cache.get(f"otp:{phone}")
        if not stored_otp:
            return Response(
                {
                    "error": "OTP has expired. Please request a new one.",
                    "error_code": "OTP_EXPIRED",
                    "error_hi": "OTP समाप्त हो गया। नया OTP भेजें।",
                },
                status=400,
            )

        if stored_otp != otp_code:
            return Response(
                {
                    "error": "Invalid OTP. Please check and try again.",
                    "error_code": "INVALID_OTP",
                    "error_hi": "गलत OTP। दोबारा जांचें।",
                },
                status=400,
            )

        # OTP verified — delete it (one-time use)
        cache.delete(f"otp:{phone}")

        # Get or create User (username = phone digits without +)
        username = phone.lstrip("+").replace(" ", "")
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_active": True},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            logger.info("New farmer account created via OTP: %s", phone)

        # Get or create FarmerProfile + migrate guest session
        profile_name = ""
        try:
            from ...models import FarmerProfile
            profile, profile_created = FarmerProfile.objects.get_or_create(
                phone_number=phone,
                defaults={"is_active": True} if hasattr(FarmerProfile, "is_active") else {},
            )
            # Migrate guest session data into this profile
            if session_id and not profile.session_id:
                profile.session_id = session_id
                profile.save(update_fields=["session_id"])
                logger.info("Guest session %s migrated to phone account %s", session_id, phone)
            profile_name = profile.location_name or ""
        except Exception as exc:
            logger.warning("FarmerProfile OTP link failed: %s", exc)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        display_name = user.get_full_name() or profile_name or username

        return Response({
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id":       user.id,
                "username": username,
                "name":     display_name,
                "phone":    phone,
                "role":     getattr(user, "role", "farmer"),
                "is_new":   created,
            },
        })

    # ── POST /api/users/register/ ─────────────────────────────────────────────
    @action(methods=["POST"], detail=False, url_path="register")
    def register(self, request):
        """
        Classic username+password registration.
        Auto-logs in and returns JWT tokens on success.
        Optionally creates/links FarmerProfile with state, language, session.

        Request body: {
            "username": "ramesh_farmer",
            "password": "secure123",
            "phone_number": "9876543210",  (optional)
            "name": "Ramesh Kumar",         (optional)
            "state": "Uttar Pradesh",       (optional)
            "language": "hi",               (optional, default: hi)
            "session_id": "sess_xxxx"       (optional)
        }
        """
        username   = (request.data.get("username") or "").strip()
        password   = (request.data.get("password") or "").strip()
        phone_raw  = (request.data.get("phone_number") or "").strip()
        name       = (request.data.get("name") or "").strip()
        state      = (request.data.get("state") or "").strip()
        language   = (request.data.get("language") or "hi").strip()
        session_id = (request.data.get("session_id") or "").strip()

        # Validation
        if not username:
            return Response({"error": "username is required", "error_code": "MISSING_USERNAME"}, status=400)
        if not password:
            return Response({"error": "password is required", "error_code": "MISSING_PASSWORD"}, status=400)
        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters.", "error_code": "PASSWORD_TOO_SHORT"},
                status=400,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "This username is already taken. Please choose another.", "error_code": "USERNAME_TAKEN"},
                status=400,
            )

        # Parse name into first/last
        name_parts = name.split(" ", 1) if name else ["", ""]
        first_name = name_parts[0]
        last_name  = name_parts[1] if len(name_parts) > 1 else ""

        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Create FarmerProfile
        phone_normalised = ""
        if phone_raw:
            try:
                phone_normalised = _normalise_phone(phone_raw)
            except Exception:
                phone_normalised = phone_raw

        try:
            from ...models import FarmerProfile
            profile_defaults = {
                "state":              state,
                "preferred_language": language,
            }
            if session_id:
                profile_defaults["session_id"] = session_id

            identifier = phone_normalised or session_id
            if identifier:
                if phone_normalised:
                    profile, _ = FarmerProfile.objects.get_or_create(
                        phone_number=phone_normalised,
                        defaults=profile_defaults,
                    )
                else:
                    profile, _ = FarmerProfile.objects.get_or_create(
                        session_id=session_id,
                        defaults=profile_defaults,
                    )
                # Ensure session_id is set for guest migration
                if session_id and not profile.session_id:
                    profile.session_id = session_id
                    profile.save(update_fields=["session_id"])
        except Exception as exc:
            logger.warning("FarmerProfile register link failed: %s", exc)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access":  str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id":       user.id,
                    "username": username,
                    "name":     name or username,
                    "phone":    phone_normalised,
                    "role":     getattr(user, "role", "farmer"),
                    "is_new":   True,
                },
            },
            status=201,
        )

    # ── GET /api/users/me/ ────────────────────────────────────────────────────
    @action(methods=["GET"], detail=False, url_path="me",
            permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Return the current authenticated user's info + linked FarmerProfile.
        Requires: Authorization: Bearer <access_token>
        """
        user = request.user
        profile_data: dict = {}

        try:
            from ...models import FarmerProfile
            # Try to find profile by phone number (username for OTP users) or session_id
            session_id = request.query_params.get("session_id", "")
            profile = (
                FarmerProfile.objects.filter(phone_number=f"+91{user.username}").first()
                or FarmerProfile.objects.filter(phone_number=user.username).first()
                or (FarmerProfile.objects.filter(session_id=session_id).first() if session_id else None)
            )
            if profile:
                profile_data = {
                    "location_name":    profile.location_name,
                    "state":            profile.state,
                    "district":         profile.district,
                    "current_crop":     profile.current_crop,
                    "current_season":   profile.current_season,
                    "preferred_language": profile.preferred_language,
                    "farm_size_bigha":  profile.farm_size_bigha,
                    "irrigation_type":  profile.irrigation_type,
                    "has_pm_kisan":     profile.has_pm_kisan,
                    "has_kcc":          profile.has_kcc,
                    "crop_history":     profile.crop_history,
                }
        except Exception as exc:
            logger.warning("FarmerProfile /me lookup failed: %s", exc)

        return Response({
            "id":         user.id,
            "username":   user.username,
            "name":       user.get_full_name() or user.username,
            "email":      user.email or "",
            "role":       getattr(user, "role", "farmer"),
            "is_active":  user.is_active,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "profile":    profile_data,
        })

    # ── POST /api/users/logout/ ───────────────────────────────────────────────
    @action(methods=["POST"], detail=False, url_path="logout")
    def logout(self, request):
        """
        Logout endpoint. JWT is stateless so actual logout happens client-side
        (clear localStorage). This endpoint optionally blacklists the refresh token
        if simplejwt token blacklisting is enabled, and returns 200 so the
        frontend has a consistent API call pattern.

        Request body: { "refresh": "<refresh_token>" }  (optional)
        """
        try:
            refresh_token = request.data.get("refresh", "")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Refresh token blacklisted for user %s", request.user)
        except TokenError:
            pass  # already expired or invalid — logout anyway
        except Exception as exc:
            logger.debug("Token blacklist failed (may not be enabled): %s", exc)

        return Response({"success": True, "message": "Logged out successfully."})
