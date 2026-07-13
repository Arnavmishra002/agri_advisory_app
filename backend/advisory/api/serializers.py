from collections.abc import Mapping
import re

from rest_framework import serializers
from ..models import CropAdvisory, Crop, User, ForumPost # Update import for models

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name')
        read_only_fields = ('role',) # Role should typically be set by admin, not user directly via registration

class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = '__all__'

class CropAdvisorySerializer(serializers.ModelSerializer):
    # Define choices for validation
    SOIL_TYPE_CHOICES = [
        ('sandy', 'Sandy'),
        ('clayey', 'Clayey'),
        ('loamy', 'Loamy'),
        ('silty', 'Silty'),
        ('peaty', 'Peaty'),
    ]
    WEATHER_CONDITION_CHOICES = [
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('rainy', 'Rainy'),
        ('humid', 'Humid'),
        ('dry', 'Dry'),
    ]

    crop = CropSerializer(read_only=True)
    crop_id = serializers.PrimaryKeyRelatedField(queryset=Crop.objects.all(), source='crop', write_only=True)
    soil_type = serializers.ChoiceField(choices=SOIL_TYPE_CHOICES)
    weather_condition = serializers.ChoiceField(choices=WEATHER_CONDITION_CHOICES)

    class Meta:
        model = CropAdvisory
        fields = '__all__'

class SMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    message = serializers.CharField(max_length=160, required=True)

class IVRInputSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    user_input = serializers.CharField(max_length=255, required=True)

class PestDetectionSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)

class TextToSpeechSerializer(serializers.Serializer):
    text = serializers.CharField(required=True)
    language = serializers.CharField(max_length=10, default='en')

class ForumPostSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = ForumPost
        fields = ('id', 'user', 'user_username', 'title', 'content', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

# API Endpoint Serializers for Swagger Documentation
class YieldPredictionSerializer(serializers.Serializer):
    crop_type = serializers.CharField(max_length=100, help_text="Type of crop (e.g., 'rice', 'wheat', 'corn')")
    soil_type = serializers.CharField(max_length=100, help_text="Type of soil (e.g., 'sandy', 'clayey', 'loamy')")
    weather_data = serializers.DictField(required=False, help_text="Weather data dictionary")
    temperature = serializers.FloatField(default=25.0, help_text="Temperature in Celsius")
    rainfall = serializers.FloatField(default=800.0, help_text="Rainfall in mm")
    humidity = serializers.FloatField(default=60.0, help_text="Humidity percentage")
    ph = serializers.FloatField(default=6.5, help_text="Soil pH level")
    organic_matter = serializers.FloatField(default=2.0, help_text="Organic matter percentage")
    season = serializers.CharField(default='kharif', help_text="Growing season (kharif/rabi)")

class ChatbotSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, help_text="User's question or query")
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('hi', 'Hindi'), ('hinglish', 'Hinglish'), ('auto', 'Auto-detect')],
        default='en', 
        help_text="Language code (en, hi, hinglish, auto)"
    )
    user_id = serializers.CharField(default='anonymous', max_length=100, help_text="User identifier")
    session_id = serializers.CharField(required=False, max_length=100, help_text="Session identifier")
    latitude = serializers.FloatField(required=False, help_text="Latitude coordinate")
    longitude = serializers.FloatField(required=False, help_text="Longitude coordinate")
    conversation_history = serializers.ListField(required=False, help_text="Previous conversation history")
    location_name = serializers.CharField(required=False, max_length=100, help_text="Location name")


