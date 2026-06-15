"""
Management command: seed_msp
=============================
Seeds / updates the Crop model with MSP 2024-25 values announced by CACP.

Usage (run once after each annual MSP announcement):
    python manage.py seed_msp
    python manage.py seed_msp --season 2025-26  # override season label
    python manage.py seed_msp --dry-run          # preview without writing

This replaces the hardcoded MSP_2024_25 dict in unified_realtime_service.py.
After running this command, use get_msp(crop_id) in services to read from DB.
"""

from django.core.management.base import BaseCommand


# ── MSP 2024-25 (Cabinet approved — update here annually) ────────────────────
MSP_DATA = {
    # crop_name (lowercase, matches Crop.name in DB): (msp_per_quintal, name_hindi, season)
    "wheat":      (2275, "गेहूँ",     "rabi"),
    "rice":       (2300, "धान",       "kharif"),
    "maize":      (2090, "मक्का",     "kharif"),
    "soybean":    (4892, "सोयाबीन",   "kharif"),
    "cotton":     (7121, "कपास",      "kharif"),    # medium staple
    "mustard":    (5650, "सरसों",     "rabi"),
    "gram":       (5440, "चना",       "rabi"),
    "lentil":     (6425, "मसूर",      "rabi"),
    "groundnut":  (6783, "मूँगफली",   "kharif"),
    "sunflower":  (7280, "सूरजमुखी",  "rabi"),
    "jowar":      (3371, "ज्वार",      "kharif"),
    "bajra":      (2625, "बाजरा",     "kharif"),
    "ragi":       (3846, "रागी",      "kharif"),
    "barley":     (1735, "जौ",         "rabi"),
    "arhar":      (7000, "अरहर",      "kharif"),
    "moong":      (8682, "मूँग",       "kharif"),
    "urad":       (7400, "उड़द",       "kharif"),
}


class Command(BaseCommand):
    help = "Seed Crop model with MSP 2024-25 values. Run annually after CACP announcement."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            default="2024-25",
            help="MSP season label (default: 2024-25)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database",
        )

    def handle(self, *args, **options):
        from advisory.models import Crop

        season  = options["season"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written"))

        created_count = 0
        updated_count = 0

        for crop_name, (msp, hindi, crop_season) in MSP_DATA.items():
            crop, created = Crop.objects.get_or_create(
                name=crop_name,
                defaults={
                    "description":              f"ICAR crop: {crop_name.title()}",
                    "ideal_soil_type":          "Loamy",
                    "min_temperature_c":        10.0,
                    "max_temperature_c":        40.0,
                    "min_rainfall_mm_per_month": 30.0,
                    "max_rainfall_mm_per_month": 200.0,
                    "duration_days":            120,
                    "msp_per_quintal":          msp,
                    "season":                   crop_season,
                    "name_hindi":               hindi,
                    "msp_season":               season,
                },
            )

            if created:
                created_count += 1
                msg = f"  CREATE  {crop_name:15s}  MSP ₹{msp:,}  [{season}]"
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                old_msp = crop.msp_per_quintal
                if old_msp != msp or crop.msp_season != season or crop.name_hindi != hindi or crop.season != crop_season:
                    updated_count += 1
                    msg = f"  UPDATE  {crop_name:15s}  ₹{old_msp:,} → ₹{msp:,}  [{season}]"
                    self.stdout.write(self.style.WARNING(msg))
                    if not dry_run:
                        crop.msp_per_quintal = msp
                        crop.name_hindi      = hindi
                        crop.season          = crop_season
                        crop.msp_season      = season
                        crop.save(update_fields=["msp_per_quintal", "name_hindi", "season", "msp_season"])
                else:
                    self.stdout.write(f"  OK      {crop_name:15s}  ₹{msp:,}  (no change)")

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run complete: would create {created_count}, update {updated_count} crops."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done: created {created_count}, updated {updated_count} crops in Crop table."
            ))
