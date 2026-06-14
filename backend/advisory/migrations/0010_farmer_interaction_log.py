"""Migration 0010 — FarmerInteractionLog for ML training data collection."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("advisory", "0009_chathistory_session_id_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="FarmerInteractionLog",
            fields=[
                ("id",               models.BigAutoField(auto_created=True, primary_key=True)),
                ("session_id",       models.CharField(max_length=100, db_index=True)),
                ("phone_number",     models.CharField(max_length=20, blank=True, db_index=True)),
                ("location_name",    models.CharField(max_length=200, blank=True)),
                ("state",            models.CharField(max_length=100, blank=True)),
                ("latitude",         models.FloatField(null=True, blank=True)),
                ("longitude",        models.FloatField(null=True, blank=True)),
                ("query",            models.TextField()),
                ("response",         models.TextField()),
                ("intent",           models.CharField(max_length=50, blank=True)),
                ("language",         models.CharField(max_length=10, default="hi")),
                ("crops_detected",   models.JSONField(default=list)),
                ("ai_tier",          models.CharField(max_length=30, blank=True)),
                ("data_source",      models.CharField(max_length=100, blank=True)),
                ("sensor_data",      models.JSONField(null=True, blank=True)),
                ("weather_data",     models.JSONField(null=True, blank=True)),
                ("market_prices",    models.JSONField(null=True, blank=True)),
                ("season",           models.CharField(max_length=30, blank=True)),
                ("feedback_score",   models.IntegerField(null=True, blank=True)),
                ("feedback_text",    models.TextField(blank=True)),
                ("is_helpful",       models.BooleanField(null=True, blank=True)),
                ("response_time_ms", models.IntegerField(null=True, blank=True)),
                ("created_at",       models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"db_table": "farmer_interaction_logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="farmerinteractionlog",
            index=models.Index(fields=["session_id", "created_at"], name="fil_session_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerinteractionlog",
            index=models.Index(fields=["intent", "created_at"], name="fil_intent_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerinteractionlog",
            index=models.Index(fields=["state", "intent"], name="fil_state_intent_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerinteractionlog",
            index=models.Index(fields=["ai_tier", "created_at"], name="fil_tier_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerinteractionlog",
            index=models.Index(fields=["language", "created_at"], name="fil_lang_idx"),
        ),
    ]