class StrictSerializer(serializers.Serializer):
    """Reject silently ignored client fields on security-sensitive inputs."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Request body must be a JSON object.")
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"non_field_errors": [f"Unexpected field: {field}" for field in sorted(unknown)]}
            )
        return super().to_internal_value(data)


class TwilioWebhookInputSerializer(StrictSerializer):
    """Bounded form contract for Twilio SMS and Voice callbacks."""

    From = serializers.CharField(required=False, allow_blank=True, max_length=32)
    To = serializers.CharField(required=False, allow_blank=True, max_length=32)
    Body = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    SpeechResult = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    Digits = serializers.CharField(required=False, allow_blank=True, max_length=32)
    CallSid = serializers.CharField(required=False, allow_blank=True, max_length=128)
    AccountSid = serializers.CharField(required=False, allow_blank=True, max_length=128)
    CallStatus = serializers.CharField(required=False, allow_blank=True, max_length=32)
    Direction = serializers.CharField(required=False, allow_blank=True, max_length=64)
    MessageSid = serializers.CharField(required=False, allow_blank=True, max_length=128)
    MessageStatus = serializers.CharField(required=False, allow_blank=True, max_length=64)
    NumMedia = serializers.CharField(required=False, allow_blank=True, max_length=8)
    MediaUrl0 = serializers.URLField(required=False, allow_blank=True, max_length=2048)
    MediaContentType0 = serializers.CharField(required=False, allow_blank=True, max_length=128)
    RecordingUrl = serializers.URLField(required=False, allow_blank=True, max_length=2048)
    RecordingSid = serializers.CharField(required=False, allow_blank=True, max_length=128)
    RecordingStatus = serializers.CharField(required=False, allow_blank=True, max_length=32)
    RecordingDuration = serializers.CharField(required=False, allow_blank=True, max_length=16)
    Language = serializers.CharField(required=False, allow_blank=True, max_length=32)
    Confidence = serializers.CharField(required=False, allow_blank=True, max_length=16)
    ApiVersion = serializers.CharField(required=False, allow_blank=True, max_length=32)


class WhatsAppWebhookInputSerializer(StrictSerializer):
    """Validate the bounded subset of Meta webhook payloads we consume."""

    object = serializers.CharField(required=False, allow_blank=True, max_length=64)
    entry = serializers.ListField(
        required=True,
        child=serializers.DictField(),
        max_length=10,
    )

    @staticmethod
    def _check_dict(value, allowed, path):
        if not isinstance(value, Mapping):
            raise serializers.ValidationError({path: "must be an object"})
        unknown = set(value) - set(allowed)
        if unknown:
            raise serializers.ValidationError(
                {path: [f"Unexpected field: {field}" for field in sorted(unknown)]}
            )

    def validate(self, attrs):
        for entry_index, entry in enumerate(attrs.get("entry", [])):
            self._check_dict(entry, {"id", "changes"}, f"entry[{entry_index}]")
            changes = entry.get("changes", [])
            if not isinstance(changes, list) or len(changes) > 10:
                raise serializers.ValidationError({f"entry[{entry_index}].changes": "must contain at most 10 items"})
            for change_index, change in enumerate(changes):
                path = f"entry[{entry_index}].changes[{change_index}]"
                self._check_dict(change, {"field", "value"}, path)
                value = change.get("value", {})
                self._check_dict(
                    value,
                    {"messaging_product", "metadata", "contacts", "messages", "statuses"},
                    f"{path}.value",
                )
                messages = value.get("messages", [])
                if not isinstance(messages, list) or len(messages) > 10:
                    raise serializers.ValidationError({f"{path}.value.messages": "must contain at most 10 items"})
                for message_index, message in enumerate(messages):
                    message_path = f"{path}.value.messages[{message_index}]"
                    self._check_dict(
                        message,
                        {"from", "id", "timestamp", "type", "text", "audio", "image", "caption", "body"},
                        message_path,
                    )
                    for nested_name, nested_allowed in {
                        "text": {"body"},
                        "audio": {"id"},
                        "image": {"id", "caption", "mime_type", "sha256"},
                    }.items():
                        if nested_name in message:
                            self._check_dict(
                                message[nested_name],
                                nested_allowed,
                                f"{message_path}.{nested_name}",
                            )
                    for text_field in ("from", "id", "timestamp", "type", "caption", "body"):
                        if text_field in message and (
                            not isinstance(message[text_field], str) or len(message[text_field]) > 4000
                        ):
                            raise serializers.ValidationError(
                                {f"{message_path}.{text_field}": "must be a bounded string"}
                            )
        return attrs


class StrictQuerySerializer(StrictSerializer):
    """StrictSerializer variant used for query strings as well as JSON bodies."""


class EmptyInputSerializer(StrictSerializer):
    """Schema for endpoints that intentionally accept no request parameters."""


class WhatsAppVerificationQuerySerializer(StrictQuerySerializer):
    """Strict contract for Meta's three webhook verification parameters."""

    mode = serializers.ChoiceField(choices=("subscribe",))
    verify_token = serializers.CharField(max_length=512)
    challenge = serializers.CharField(max_length=2048)

    _META_FIELDS = frozenset({"hub.mode", "hub.verify_token", "hub.challenge"})

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Query parameters are required.")
        unknown = set(data) - self._META_FIELDS
        if unknown:
            raise serializers.ValidationError(
                {"non_field_errors": [f"Unexpected field: {field}" for field in sorted(unknown)]}
            )
        if hasattr(data, "getlist"):
            repeated = {
                field: "must be provided once"
                for field in self._META_FIELDS
                if len(data.getlist(field)) != 1
            }
            if repeated:
                raise serializers.ValidationError(repeated)
        return super().to_internal_value({
            "mode": data.get("hub.mode"),
            "verify_token": data.get("hub.verify_token"),
            "challenge": data.get("hub.challenge"),
        })


