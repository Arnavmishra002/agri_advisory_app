from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.

class User(AbstractUser):
    ROLES = (
        ('farmer', 'Farmer'),
        ('admin', 'Admin'),
        ('officer', 'Officer'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='farmer')

class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    ideal_soil_type = models.CharField(max_length=100)
    min_temperature_c = models.FloatField()
    max_temperature_c = models.FloatField()
    min_rainfall_mm_per_month = models.FloatField()
    max_rainfall_mm_per_month = models.FloatField()
    duration_days = models.IntegerField(help_text="Approximate duration of crop cycle in days")
    
    # MSP 2024-25 (₹/quintal, 0 = no MSP for this crop)
    msp_per_quintal = models.PositiveIntegerField(
        default=0,
        help_text="Minimum Support Price ₹/quintal (0 = no government MSP). "
                  "Update annually after CACP Cabinet approval.",
    )
    # Season for quick filtering
    season = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="rabi | kharif | zaid | year_round",
    )
    # Hindi name for multilingual UI
    name_hindi = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Crop name in Hindi script",
    )
    # MSP year label so we know which announcement is in the DB
    msp_season = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Season the MSP applies to e.g. '2024-25'",
    )

    def __str__(self):
        return self.name

class CropAdvisory(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='advisories')
    soil_type = models.CharField(max_length=100)
    weather_condition = models.CharField(max_length=100)
    recommendation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop.name} - {self.soil_type}"

class UserFeedback(models.Model):
    """Model to store user feedback for ML model improvement"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, help_text="Session identifier")
    prediction_type = models.CharField(max_length=50, help_text="Type of prediction (crop_recommendation, yield_prediction, etc.)")
    
    # Input data that was used for prediction
    input_data = models.JSONField(help_text="Input parameters used for prediction")
    
    # Prediction made by the system
    system_prediction = models.JSONField(help_text="System's prediction")
    
    # User's actual results/feedback
    actual_result = models.JSONField(help_text="Actual result or user's feedback")
    
    # Feedback rating (1-5 scale)
    feedback_rating = models.IntegerField(help_text="User rating from 1-5")
    
    # Additional feedback text
    feedback_text = models.TextField(blank=True, null=True, help_text="Additional user comments")
    
    # Location data
    latitude = models.FloatField(null=True, blank=True, help_text="User's latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="User's longitude")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_feedback'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['prediction_type', 'created_at']),
            models.Index(fields=['feedback_rating', 'created_at']),
        ]
    
    def __str__(self):
        return f"Feedback from {self.user_id} for {self.prediction_type} - Rating: {self.feedback_rating}"

class MLModelPerformance(models.Model):
    """Model to track ML model performance metrics"""
    
    model_name = models.CharField(max_length=100, help_text="Name of the ML model")
    model_version = models.CharField(max_length=50, help_text="Model version")
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, help_text="Model accuracy")
    precision = models.FloatField(null=True, blank=True, help_text="Model precision")
    recall = models.FloatField(null=True, blank=True, help_text="Model recall")
    f1_score = models.FloatField(null=True, blank=True, help_text="Model F1 score")
    r2_score = models.FloatField(null=True, blank=True, help_text="Model R2 score")
    rmse = models.FloatField(null=True, blank=True, help_text="Root Mean Square Error")
    
    # Training information
    training_samples = models.IntegerField(help_text="Number of training samples")
    validation_samples = models.IntegerField(help_text="Number of validation samples")
    training_date = models.DateTimeField(help_text="Date when model was trained")
    
    # Model metadata
    model_parameters = models.JSONField(help_text="Model hyperparameters")
    feature_importance = models.JSONField(null=True, blank=True, help_text="Feature importance scores")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ml_model_performance'
        ordering = ['-training_date']
    
    def __str__(self):
        return f"{self.model_name} v{self.model_version} - Accuracy: {self.accuracy}"

class UserSession(models.Model):
    """Model to track user sessions and interactions"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique session identifier")
    
    # Session metadata
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_interactions = models.IntegerField(default=0)
    
    # Location data
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Session preferences
    preferred_language = models.CharField(max_length=10, default='en')
    device_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Session summary
    session_summary = models.JSONField(null=True, blank=True, help_text="Summary of session interactions")
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} for user {self.user_id}"

