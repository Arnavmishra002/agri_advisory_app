"""Seed the Crop table with the current Cabinet-approved MSP references.

Run this command after deploying an annual MSP table update. Preview mode is
strictly read-only:

    python manage.py seed_msp --dry-run
    python manage.py seed_msp
"""

from django.core.management.base import BaseCommand

from advisory.services.msp_data import MSP_CURRENT, MSP_MARKETING_SEASON


_MSP_META = {
    "wheat": ("गेहूँ", "rabi"),
    "rice": ("धान", "kharif"),
    "paddy": ("धान", "kharif"),
    "maize": ("मक्का", "kharif"),
    "soybean": ("सोयाबीन", "kharif"),
    "cotton": ("कपास", "kharif"),
    "mustard": ("सरसों", "rabi"),
    "gram": ("चना", "rabi"),
    "masoor": ("मसूर", "rabi"),
    "lentil": ("मसूर", "rabi"),
    "groundnut": ("मूँगफली", "kharif"),
    "sunflower": ("सूरजमुखी", "kharif"),
    "jowar": ("ज्वार", "kharif"),
    "bajra": ("बाजरा", "kharif"),
    "ragi": ("रागी", "kharif"),
    "barley": ("जौ", "rabi"),
    "tur": ("अरहर", "kharif"),
    "arhar": ("अरहर", "kharif"),
    "moong": ("मूँग", "kharif"),
    "urad": ("उड़द", "kharif"),
    "sesame": ("तिल", "kharif"),
    "niger": ("रामतिल", "kharif"),
    "safflower": ("कुसुम", "rabi"),
    "jute": ("जूट", "kharif"),
    "copra": ("खोपरा", "year_round"),
}

MSP_DATA = {
    crop_name: (MSP_CURRENT[crop_name], hindi, season)
    for crop_name, (hindi, season) in _MSP_META.items()
    if crop_name in MSP_CURRENT
}


class Command(BaseCommand):
    help = f"Seed Crop records with official MSP {MSP_MARKETING_SEASON} values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            default=MSP_MARKETING_SEASON,
            help=f"MSP season label (default: {MSP_MARKETING_SEASON})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database",
        )

    def handle(self, *args, **options):
        from advisory.models import Crop

        season = options["season"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be written"))

        created_count = 0
        updated_count = 0
        cleared_count = 0

        for crop_name, (msp, hindi, crop_season) in MSP_DATA.items():
            crop = Crop.objects.filter(name=crop_name).first()
            if crop is None:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  CREATE  {crop_name:15s}  MSP Rs {msp:,}  [{season}]"
                    )
                )
                if not dry_run:
                    Crop.objects.create(
                        name=crop_name,
                        description=f"ICAR crop: {crop_name.title()}",
                        ideal_soil_type="Loamy",
                        min_temperature_c=10.0,
                        max_temperature_c=40.0,
                        min_rainfall_mm_per_month=30.0,
                        max_rainfall_mm_per_month=200.0,
                        duration_days=120,
                        msp_per_quintal=msp,
                        season=crop_season,
                        name_hindi=hindi,
                        msp_season=season,
                    )
                continue

            changed = (
                crop.msp_per_quintal != msp
                or crop.msp_season != season
                or crop.name_hindi != hindi
                or crop.season != crop_season
            )
            if not changed:
                self.stdout.write(f"  OK      {crop_name:15s}  Rs {msp:,}  (no change)")
                continue

            updated_count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  UPDATE  {crop_name:15s}  Rs {crop.msp_per_quintal:,} -> "
                    f"Rs {msp:,}  [{season}]"
                )
            )
            if not dry_run:
                crop.msp_per_quintal = msp
                crop.name_hindi = hindi
                crop.season = crop_season
                crop.msp_season = season
                crop.save(
                    update_fields=[
                        "msp_per_quintal",
                        "name_hindi",
                        "season",
                        "msp_season",
                    ]
                )

        obsolete = Crop.objects.filter(msp_per_quintal__gt=0).exclude(name__in=MSP_DATA)
        cleared_count = obsolete.count()
        for crop in obsolete.only("name", "msp_per_quintal"):
            self.stdout.write(
                self.style.WARNING(
                    f"  CLEAR   {crop.name:15s}  obsolete MSP Rs {crop.msp_per_quintal:,}"
                )
            )
        if cleared_count and not dry_run:
            obsolete.update(msp_per_quintal=0, msp_season="")

        prefix = "Dry run complete" if dry_run else "Done"
        message = (
            f"{prefix}: create {created_count}, update {updated_count}, "
            f"clear {cleared_count} crop records."
        )
        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(message))