class LocationQuerySerializer(StrictQuerySerializer):
    """Common, bounded location and pagination query contract."""

    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)
    gps_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    gps_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    gps_latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    gps_longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, min_value=0, max_value=100000)
    accuracy_meters = serializers.FloatField(required=False, min_value=0, max_value=100000)
    gps_accuracy = serializers.FloatField(required=False, min_value=0, max_value=100000)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    location_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    village = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    place = serializers.CharField(required=False, allow_blank=True, max_length=200)
    address = serializers.CharField(required=False, allow_blank=True, max_length=300)
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)
    language = serializers.CharField(required=False, allow_blank=True, max_length=20)
    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    mandi = serializers.CharField(required=False, allow_blank=True, max_length=200)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50)
    radius_km = serializers.FloatField(required=False, min_value=1, max_value=500)
    include_estimates = serializers.BooleanField(required=False, default=False)
    category = serializers.CharField(required=False, allow_blank=True, max_length=100)
    strict = serializers.BooleanField(required=False, default=False)
    lang = serializers.CharField(required=False, allow_blank=True, max_length=20)
    field_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    previous_crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    nitrogen_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    phosphorus_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=2000)
    potassium_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    ph = serializers.FloatField(required=False, min_value=0, max_value=14)
    ec_ds_m = serializers.FloatField(required=False, min_value=0, max_value=100)
    moisture_pct = serializers.FloatField(required=False, min_value=0, max_value=100)
    organic_carbon = serializers.FloatField(required=False, min_value=0, max_value=100)


class CropRecommendationQuerySerializer(LocationQuerySerializer):
    """Strict farmer inputs used by the multi-factor crop engine."""

    _INPUT_FIELDS = frozenset({
        "season",
        "soil_type",
        "irrigation",
        "farm_size_ha",
        "budget_per_hectare",
        "risk_tolerance",
        "preferred_categories",
        "exclude_crops",
        "previous_crop",
        "nitrogen_kg_ha",
        "phosphorus_kg_ha",
        "potassium_kg_ha",
        "ph",
        "ec_ds_m",
        "moisture_pct",
        "organic_carbon",
    })

    season = serializers.ChoiceField(
        required=False,
        choices=("rabi", "kharif", "zaid", "year_round"),
    )
    soil_type = serializers.ChoiceField(
        required=False,
        choices=(
            "alluvial",
            "loamy",
            "sandy",
            "sandy_loam",
            "clay",
            "clay_loam",
            "black",
            "red",
            "laterite",
            "saline",
            "peaty",
        ),
    )
    irrigation = serializers.ChoiceField(
        required=False,
        choices=("rainfed", "low", "medium", "high", "drip", "sprinkler", "flood"),
    )
    farm_size_ha = serializers.FloatField(required=False, min_value=0.01, max_value=1_000_000)
    budget_per_hectare = serializers.FloatField(required=False, min_value=0, max_value=1_000_000_000)
    risk_tolerance = serializers.ChoiceField(
        required=False,
        choices=("low", "medium", "high"),
        default="medium",
    )
    preferred_categories = serializers.CharField(required=False, allow_blank=True, max_length=300)
    exclude_crops = serializers.CharField(required=False, allow_blank=True, max_length=500)

    @staticmethod
    def _split_csv(value, *, max_items):
        values = [item.strip() for item in str(value or "").split(",") if item.strip()]
        if len(values) > max_items:
            raise serializers.ValidationError(f"At most {max_items} values are allowed.")
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,79}", item) for item in values):
            raise serializers.ValidationError("Use comma-separated crop/category names only.")
        return values

    def validate_preferred_categories(self, value):
        allowed = {
            "aquatic", "aromatic", "cash", "cereal", "fiber", "flower",
            "fodder", "fruit", "leaf crop", "medicinal", "millet", "nut",
            "oilseed", "plantation", "pseudo cereal", "pulse", "spice",
            "vegetable",
        }
        values = self._split_csv(value, max_items=12)
        invalid = sorted({item.lower() for item in values} - allowed)
        if invalid:
            raise serializers.ValidationError(f"Unsupported categories: {', '.join(invalid)}")
        return [item.lower().title() for item in values]

    def validate_exclude_crops(self, value):
        return [
            item.lower().replace("-", "_").replace(" ", "_")
            for item in self._split_csv(value, max_items=30)
        ]

    @property
    def recommendation_inputs(self):
        if not hasattr(self, "validated_data"):
            raise AssertionError("Call is_valid() before reading recommendation_inputs.")
        return {
            key: self.validated_data[key]
            for key in self._INPUT_FIELDS
            if key in self.validated_data
        }