class ChatHistory(models.Model):
    """Model to persist chat conversation history"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, help_text="Session identifier")
    
    # Message details
    message_type = models.CharField(
        max_length=20, 
        choices=[
            ('user', 'User Message'),
            ('assistant', 'Assistant Response'),
            ('system', 'System Message')
        ],
        help_text="Type of message"
    )
    message_content = models.TextField(help_text="The actual message content")
    
    # Language and processing info
    detected_language = models.CharField(max_length=10, default="", blank=True, help_text="Detected language")
    response_language = models.CharField(max_length=10, default="", blank=True, help_text="Response language")
    
    # Response metadata
    confidence_score = models.FloatField(null=True, blank=True, help_text="Confidence score of response")
    response_source = models.CharField(max_length=50, default="", blank=True, help_text="Source of response (advanced_chatbot, fallback, etc.)")
    response_type = models.CharField(max_length=50, default="", blank=True, help_text="Type of response (greeting, agricultural, etc.)")
    
    # Context information
    has_location = models.BooleanField(default=False, help_text="Whether location was detected")
    has_product = models.BooleanField(default=False, help_text="Whether product was mentioned")
    latitude = models.FloatField(null=True, blank=True, help_text="User's latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="User's longitude")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_history'
        ordering = ['session_id', 'created_at']
        indexes = [
            # BUG 6 FIX: explicit single-column index so PostgreSQL can satisfy
            # plain `WHERE session_id = ?` without needing ORDER BY created_at.
            # Without this, load_history() causes full table scans at scale.
            models.Index(fields=['session_id']),
            models.Index(fields=['user_id', 'session_id']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.message_type} from {self.user_id} in session {self.session_id}"

class ChatSession(models.Model):
    """Model to track chat sessions with enhanced metadata"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique session identifier")
    
    # Session metadata
    start_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Conversation context
    conversation_context = models.JSONField(
        default=dict,
        help_text="Persistent conversation context including location, preferences, etc."
    )
    
    # Session preferences
    preferred_language = models.CharField(max_length=10, default='auto')
    location_name = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Session statistics
    total_messages = models.IntegerField(default=0)
    user_messages = models.IntegerField(default=0)
    assistant_messages = models.IntegerField(default=0)
    
    # Device and browser info
    device_type = models.CharField(max_length=50, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_sessions'
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['session_id']),
            models.Index(fields=['is_active', 'last_activity']),
        ]
    
    def __str__(self):
        return f"Chat session {self.session_id} for user {self.user_id}"

