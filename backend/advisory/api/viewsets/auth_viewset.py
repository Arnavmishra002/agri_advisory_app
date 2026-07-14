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
import re
import os
import secrets
import base64
import urllib.parse
import urllib.request as _urllib_request

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from ...rate_limiters import AtomicWindowRateLimiter, ExponentialBackoff, client_ip_from_request
from ...services.guest_session_service import verify_guest_session_token
from ..serializers import (
    OTPRequestInputSerializer,
    OTPVerifyInputSerializer,
    RegistrationInputSerializer,
    LogoutInputSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# ── OTP rate limiters ─────────────────────────────────────────────────────────
# Uses phone number as client_id (not IP) so rate limit is per-user not per-network.
otp_rate_limiter = AtomicWindowRateLimiter(
    key_prefix="otp",
    capacity=settings.OTP_REQUEST_CAPACITY,
    window_seconds=settings.OTP_REQUEST_WINDOW_SECONDS,
)
otp_verify_rate_limiter = AtomicWindowRateLimiter(
    key_prefix="otp_verify",
    capacity=settings.OTP_VERIFY_CAPACITY,
    window_seconds=settings.OTP_VERIFY_WINDOW_SECONDS,
)
otp_backoff = ExponentialBackoff("otp_verify")

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
    Send OTP via Twilio SMS. In local DEBUG only, falls back to console logging.
    Returns True if SMS was sent, False if fallback (dev mode).
    """
    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from  = os.getenv("TWILIO_FROM_NUMBER", "")

    if not (twilio_sid and twilio_token and twilio_from):
        if settings.DEBUG:
            logger.info("📱 OTP for %s: %s  (Twilio not configured — dev console fallback)", phone, otp)
        else:
            logger.warning("Twilio not configured; OTP not sent for %s", phone)
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
        if settings.DEBUG:
            logger.info("📱 OTP for %s: %s  (SMS failed — dev console fallback)", phone, otp)
        else:
            logger.warning("OTP delivery failed for %s; code suppressed outside DEBUG", phone)
        return False


def _auth_identifiers(request, phone: str) -> tuple[str, str]:
    """Return independent IP and account keys for OTP failure backoff."""
    return f"ip:{client_ip_from_request(request)}", f"phone:{phone}"


def _backoff_response(request, identifiers: tuple[str, str]):
    retry_after = max((otp_backoff.retry_after(identifier) for identifier in identifiers), default=0)
    if retry_after <= 0:
        return None
    return Response(
        {
            "error": "Too many verification attempts. Please wait before trying again.",
            "error_code": "OTP_VERIFY_RATE_LIMITED",
            "error_hi": "बहुत अधिक प्रयास। कृपया कुछ देर बाद फिर कोशिश करें।",
            "retry_after": retry_after,
        },
        status=429,
        headers={"Retry-After": str(retry_after)},
    )


def _verified_guest_session(validated: dict) -> str:
    session_id = str(validated.get("session_id") or "")
    token = str(validated.get("guest_session_token") or "")
    return session_id if verify_guest_session_token(session_id, token) else ""


def _copy_guest_profile_fields(source, target) -> None:
    for field in (
        "location_name", "state", "district", "latitude", "longitude",
        "farm_size_bigha", "farm_size_hectare", "irrigation_type", "soil_type",
        "soil_ph", "crop_history", "current_crop", "current_season",
        "preferred_language",
    ):
        current = getattr(target, field)
        incoming = getattr(source, field)
        if current in (None, "", [], {}) and incoming not in (None, "", [], {}):
            setattr(target, field, incoming)


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
        serializer = OTPRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors, "error_code": "INVALID_REQUEST"}, status=400)
        phone_raw = serializer.validated_data["phone_number"]

        phone = _normalise_phone(phone_raw)
        if not _PHONE_RE.match(phone):
            return Response(
                {"error": "Invalid Indian mobile number. Use 10-digit format.", "error_code": "INVALID_PHONE"},
                status=400,
            )

        # Rate limiting: configured per-phone window
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
        otp = f"{secrets.randbelow(900000) + 100000}"
        cache.set(f"otp:{phone}", otp, timeout=600)  # 10 minutes

        # Send SMS
        sms_sent = _send_otp_sms(phone, otp)

        resp: dict = {"success": True, "expires_in": 600, "sms_sent": sms_sent}

        # In DEBUG mode, include the OTP in the response for easier dev/testing
        if settings.DEBUG:
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
        serializer = OTPVerifyInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors, "error_code": "INVALID_REQUEST"}, status=400)
        phone_raw = serializer.validated_data["phone_number"]
        otp_code = serializer.validated_data["otp_code"]
        session_id = serializer.validated_data.get("session_id", "")
        verified_guest_session = _verified_guest_session(serializer.validated_data)

        phone = _normalise_phone(phone_raw)
        identifiers = _auth_identifiers(request, phone)
        blocked = _backoff_response(request, identifiers)
        if blocked:
            return blocked

        if not otp_verify_rate_limiter.is_allowed(phone):
            return Response(
                {
                    "error": "Too many OTP verification attempts. Please request a new OTP later.",
                    "error_code": "OTP_VERIFY_RATE_LIMITED",
                    "error_hi": "बहुत अधिक गलत प्रयास। कुछ देर बाद नया OTP भेजें।",
                },
                status=429,
            )

        # Check OTP from cache
        stored_otp = cache.get(f"otp:{phone}")
        if not stored_otp:
            for identifier in identifiers:
                otp_backoff.record_failure(identifier)
            return Response(
                {
                    "error": "OTP has expired. Please request a new one.",
                    "error_code": "OTP_EXPIRED",
                    "error_hi": "OTP समाप्त हो गया। नया OTP भेजें।",
                },
                status=400,
            )

        if stored_otp != otp_code:
            for identifier in identifiers:
                otp_backoff.record_failure(identifier)
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
        otp_verify_rate_limiter.reset(phone)
        for identifier in identifiers:
            otp_backoff.clear(identifier)

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
            profile = FarmerProfile.objects.filter(phone_number=phone).first()
            guest_profile = None
            if verified_guest_session:
                guest_profile = FarmerProfile.objects.filter(
                    session_id=verified_guest_session, phone_number=""
                ).first()
            if profile is None:
                profile = guest_profile or FarmerProfile(phone_number=phone)
                profile.phone_number = phone
            elif guest_profile and guest_profile.pk != profile.pk:
                _copy_guest_profile_fields(guest_profile, profile)
            if verified_guest_session and not profile.session_id:
                profile.session_id = verified_guest_session
            profile.save()
            if verified_guest_session:
                logger.info("Verified guest session migrated to phone account %s", phone)
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
        serializer = RegistrationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors, "error_code": "INVALID_REQUEST"}, status=400)
        validated = serializer.validated_data
        username = validated["username"]
        password = validated["password"]
        phone_raw = validated.get("phone_number", "")
        name = validated.get("name", "")
        state = validated.get("state", "")
        language = validated.get("language", "hi")
        session_id = validated.get("session_id", "")
        verified_guest_session = _verified_guest_session(validated)
        phone_normalised = ""
        if phone_raw:
            phone_normalised = _normalise_phone(phone_raw)
            if not _PHONE_RE.match(phone_normalised):
                return Response(
                    {"error": "Invalid Indian mobile number.", "error_code": "INVALID_PHONE"},
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
        try:
            from ...models import FarmerProfile
            profile_defaults = {
                "state":              state,
                "preferred_language": language,
            }
            if session_id:
                profile_defaults["session_id"] = session_id

            owned_session_id = f"user:{user.id}"
            profile = None
            if verified_guest_session:
                profile = FarmerProfile.objects.filter(
                    session_id=verified_guest_session, phone_number=""
                ).first()
            if profile is None:
                profile = FarmerProfile.objects.filter(session_id=owned_session_id).first()
            if profile is None:
                profile = FarmerProfile(**profile_defaults)
            for field, value in profile_defaults.items():
                if getattr(profile, field) in (None, "", [], {}) and value not in (None, "", [], {}):
                    setattr(profile, field, value)
            profile.session_id = owned_session_id
            if phone_normalised:
                profile.phone_number = phone_normalised
            profile.save()
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
            # Resolve only through the authenticated user's phone/username. A
            # client-supplied session_id must never select another farmer's PII.
            profile = (
                FarmerProfile.objects.filter(session_id=f"user:{user.id}").first()
                or FarmerProfile.objects.filter(phone_number=f"+91{user.username}").first()
                or FarmerProfile.objects.filter(phone_number=user.username).first()
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
            serializer = LogoutInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"success": False, "message": "Invalid logout request", "errors": serializer.errors}, status=400)
            refresh_token = serializer.validated_data.get("refresh", "")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Refresh token blacklisted for user %s", request.user)
        except TokenError:
            pass  # already expired or invalid — logout anyway
        except Exception as exc:
            logger.debug("Token blacklist failed (may not be enabled): %s", exc)

        return Response({"success": True, "message": "Logged out successfully."})