class GovernmentPestInputSerializer(StrictSerializer):
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120, default="Wheat")
    location = serializers.CharField(required=False, allow_blank=True, max_length=200, default="Delhi")
    language = serializers.CharField(required=False, allow_blank=True, max_length=20, default="hi")


class FarmerEligibilityProfileSerializer(StrictSerializer):
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    age = serializers.IntegerField(required=False, min_value=0, max_value=120)
    gender = serializers.CharField(required=False, allow_blank=True, max_length=30)
    category = serializers.CharField(required=False, allow_blank=True, max_length=50)
    farmer_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    land_size = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    land_size_acres = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    land_size_hectare = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    land_hectares = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    annual_income = serializers.FloatField(required=False, min_value=0, max_value=1_000_000_000)
    pincode = serializers.RegexField(required=False, regex=r"^\d{6}$")
    has_pm_kisan = serializers.BooleanField(required=False)
    has_kcc = serializers.BooleanField(required=False)
    has_pmfby = serializers.BooleanField(required=False)


class SchemeEligibilityInputSerializer(StrictSerializer):
    farmer_profile = FarmerEligibilityProfileSerializer()


class LogoutInputSerializer(StrictSerializer):
    refresh = serializers.CharField(required=False, allow_blank=True, max_length=4096)


class RateLimitResetInputSerializer(StrictSerializer):
    client_id = serializers.RegexField(regex=r"^[A-Za-z0-9:_./@+-]{1,160}$")


class DiagnosticMultipartPredictInputSerializer(StrictSerializer):
    image = serializers.FileField(required=True)
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    crop_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    commodity = serializers.CharField(required=False, allow_blank=True, max_length=120)
    language = serializers.ChoiceField(required=False, choices=("hi", "en", "hinglish"), default="hi")
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)


class PestDetectionInputSerializer(StrictSerializer):
    image = serializers.CharField(required=False, allow_blank=False)
    image_base64 = serializers.CharField(required=False, allow_blank=False)
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200, default="Delhi")
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    language = serializers.CharField(required=False, allow_blank=True, max_length=20, default="hi")


class OTPRequestInputSerializer(StrictSerializer):
    phone_number = serializers.CharField(min_length=10, max_length=16, trim_whitespace=True)


class OTPVerifyInputSerializer(StrictSerializer):
    phone_number = serializers.CharField(min_length=10, max_length=16, trim_whitespace=True)
    otp_code = serializers.RegexField(regex=r"^\d{6}$")
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)


class RegistrationInputSerializer(StrictSerializer):
    username = serializers.RegexField(
        regex=r"^[A-Za-z0-9_.-]{3,64}$",
        max_length=64,
    )
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=16)
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    language = serializers.ChoiceField(
        required=False,
        choices=("hi", "en", "hinglish"),
        default="hi",
    )
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ChatHistoryEntrySerializer(StrictSerializer):
    role = serializers.ChoiceField(choices=("user", "assistant"), default="user")
    content = serializers.CharField(max_length=2000, allow_blank=False)
    intent = serializers.CharField(required=False, allow_blank=True, max_length=80)


