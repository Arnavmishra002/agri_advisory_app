"""
KrishiMitra — Django Admin Configuration
==========================================
Registers all production models with useful search, filter,
and display columns so the team can monitor farmer activity,
debug chat issues, and manage data without writing queries.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ChatHistory,
    ChatSession,
    Crop,
    CropAdvisory,
    DiagnosticSession,
    FarmerProfile,
    ForumPost,
    IoTSensorReading,
    User,
)

try:
    from .models import ExpertVerification
    _HAS_EXPERT = True
except ImportError:
    _HAS_EXPERT = False

# ── Site branding ─────────────────────────────────────────────────────────────
admin.site.site_header = "🌾 KrishiMitra AI Admin"
admin.site.site_title  = "KrishiMitra Admin"
admin.site.index_title = "Farmer Advisory Platform"


# ─────────────────────────────────────────────────────────────────────────────
#  User
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display  = ("username", "email", "role", "is_active", "date_joined")
    list_filter   = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering      = ("-date_joined",)


# ─────────────────────────────────────────────────────────────────────────────
#  FarmerProfile
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display  = (
        "phone_display", "state", "district", "current_crop",
        "preferred_language", "whatsapp_opt_in", "last_seen_at",
    )
    list_filter   = (
        "state", "preferred_language", "whatsapp_opt_in",
        "has_pm_kisan", "has_kcc", "irrigation_type",
    )
    search_fields  = ("phone_number", "session_id", "state", "district", "current_crop")
    readonly_fields = ("created_at", "last_seen_at", "updated_at")
    ordering       = ("-last_seen_at",)
    fieldsets = (
        ("Identity", {
            "fields": ("phone_number", "session_id", "preferred_language", "whatsapp_opt_in"),
        }),
        ("Location", {
            "fields": ("location_name", "state", "district", "latitude", "longitude"),
        }),
        ("Farm", {
            "fields": (
                "farm_size_bigha", "farm_size_hectare",
                "current_crop", "current_season",
                "soil_type", "soil_ph", "irrigation_type",
                "crop_history",
            ),
        }),
        ("Government Schemes", {
            "fields": ("has_pm_kisan", "pm_kisan_status", "has_kcc", "has_pmfby"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "last_seen_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def phone_display(self, obj):
        p = obj.phone_number or ""
        if len(p) > 6:
            return p[:4] + "****" + p[-2:]
        return p or "(session only)"
    phone_display.short_description = "Phone"


# ─────────────────────────────────────────────────────────────────────────────
#  ChatSession
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display  = ("session_id_short", "preferred_language", "is_active", "last_activity")
    list_filter   = ("preferred_language", "is_active")
    search_fields = ("session_id", "user_id")
    readonly_fields = ("last_activity",)
    ordering      = ("-last_activity",)

    def session_id_short(self, obj):
        s = obj.session_id or ""
        return (s[:20] + "…") if len(s) > 20 else s
    session_id_short.short_description = "Session ID"


# ─────────────────────────────────────────────────────────────────────────────
#  ChatHistory  (most useful for debugging chatbot issues)
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display  = (
        "session_short", "message_type", "lang_badge",
        "intent_tag", "content_preview", "created_at",
    )
    list_filter   = ("message_type", "detected_language", "response_type", "has_location")
    search_fields = ("session_id", "user_id", "message_content")
    readonly_fields = ("created_at",)
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"

    def session_short(self, obj):
        s = obj.session_id or ""
        return (s[:16] + "…") if len(s) > 16 else s
    session_short.short_description = "Session"

    def lang_badge(self, obj):
        lang = obj.detected_language or "?"
        colors = {"hi": "#ff9800", "en": "#2196f3", "mr": "#4caf50",
                  "ta": "#9c27b0", "te": "#e91e63", "gu": "#00bcd4"}
        color = colors.get(lang, "#607d8b")
        return format_html(
            '<span style="background:{};color:#fff;padding:1px 6px;'
            'border-radius:3px;font-size:11px">{}</span>',
            color, lang.upper()
        )
    lang_badge.short_description = "Lang"

    def intent_tag(self, obj):
        return obj.response_type or "—"
    intent_tag.short_description = "Intent"

    def content_preview(self, obj):
        c = obj.message_content or ""
        return (c[:80] + "…") if len(c) > 80 else c
    content_preview.short_description = "Message"


# ─────────────────────────────────────────────────────────────────────────────
#  DiagnosticSession  (crop disease detection logs)
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(DiagnosticSession)
class DiagnosticSessionAdmin(admin.ModelAdmin):
    list_display  = (
        "session_id_short", "crop_detected", "final_diagnosis",
        "confidence_pct", "severity_level", "created_at",
    )
    list_filter   = ("severity_level", "crop_detected")
    search_fields = ("session_id", "crop_detected", "final_diagnosis")
    readonly_fields = ("created_at",)
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"

    def session_id_short(self, obj):
        s = str(obj.session_id or "")
        return (s[:12] + "…") if len(s) > 12 else s
    session_id_short.short_description = "Session"

    def confidence_pct(self, obj):
        pct = (obj.confidence_score or 0) * 100
        color = "#4caf50" if pct > 70 else "#ff9800" if pct > 40 else "#f44336"
        return format_html('<span style="color:{};font-weight:bold">{:.0f}%</span>', color, pct)
    confidence_pct.short_description = "Confidence"


# ─────────────────────────────────────────────────────────────────────────────
#  IoTSensorReading  (ESP32 field telemetry)
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(IoTSensorReading)
class IoTSensorReadingAdmin(admin.ModelAdmin):
    list_display  = (
        "field_id", "sensor_device_id", "moisture_pct",
        "ph", "nitrogen_short", "state", "created_at",
    )
    list_filter   = ("state", "sensor_device_id")
    search_fields = ("field_id", "sensor_device_id", "state")
    readonly_fields = ("created_at",)
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"

    def nitrogen_short(self, obj):
        if obj.nitrogen_kg_ha is None:
            return "—"
        return f"{obj.nitrogen_kg_ha:.0f} kg/ha"
    nitrogen_short.short_description = "N (kg/ha)"


# ─────────────────────────────────────────────────────────────────────────────
#  Crop & CropAdvisory
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)


@admin.register(CropAdvisory)
class CropAdvisoryAdmin(admin.ModelAdmin):
    list_display  = ("crop", "soil_type", "weather_condition", "created_at")
    list_filter   = ("soil_type", "weather_condition")
    search_fields = ("crop__name",)
    ordering      = ("-created_at",)


# ─────────────────────────────────────────────────────────────────────────────
#  ForumPost
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display  = ("title", "user", "created_at")
    search_fields = ("title", "content", "user__username")
    ordering      = ("-created_at",)


# ─────────────────────────────────────────────────────────────────────────────
#  ExpertVerification  (Active Learning feedback)
# ─────────────────────────────────────────────────────────────────────────────
if _HAS_EXPERT:
    @admin.register(ExpertVerification)
    class ExpertVerificationAdmin(admin.ModelAdmin):
        list_display  = ("diagnostic_session", "is_verified", "expert_diagnosis", "verified_at")
        list_filter   = ("is_verified",)
        search_fields = ("expert_diagnosis", "expert_notes")
        ordering      = ("-verified_at",)

