"""
KrishiMitra Farmer Profile API
================================
Manages persistent farmer profiles for personalized AI advisory.

Endpoints:
  GET  /api/farmer-profile/?phone=+919876543210
  GET  /api/farmer-profile/?session_id=sess_abc
  POST /api/farmer-profile/           — create / upsert by phone or session_id
  POST /api/farmer-profile/add_crop/  — add crop history entry
  GET  /api/farmer-profile/context/   — AI context dict for this farmer

The profile feeds directly into chat_intelligence_service.answer() so the
AI can say: "Last Rabi you grew wheat and had aphid issues. This season
with soil pH 6.8, mustard gives 15% higher expected return."
"""

import logging
from datetime import datetime

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..errors import safe_error_message

logger = logging.getLogger(__name__)


class FarmerProfileViewSet(viewsets.ViewSet):
    """CRUD + helper actions for FarmerProfile."""

    permission_classes = [AllowAny]

    # ── GET: fetch profile ────────────────────────────────────────────────────
    def list(self, request):
        """
        GET /api/farmer-profile/?phone=+919876543210
        GET /api/farmer-profile/?session_id=sess_abc123
        """
        phone      = (request.query_params.get("phone") or "").strip()
        session_id = (request.query_params.get("session_id") or "").strip()

        if not phone and not session_id:
            return Response(
                {"error": "Provide phone or session_id query param"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from ...models import FarmerProfile
            q = Q()
            if phone:
                q |= Q(phone_number=phone)
            if session_id:
                q |= Q(session_id=session_id)
            profile = FarmerProfile.objects.filter(q).first()
            if not profile:
                return Response({"exists": False, "profile": None})
            return Response({"exists": True, "profile": self._serialize(profile)})
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
          "phone": "+919876543210",     // or "session_id"
          "session_id": "sess_abc",
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
        Upserts by phone_number if provided, else session_id.
        """
        d     = request.data
        phone = (d.get("phone") or "").strip()
        sid   = (d.get("session_id") or "").strip()

        if not phone and not sid:
            return Response(
                {"error": "phone or session_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from ...models import FarmerProfile
            lookup = {"phone_number": phone} if phone else {"session_id": sid}
            profile, created = FarmerProfile.objects.get_or_create(**lookup)

            # Update all provided fields
            field_map = {
                "session_id":        "session_id",
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

            profile.last_seen_at = datetime.now()
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
          "phone": "+91...",          // or session_id
          "season": "Rabi 2024-25",
          "crop": "wheat",
          "issue": "aphid"           // optional
        }
        Appends to the farmer's crop_history list (max 6 entries kept).
        """
        d      = request.data
        phone  = (d.get("phone") or "").strip()
        sid    = (d.get("session_id") or "").strip()
        season = d.get("season", "")
        crop   = d.get("crop", "")

        if not crop:
            return Response({"error": "crop is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not phone and not sid:
            return Response({"error": "phone or session_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from ...models import FarmerProfile
            lookup  = {"phone_number": phone} if phone else {"session_id": sid}
            profile = FarmerProfile.objects.filter(**lookup).first()
            if not profile:
                return Response({"error": "Farmer profile not found — create it first"}, status=status.HTTP_404_NOT_FOUND)

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
        GET /api/farmer-profile/context/?phone=+91...
        Returns the dict used to personalise the AI chatbot prompt.
        """
        phone = (request.query_params.get("phone") or "").strip()
        sid   = (request.query_params.get("session_id") or "").strip()
        try:
            from ...models import FarmerProfile
            q = Q()
            if phone:   q |= Q(phone_number=phone)
            if sid:     q |= Q(session_id=sid)
            profile = FarmerProfile.objects.filter(q).first() if (phone or sid) else None
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
        phone = (request.query_params.get("phone") or request.data.get("phone") or "").strip()
        sid = (request.query_params.get("session_id") or request.data.get("session_id") or "").strip()

        from ...models import FarmerProfile
        profile = None
        q = Q()
        if phone:
            q |= Q(phone_number=phone)
        if sid:
            q |= Q(session_id=sid)

        if q:
            profile = FarmerProfile.objects.filter(q).first()

        if not profile:
            if request.method in ["PATCH", "PUT"] or (sid or phone):
                lookup = {"phone_number": phone} if phone else {"session_id": sid or f"sess_{user.id if (user and user.is_authenticated) else 'anon'}"}
                profile, created = FarmerProfile.objects.get_or_create(**lookup)
            else:
                return Response(
                    {"exists": False, "profile": None, "message": "No profile matches your session_id or phone"},
                    status=status.HTTP_404_NOT_FOUND if request.method == "GET" else status.HTTP_400_BAD_REQUEST
                )

        if request.method in ["PATCH", "PUT"]:
            d = request.data
            field_map = {
                "session_id":        "session_id",
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

            profile.last_seen_at = datetime.now()
            profile.save()
            return Response({"status": "updated", "profile": self._serialize(profile)})

        # GET request
        profile.last_seen_at = datetime.now()
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