class ForumPost(models.Model):
    """
    Model for community forum posts.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.user.username}"

class DiagnosticSession(models.Model):
    """
    Tracks a user's multi-step diagnostic session (KrishiRaksha 2.0).
    """
    user_id = models.CharField(max_length=100, help_text="User ID")
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    crop_detected = models.CharField(max_length=100, blank=True, null=True)
    images_json = models.JSONField(default=dict, help_text="{'whole': '/path/to/img1', 'close_up': '/path/to/img2'}")
    
    # Analysis results
    final_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    confidence_score = models.FloatField(default=0.0)
    severity_level = models.CharField(max_length=50, blank=True, null=True) # Low, Medium, High
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnostic {self.session_id} - {self.crop_detected}"

class IoTSensorReading(models.Model):
    """
    Stores IoT field sensor readings for historical soil analysis.
    """
    field_id         = models.CharField(max_length=100, db_index=True, help_text="Farmer's field identifier")
    latitude         = models.FloatField()
    longitude        = models.FloatField()
    location_name    = models.CharField(max_length=200, blank=True)
    state            = models.CharField(max_length=100, blank=True)

    # NPK Nutrients (kg/ha)
    nitrogen_kg_ha   = models.FloatField(null=True, blank=True)
    phosphorus_kg_ha = models.FloatField(null=True, blank=True)
    potassium_kg_ha  = models.FloatField(null=True, blank=True)

    # Soil chemistry
    ph               = models.FloatField(null=True, blank=True)
    ec_ds_m          = models.FloatField(null=True, blank=True, help_text="Electrical Conductivity dS/m")
    organic_carbon   = models.FloatField(null=True, blank=True, help_text="OC %")
    sulfur_ppm       = models.FloatField(null=True, blank=True)
    zinc_ppm         = models.FloatField(null=True, blank=True)

    # Physical
    moisture_pct     = models.FloatField(null=True, blank=True, help_text="Volumetric moisture %")
    soil_temp_c      = models.FloatField(null=True, blank=True)
    bulk_density     = models.FloatField(null=True, blank=True)

    # Metadata
    sensor_device_id = models.CharField(max_length=100, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "iot_sensor_readings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["field_id", "created_at"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(
                fields=["latitude", "longitude", "created_at"],
                name="iot_latlon_createdat_idx",
            ),
        ]

    def __str__(self):
        return f"Sensor {self.field_id} @ {self.latitude},{self.longitude} — {self.created_at.date()}"


class FieldSoilHistory(models.Model):
    """
    Aggregated soil history per GPS grid cell (0.001° ≈ 100m resolution).
    Updated from IoT readings and Soil Health Card.
    """
    lat_grid   = models.FloatField(db_index=True, help_text="latitude rounded to 3dp")
    lon_grid   = models.FloatField(db_index=True, help_text="longitude rounded to 3dp")
    state      = models.CharField(max_length=100, blank=True)
    district   = models.CharField(max_length=100, blank=True)

    # Averaged nutrient values
    avg_nitrogen   = models.FloatField(null=True, blank=True)
    avg_phosphorus = models.FloatField(null=True, blank=True)
    avg_potassium  = models.FloatField(null=True, blank=True)
    avg_ph         = models.FloatField(null=True, blank=True)
    avg_oc         = models.FloatField(null=True, blank=True)
    avg_ec         = models.FloatField(null=True, blank=True)

    # Trend
    reading_count  = models.IntegerField(default=0)
    last_updated   = models.DateTimeField(auto_now=True)
    data_source    = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "field_soil_history"
        unique_together = [("lat_grid", "lon_grid")]

class ExpertVerification(models.Model):
    """
    For 'Active Learning': difficult cases sent to experts.
    """
    diagnostic_session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    expert_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    expert_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Verification for {self.diagnostic_session.session_id}"


class FarmerProfile(models.Model):
    """
    Persistent farmer profile — turns the chatbot into a personal advisor.
    Keyed by phone_number (WhatsApp/SMS identifier) or session_id.

    With this data the AI can say:
      "Last Rabi you grew wheat and had aphid issues. This year with soil
       pH 6.8 and current rainfall forecast, mustard is a 15% better choice."
    """
    # Identity — one of these must be set
    phone_number  = models.CharField(
        max_length=20, blank=True, db_index=True,
        help_text="WhatsApp/SMS number in E.164 format e.g. +919876543210",
    )
    session_id    = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Web/app session ID for non-WhatsApp users",
    )

    # Location
    location_name = models.CharField(max_length=200, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    district      = models.CharField(max_length=100, blank=True)
    latitude      = models.FloatField(null=True, blank=True)
    longitude     = models.FloatField(null=True, blank=True)

    # Farm details
    farm_size_bigha   = models.FloatField(null=True, blank=True, help_text="Farm size in bigha")
    farm_size_hectare = models.FloatField(null=True, blank=True, help_text="Farm size in hectare (1 bigha ≈ 0.2 ha)")
    irrigation_type   = models.CharField(
        max_length=30, blank=True,
        help_text="drip | sprinkler | flood | rainfed",
    )
    soil_type         = models.CharField(max_length=50, blank=True, help_text="loamy | clay | sandy | black | red")
    soil_ph           = models.FloatField(null=True, blank=True)

    # Crop history — last 3 seasons (JSON list of {season, crop, issue})
    crop_history      = models.JSONField(
        default=list,
        help_text='e.g. [{"season":"Rabi 2023-24","crop":"wheat","issue":"aphid"}]',
    )
    current_crop      = models.CharField(max_length=100, blank=True)
    current_season    = models.CharField(max_length=20, blank=True, help_text="Kharif 2025 | Rabi 2025-26")

    # Government enrollments
    has_pm_kisan    = models.BooleanField(default=False)
    has_kcc         = models.BooleanField(default=False)
    has_pmfby       = models.BooleanField(default=False)
    pm_kisan_status = models.CharField(max_length=20, blank=True, help_text="active | pending | none")

    # Preferences
    preferred_language = models.CharField(max_length=10, default="hi")
    whatsapp_opt_in    = models.BooleanField(default=True)

    # Metadata
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "farmer_profiles"
        indexes  = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["session_id"]),
            models.Index(fields=["state", "district"]),
        ]

    def __str__(self):
        return f"Farmer {self.phone_number or self.session_id} — {self.location_name or 'unknown'}"

    def crop_history_summary(self) -> str:
        """Return a compact string for injection into the AI prompt."""
        if not self.crop_history:
            return "No crop history recorded."
        parts = []
        for entry in self.crop_history[-3:]:
            season = entry.get("season", "?")
            crop   = entry.get("crop",   "?")
            issue  = entry.get("issue",  "")
            parts.append(f"{season}: {crop}" + (f" (issue: {issue})" if issue else ""))
        return " | ".join(parts)

    def to_context_dict(self) -> dict:
        """Return a dict suitable for injecting into the AI prompt context."""
        return {
            "location":        self.location_name or self.district or self.state,
            "state":           self.state,
            "farm_size_bigha": self.farm_size_bigha,
            "current_crop":    self.current_crop,
            "current_season":  self.current_season,
            "soil_ph":         self.soil_ph,
            "irrigation_type": self.irrigation_type,
            "crop_history":    self.crop_history_summary(),
            "has_pm_kisan":    self.has_pm_kisan,
            "has_kcc":         self.has_kcc,
            "language":        self.preferred_language,
        }


class FarmerInteractionLog(models.Model):
    """
    Stores every farmer–AI interaction for future ML training and analytics.

    This is the prediction dataset. Each row = one chat Q&A with full context:
      - The question and answer
      - Intent classification (irrigation, pest, market, etc.)
      - Sensor data at the time of the question
      - Weather conditions
      - Crops mentioned
      - AI tier used (Gemini / Qwen / rule-based)
      - Whether the farmer gave positive/negative feedback

    Use cases:
      1. Fine-tune Qwen on real farmer queries → better Hindi/regional responses
      2. Train intent classifier on labelled query data
      3. Predict crop disease risk from seasonal interaction patterns
      4. Personalise crop recommendations from historical chat context
      5. Measure AI response quality (feedback_rating) for A/B testing
    """
    # Identity
    session_id     = models.CharField(max_length=100, db_index=True)
    phone_number   = models.CharField(max_length=20, blank=True, db_index=True)
    location_name  = models.CharField(max_length=200, blank=True)
    state          = models.CharField(max_length=100, blank=True)
    latitude       = models.FloatField(null=True, blank=True)
    longitude      = models.FloatField(null=True, blank=True)

    # Interaction
    query          = models.TextField(help_text="Farmer's question")
    response       = models.TextField(help_text="AI response text")
    intent         = models.CharField(max_length=50, blank=True,
                                      help_text="Classified intent: irrigation, pest_disease, market_price, etc.")
    language       = models.CharField(max_length=10, default="hi")
    crops_detected = models.JSONField(default=list, help_text="Crop names extracted from the query")
    ai_tier        = models.CharField(max_length=30, blank=True,
                                      help_text="gemini | qwen_rag | rule_based")
    data_source    = models.CharField(max_length=100, blank=True)

    # Contextual data at query time (for ML feature engineering)
    sensor_data    = models.JSONField(null=True, blank=True,
                                      help_text="IoT sensor readings: moisture, NPK, pH at time of query")
    weather_data   = models.JSONField(null=True, blank=True,
                                      help_text="Weather conditions: temp, humidity, alerts at time of query")
    market_prices  = models.JSONField(null=True, blank=True,
                                      help_text="Top crop prices at time of query for market-related queries")
    season         = models.CharField(max_length=30, blank=True)

    # Feedback (for reinforcement learning / quality measurement)
    feedback_score = models.IntegerField(null=True, blank=True,
                                         help_text="1-5 farmer satisfaction rating (from feedback button)")
    feedback_text  = models.TextField(blank=True, help_text="Optional feedback text")
    is_helpful     = models.BooleanField(null=True, blank=True,
                                         help_text="True/False from thumbs up/down")

    # Metadata
    response_time_ms = models.IntegerField(null=True, blank=True,
                                            help_text="AI response generation time in milliseconds")
    created_at       = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "farmer_interaction_logs"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["session_id", "created_at"], name="fil_session_idx"),
            models.Index(fields=["intent", "created_at"], name="fil_intent_idx"),
            models.Index(fields=["state", "intent"], name="fil_state_intent_idx"),
            models.Index(fields=["ai_tier", "created_at"], name="fil_tier_idx"),
            models.Index(fields=["language", "created_at"], name="fil_lang_idx"),
        ]

    def __str__(self):
        return f"[{self.intent}] {self.query[:60]} — {self.created_at.date()}"


class CropRecommendationLog(models.Model):
    """
    Logs every crop recommendation made by the engine.
    Used to:
      1. Track which crops were recommended in which region/season
      2. Build a feedback loop — if farmer later says crop failed, score goes down
      3. Tune agro-zone priority_crops based on real adoption
      4. Export training data for next model version
    """
    session_id    = models.CharField(max_length=100, db_index=True)
    phone_number  = models.CharField(max_length=20, blank=True)
    location_name = models.CharField(max_length=200, blank=True)
    state         = models.CharField(max_length=100, blank=True, db_index=True)
    district      = models.CharField(max_length=100, blank=True)
    latitude      = models.FloatField(null=True, blank=True)
    longitude     = models.FloatField(null=True, blank=True)
    agro_zone     = models.CharField(max_length=50, blank=True)
    season        = models.CharField(max_length=20, blank=True, db_index=True)

    # What was recommended
    recommendations = models.JSONField(
        help_text="List of {crop_key, crop_name, score, rank} dicts"
    )
    top_crop       = models.CharField(max_length=100, blank=True, db_index=True)
    profile_source = models.CharField(max_length=50, blank=True,
                                       help_text="district_exact | state_first_district | keyword | gps_zone")

    # Context at recommendation time
    soil_type     = models.CharField(max_length=50, blank=True)
    rainfall_band = models.CharField(max_length=20, blank=True)
    irrigation    = models.CharField(max_length=20, blank=True)
    weather_risk  = models.CharField(max_length=50, blank=True)
    current_temp  = models.FloatField(null=True, blank=True)
    market_is_live = models.BooleanField(default=False)

    # Outcome feedback (filled later when farmer reports results)
    farmer_adopted   = models.BooleanField(null=True, blank=True,
                                            help_text="Did farmer actually grow the recommended crop?")
    adopted_crop     = models.CharField(max_length=100, blank=True,
                                         help_text="Which crop they actually grew")
    outcome_rating   = models.IntegerField(null=True, blank=True,
                                            help_text="1-5: how well the recommendation worked out")
    outcome_notes    = models.TextField(blank=True)
    feedback_at      = models.DateTimeField(null=True, blank=True)

    language      = models.CharField(max_length=10, default="hi")
    created_at    = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "crop_recommendation_logs"
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["session_id", "created_at"]),
            models.Index(fields=["state", "season", "created_at"]),
            models.Index(fields=["top_crop", "state"]),
            models.Index(fields=["agro_zone", "season"]),
            models.Index(fields=["farmer_adopted", "top_crop"]),
        ]

    def __str__(self):
        return f"Rec {self.top_crop} for {self.location_name} ({self.season}) — {self.created_at.date()}"
