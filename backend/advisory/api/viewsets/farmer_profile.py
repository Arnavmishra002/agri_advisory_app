"""
KrishiMitra Farmer Profile API
================================
Manages persistent farmer profiles for personalized AI advisory.

Endpoints:
  GET  /api/farmer-profile/           — current farmer, redacted public shape
  POST /api/farmer-profile/           — create / upsert current farmer profile
  POST /api/farmer-profile/add_crop/  — add crop history entry
  GET  /api/farmer-profile/context/   — AI context dict for current farmer

The profile feeds directly into chat_intelligence_service.answer() so the
AI can say: "Last Rabi you grew wheat and had aphid issues. This season
with soil pH 6.8, mustard gives 15% higher expected return."
"""

import logging
from datetime import datetime, timezone

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..errors import safe_error_message
from ..serializers import FarmerCropInputSerializer, FarmerProfileInputSerializer

logger = logging.getLogger(__name__)


class FarmerProfileViewSet(viewsets.ViewSet):
    """CRUD + helper actions for FarmerProfile."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _phone_candidates(user) -> set[str]:
        username = (getattr(user, "username", "") or "").strip()
        digits = "".join(ch for ch in username if ch.isdigit())
        candidates = {username} if username else set()
        if digits:
            candidates.add(digits)
            candidates.add(f"+{digits}")
            if len(digits) == 10:
                candidates.add(f"+91{digits}")
            elif len(digits) == 12 and digits.startswith("91"):
                candidates.add(f"+{digits}")
        return {c for c in candidates if c}

    @classmethod
    def _owned_filter(cls, user) -> Q:
        q = Q(session_id=f"user:{user.id}")
        for phone in cls._phone_candidates(user):
            q |= Q(phone_number=phone)
        return q

    @classmethod
    def _lookup_for_new_profile(cls, user) -> dict:
        phones = sorted(
            [p for p in cls._phone_candidates(user) if p.startswith("+91")],
            key=len,
        )
        if phones:
            return {"phone_number": phones[0]}
        return {"session_id": f"user:{user.id}"}

    @classmethod
    def _get_owned_profile(cls, user):
        from ...models import FarmerProfile
        return FarmerProfile.objects.filter(cls._owned_filter(user)).first()

    # ── GET: fetch profile ────────────────────────────────────────────────────
    def list(self, request):
        """
        GET /api/farmer-profile/

        Client-supplied phone/session_id query params are intentionally ignored:
        ownership is derived from the authenticated JWT user.
        """
        try:
            profile = self._get_owned_profile(request.user)
            if not profile:
                return Response({"exists": False, "profile": None})
            return Response({"exists": True, "profile": self._serialize_public(profile)})
        except Exception as exc:
            return Response(
                {"error": safe_error_message(exc, context="farmer_profile_get")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── POST: create or upsert ────────────────────────────────────────────────
    def create(self, request):
        """
        POST /api/farmer-profile/
        Body: {
          "location_name": "Jaipur",
          "state": "Rajasthan",
          "district": "Jaipur",
          "latitude": 26.9, "longitude": 75.7,
          "farm_size_bigha": 5,
          "current_crop": "wheat",
          "current_season": "Rabi 2025-26",
          "soil_ph": 6.8,
          "irrigation_type": "drip",
          "preferred_language": "hi",
          "has_pm_kisan": true,
          "has_kcc": false
        }
        Upserts the current authenticated farmer's profile.
        Client-supplied phone/session_id are not accepted as ownership proof.
        """
        serializer = FarmerProfileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "error_code": "INVALID_PROFILE"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        d = serializer.validated_data
        try:
            from ...models import FarmerProfile
            profile = self._get_owned_profile(request.user)
            if profile:
                created = False
            else:
                profile, created = FarmerProfile.objects.get_or_create(
                    **self._lookup_for_new_profile(request.user)
                )

            # Update all provided fields
            field_map = {
                "location_name":     "location_name",
                "state":             "state",
                "district":          "district",
                "latitude":          "latitude",
                "longitude":         "longitude",
                "farm_size_bigha":   "farm_size_bigha",
                "farm_size_hectare": "farm_size_hectare",
                "current_crop":      "current_crop",
                "current_season":    "current_season",
                "soil_ph":           "soil_ph",
                "soil_type":         "soil_type",
                "irrigation_type":   "irrigation_type",
                "preferred_language":"preferred_language",
                "has_pm_kisan":      "has_pm_kisan",
                "has_kcc":           "has_kcc",
                "has_pmfby":         "has_pmfby",
                "pm_kisan_status":   "pm_kisan_status",
                "whatsapp_opt_in":   "whatsapp_opt_in",
            }
            for payload_key, model_field in field_map.items():
                if payload_key in d:
                    setattr(profile, model_field, d[payload_key])

            profile.last_seen_at = datetime.now(tz=timezone.utc)
            profile.save()

            return Response(
                {
                    "status":  "created" if created else "updated",
                    "profile": self._serialize(profile),
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response(
                {"error": safe_error_message(exc, context="farmer_profile_create")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── POST: add crop history entry ──────────────────────────────────────────
    @action(detail=False, methods=["post"], url_path="add-crop")
    def add_crop(self, request):
        """
        POST /api/farmer-profile/add-crop/
        Body: {
          "season": "Rabi 2024-25",
          "crop": "wheat",
          "issue": "aphid"           // optional
        }
        Appends to the authenticated farmer's crop_history list (max 6 entries kept).
        """
        serializer = FarmerCropInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "error_code": "INVALID_CROP_HISTORY"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        d = serializer.validated_data
        season = d.get("season", "")
        crop = d["crop"]

        try:
            profile = self._get_owned_profile(request.user)
            if not profile:
                return Response(
                    {"error": "Farmer profile not found — create it first"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            entry  = {"season": season, "crop": crop}
            if d.get("issue"):
                entry["issue"] = d["issue"]
            if d.get("yield_qtl"):
                entry["yield_qtl"] = d["yield_qtl"]

            history = profile.crop_history or []
            history.append(entry)
            profile.crop_history = history[-6:]   # keep last 6 seasons
            profile.save(update_fields=["crop_history", "updated_at"])

            return Response({"status": "added", "crop_history": profile.crop_history})
        except Exception as exc:
            return Response(
                {"error": safe_error_message(exc, context="add_crop")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── GET: AI context dict ──────────────────────────────────────────────────
    @action(detail=False, methods=["get"], url_path="context")
    def context(self, request):
        """
        GET /api/farmer-profile/context/
        Returns the dict used to personalise the AI chatbot prompt.
        """
        try:
            profile = self._get_owned_profile(request.user)
            ctx = profile.to_context_dict() if profile else {}
            return Response({"context": ctx, "has_profile": bool(profile)})
        except Exception as exc:
            return Response(
                {"error": safe_error_message(exc, context="farmer_context")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── GET/PATCH/PUT: current farmer profile ─────────────────────────────────
    @action(detail=False, methods=["get", "patch", "put"], url_path="me")
    def me(self, request):
        """
        GET  /api/farmer-profile/me/
        PATCH /api/farmer-profile/me/
        PUT   /api/farmer-profile/me/
        """
        user = getattr(request, "user", None)

        from ...models import FarmerProfile
        profile = self._get_owned_profile(user)

        if not profile:
            if request.method in ["PATCH", "PUT"]:
                profile, created = FarmerProfile.objects.get_or_create(
                    **self._lookup_for_new_profile(user)
                )
            else:
                return Response(
                    {"exists": False, "profile": None, "message": "No profile matches the authenticated user"},
                    status=status.HTTP_404_NOT_FOUND if request.method == "GET" else status.HTTP_400_BAD_REQUEST
                )

        if request.method in ["PATCH", "PUT"]:
            serializer = FarmerProfileInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": serializer.errors, "error_code": "INVALID_PROFILE"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            d = serializer.validated_data
            field_map = {
                "location_name":     "location_name",
                "state":             "state",
                "district":          "district",
                "latitude":          "latitude",
                "longitude":         "longitude",
                "farm_size_bigha":   "farm_size_bigha",
                "farm_size_hectare": "farm_size_hectare",
                "current_crop":      "current_crop",
                "current_season":    "current_season",
                "soil_ph":           "soil_ph",
                "soil_type":         "soil_type",
                "irrigation_type":   "irrigation_type",
                "preferred_language":"preferred_language",
                "has_pm_kisan":      "has_pm_kisan",
                "has_kcc":           "has_kcc",
                "has_pmfby":         "has_pmfby",
                "pm_kisan_status":   "pm_kisan_status",
                "whatsapp_opt_in":   "whatsapp_opt_in",
            }
            for payload_key, model_field in field_map.items():
                if payload_key in d:
                    setattr(profile, model_field, d[payload_key])

            profile.last_seen_at = datetime.now(tz=timezone.utc)
            profile.save()
            return Response({"status": "updated", "profile": self._serialize(profile)})

        # GET request
        profile.last_seen_at = datetime.now(tz=timezone.utc)
        profile.save(update_fields=["last_seen_at"])
        return Response({"exists": True, "profile": self._serialize(profile)})

    # ── Helper ────────────────────────────────────────────────────────────────
    @staticmethod
    def _serialize(p) -> dict:
        return {
            "phone_number":       p.phone_number,
            "session_id":         p.session_id,
            "location_name":      p.location_name,
            "state":              p.state,
            "district":           p.district,
            "latitude":           p.latitude,
            "longitude":          p.longitude,
            "farm_size_bigha":    p.farm_size_bigha,
            "farm_size_hectare":  p.farm_size_hectare,
            "current_crop":       p.current_crop,
            "current_season":     p.current_season,
            "soil_ph":            p.soil_ph,
            "soil_type":          p.soil_type,
            "irrigation_type":    p.irrigation_type,
            "crop_history":       p.crop_history,
            "has_pm_kisan":       p.has_pm_kisan,
            "has_kcc":            p.has_kcc,
            "has_pmfby":          p.has_pmfby,
            "pm_kisan_status":    p.pm_kisan_status,
            "preferred_language": p.preferred_language,
            "whatsapp_opt_in":    p.whatsapp_opt_in,
            "created_at":         p.created_at.isoformat() if p.created_at else None,
            "last_seen_at":       p.last_seen_at.isoformat() if p.last_seen_at else None,
        }

    @staticmethod
    def _serialize_public(p) -> dict:
        return {
            "location_name":      p.location_name,
            "state":              p.state,
            "district":           p.district,
            "farm_size_bigha":    p.farm_size_bigha,
            "farm_size_hectare":  p.farm_size_hectare,
            "current_crop":       p.current_crop,
            "current_season":     p.current_season,
            "soil_ph":            p.soil_ph,
            "soil_type":          p.soil_type,
            "irrigation_type":    p.irrigation_type,
            "crop_history":       p.crop_history,
            "has_pm_kisan":       p.has_pm_kisan,
            "has_kcc":            p.has_kcc,
            "has_pmfby":          p.has_pmfby,
            "pm_kisan_status":    p.pm_kisan_status,
            "preferred_language": p.preferred_language,
            "whatsapp_opt_in":    p.whatsapp_opt_in,
            "created_at":         p.created_at.isoformat() if p.created_at else None,
            "last_seen_at":       p.last_seen_at.isoformat() if p.last_seen_at else None,
        }
