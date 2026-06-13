"""Migration 0007 — FarmerProfile model for personalized AI advisory."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("advisory", "0006_crop_msp_fields")]

    operations = [
        migrations.CreateModel(
            name="FarmerProfile",
            fields=[
                ("id",                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("phone_number",      models.CharField(blank=True, db_index=True, max_length=20,
                                      help_text="WhatsApp/SMS number in E.164 format e.g. +919876543210")),
                ("session_id",        models.CharField(blank=True, db_index=True, max_length=100)),
                ("location_name",     models.CharField(blank=True, max_length=200)),
                ("state",             models.CharField(blank=True, max_length=100)),
                ("district",          models.CharField(blank=True, max_length=100)),
                ("latitude",          models.FloatField(blank=True, null=True)),
                ("longitude",         models.FloatField(blank=True, null=True)),
                ("farm_size_bigha",   models.FloatField(blank=True, null=True)),
                ("farm_size_hectare", models.FloatField(blank=True, null=True)),
                ("irrigation_type",   models.CharField(blank=True, max_length=30)),
                ("soil_type",         models.CharField(blank=True, max_length=50)),
                ("soil_ph",           models.FloatField(blank=True, null=True)),
                ("crop_history",      models.JSONField(default=list)),
                ("current_crop",      models.CharField(blank=True, max_length=100)),
                ("current_season",    models.CharField(blank=True, max_length=20)),
                ("has_pm_kisan",      models.BooleanField(default=False)),
                ("has_kcc",           models.BooleanField(default=False)),
                ("has_pmfby",         models.BooleanField(default=False)),
                ("pm_kisan_status",   models.CharField(blank=True, max_length=20)),
                ("preferred_language",models.CharField(default="hi", max_length=10)),
                ("whatsapp_opt_in",   models.BooleanField(default=True)),
                ("created_at",        models.DateTimeField(auto_now_add=True)),
                ("updated_at",        models.DateTimeField(auto_now=True)),
                ("last_seen_at",      models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "farmer_profiles"},
        ),
        migrations.AddIndex(
            model_name="farmerprofile",
            index=models.Index(fields=["phone_number"], name="farmer_phone_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerprofile",
            index=models.Index(fields=["session_id"], name="farmer_session_idx"),
        ),
        migrations.AddIndex(
            model_name="farmerprofile",
            index=models.Index(fields=["state", "district"], name="farmer_location_idx"),
        ),
    ]