class ChatbotRequestSerializer(StrictSerializer):
    query = serializers.CharField(max_length=2000, trim_whitespace=True)
    language = serializers.ChoiceField(
        choices=("hi", "en", "hinglish", "auto"), default="hi"
    )
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    fast_mode = serializers.BooleanField(required=False, default=False)
    history = serializers.ListField(
        required=False,
        child=ChatHistoryEntrySerializer(),
        max_length=20,
    )
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)
    gps_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    gps_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, min_value=0, max_value=100000)
    accuracy_meters = serializers.FloatField(required=False, min_value=0, max_value=100000)
    gps_accuracy = serializers.FloatField(required=False, min_value=0, max_value=100000)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    location_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    village = serializers.CharField(required=False, allow_blank=True, max_length=120)
    district = serializers.CharField(required=False, allow_blank=True, max_length=120)
    place = serializers.CharField(required=False, allow_blank=True, max_length=200)
    address = serializers.CharField(required=False, allow_blank=True, max_length=300)
    state = serializers.CharField(required=False, allow_blank=True, max_length=120)


class FarmerCropHistoryEntrySerializer(StrictSerializer):
    season = serializers.CharField(max_length=40, allow_blank=True, required=False)
    crop = serializers.CharField(max_length=100)
    issue = serializers.CharField(max_length=200, allow_blank=True, required=False)
    yield_qtl = serializers.FloatField(required=False, min_value=0, max_value=100000)


class FarmerProfileInputSerializer(StrictSerializer):
    # Legacy client fields are accepted but never used for ownership.
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20, write_only=True)
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100, write_only=True)
    location_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    district = serializers.CharField(required=False, allow_blank=True, max_length=100)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    farm_size_bigha = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    farm_size_hectare = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)
    current_crop = serializers.CharField(required=False, allow_blank=True, max_length=100)
    current_season = serializers.CharField(required=False, allow_blank=True, max_length=20)
    soil_ph = serializers.FloatField(required=False, min_value=0, max_value=14)
    soil_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    irrigation_type = serializers.ChoiceField(
        required=False,
        choices=("", "drip", "sprinkler", "flood", "rainfed"),
    )
    preferred_language = serializers.ChoiceField(
        required=False,
        choices=("hi", "en", "hinglish"),
    )
    has_pm_kisan = serializers.BooleanField(required=False)
    has_kcc = serializers.BooleanField(required=False)
    has_pmfby = serializers.BooleanField(required=False)
    pm_kisan_status = serializers.ChoiceField(
        required=False,
        choices=("", "active", "pending", "none"),
    )
    whatsapp_opt_in = serializers.BooleanField(required=False)


class FarmerCropInputSerializer(StrictSerializer):
    season = serializers.CharField(required=False, allow_blank=True, max_length=40)
    crop = serializers.CharField(max_length=100)
    issue = serializers.CharField(required=False, allow_blank=True, max_length=200)
    yield_qtl = serializers.FloatField(required=False, min_value=0, max_value=100000)


class SensorValuesInputSerializer(StrictSerializer):
    nitrogen_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    phosphorus_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=2000)
    potassium_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    ph = serializers.FloatField(required=False, min_value=0, max_value=14)
    ec_ds_m = serializers.FloatField(required=False, min_value=0, max_value=100)
    moisture_pct = serializers.FloatField(required=False, min_value=0, max_value=100)
    soil_temp_c = serializers.FloatField(required=False, min_value=-20, max_value=80)
    organic_carbon = serializers.FloatField(required=False, min_value=0, max_value=100)
    bulk_density = serializers.FloatField(required=False, min_value=0, max_value=10)


class FieldSensorInputSerializer(StrictSerializer):
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    location_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    language = serializers.ChoiceField(required=False, choices=("hi", "en", "hinglish"), default="hi")
    field_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    sensors = SensorValuesInputSerializer(required=False)
    nitrogen_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    phosphorus_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=2000)
    potassium_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    ph = serializers.FloatField(required=False, min_value=0, max_value=14)
    ec_ds_m = serializers.FloatField(required=False, min_value=0, max_value=100)
    moisture_pct = serializers.FloatField(required=False, min_value=0, max_value=100)
    soil_temp_c = serializers.FloatField(required=False, min_value=-20, max_value=80)
    organic_carbon = serializers.FloatField(required=False, min_value=0, max_value=100)
    bulk_density = serializers.FloatField(required=False, min_value=0, max_value=10)
    crop_history = serializers.ListField(required=False, child=serializers.CharField(max_length=100), max_length=10)
    previous_crop = serializers.CharField(required=False, allow_blank=True, max_length=100)
    irrigation_type = serializers.ChoiceField(
        required=False, choices=("unknown", "drip", "sprinkler", "flood", "rainfed")
    )
    field_area_ha = serializers.FloatField(required=False, min_value=0, max_value=1_000_000)


