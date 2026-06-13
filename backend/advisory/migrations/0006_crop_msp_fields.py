"""Migration 0006 — Add MSP and extended crop metadata to the Crop model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("advisory", "0005_iot_sensor_field_models"),
    ]

    operations = [
        # MSP 2024-25 (₹/quintal, 0 = no MSP for this crop)
        migrations.AddField(
            model_name="crop",
            name="msp_per_quintal",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Minimum Support Price ₹/quintal (0 = no government MSP). "
                          "Update annually after CACP Cabinet approval.",
            ),
        ),
        # Season for quick filtering without hitting comprehensive_crop_database.py
        migrations.AddField(
            model_name="crop",
            name="season",
            field=models.CharField(
                max_length=20,
                blank=True,
                default="",
                help_text="rabi | kharif | zaid | year_round",
            ),
        ),
        # Hindi name for multilingual UI
        migrations.AddField(
            model_name="crop",
            name="name_hindi",
            field=models.CharField(
                max_length=100,
                blank=True,
                default="",
                help_text="Crop name in Hindi script",
            ),
        ),
        # MSP year label so we know which announcement is in the DB
        migrations.AddField(
            model_name="crop",
            name="msp_season",
            field=models.CharField(
                max_length=10,
                blank=True,
                default="",
                help_text="Season the MSP applies to e.g. '2024-25'",
            ),
        ),
    ]