class TextToSpeechInputSerializer(StrictSerializer):
    text = serializers.CharField(max_length=500, trim_whitespace=True)
    language = serializers.ChoiceField(
        required=False,
        choices=("hi", "en", "mr", "ta", "te", "gu", "pa", "bn", "kn", "ml", "or", "as"),
        default="hi",
    )


class AdvisoryAudioInputSerializer(StrictSerializer):
    query = serializers.CharField(max_length=2000, trim_whitespace=True)
    language = serializers.ChoiceField(
        required=False,
        choices=("hi", "en", "mr", "ta", "te", "gu", "pa", "bn", "kn", "ml"),
        default="hi",
    )
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)


class DiagnosticDetectInputSerializer(StrictSerializer):
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    language = serializers.ChoiceField(required=False, choices=("hi", "en", "hinglish"), default="hi")
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, min_value=0, max_value=100000)
    images = serializers.DictField(
        required=False,
        child=serializers.CharField(allow_blank=False),
    )


class DiagnosticPredictInputSerializer(StrictSerializer):
    image = serializers.CharField(required=False, allow_blank=False)
    image_base64 = serializers.CharField(required=False, allow_blank=False)
    images = serializers.DictField(required=False, child=serializers.CharField(allow_blank=False))
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120)
    crop_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    commodity = serializers.CharField(required=False, allow_blank=True, max_length=120)
    language = serializers.ChoiceField(required=False, choices=("hi", "en", "hinglish"), default="hi")


class DiagnosticFeedbackInputSerializer(StrictSerializer):
    session_id = serializers.CharField(max_length=100)
    is_correct = serializers.BooleanField()
    correct_diagnosis = serializers.CharField(required=False, allow_blank=True, max_length=200)

class FertilizerRecommendationSerializer(serializers.Serializer):
    crop_type = serializers.CharField(max_length=100, help_text="Type of crop")
    soil_type = serializers.CharField(max_length=100, help_text="Type of soil")
    season = serializers.CharField(default='kharif', max_length=50, help_text="Growing season")
    area_hectares = serializers.FloatField(default=1.0, help_text="Area in hectares")
    language = serializers.CharField(default='en', max_length=10, help_text="Language code")

class CropRecommendationSerializer(serializers.Serializer):
    soil_type = serializers.CharField(max_length=100, required=False, help_text="Type of soil (auto-detected if not provided)")
    latitude = serializers.FloatField(help_text="Latitude coordinate")
    longitude = serializers.FloatField(help_text="Longitude coordinate")
    season = serializers.CharField(default='kharif', max_length=50, help_text="Growing season")
    user_id = serializers.CharField(default='anonymous', max_length=100, help_text="User identifier")
    forecast_days = serializers.IntegerField(default=7, min_value=1, max_value=14, help_text="Weather forecast days")

class FeedbackSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=100, help_text="User identifier")
    session_id = serializers.CharField(max_length=100, help_text="Session identifier")
    prediction_type = serializers.CharField(max_length=100, help_text="Type of prediction")
    input_data = serializers.DictField(help_text="Input data used for prediction")
    system_prediction = serializers.DictField(help_text="System's prediction")
    actual_result = serializers.DictField(help_text="Actual result")
    feedback_rating = serializers.IntegerField(min_value=1, max_value=5, help_text="Rating from 1-5")
    feedback_text = serializers.CharField(required=False, max_length=500, help_text="Additional feedback text")
    latitude = serializers.FloatField(required=False, help_text="Latitude coordinate")
    longitude = serializers.FloatField(required=False, help_text="Longitude coordinate")


class InputGapsInputSerializer(StrictSerializer):
    crop = serializers.CharField(required=False, allow_blank=True, max_length=120, default="wheat")
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    location_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    language = serializers.CharField(required=False, allow_blank=True, max_length=20, default="hi")
    sensors = SensorValuesInputSerializer(required=False)
    nitrogen_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    phosphorus_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=2000)
    potassium_kg_ha = serializers.FloatField(required=False, min_value=0, max_value=5000)
    ph = serializers.FloatField(required=False, min_value=0, max_value=14)
    ec_ds_m = serializers.FloatField(required=False, min_value=0, max_value=100)
    moisture_pct = serializers.FloatField(required=False, min_value=0, max_value=100)
    organic_carbon = serializers.FloatField(required=False, min_value=0, max_value=100)
