"""Detach phone numbers that accounts attached to their profiles without OTP proof.

Before phone ownership required OTP verification, password registration stored
whatever mobile number the form contained, and a password account named after
a number (``919876543210``) was treated as owning it. Such a profile could be
read by the real owner of that number and by the account that made the claim.
Run once after deploying the ownership fix; the change is idempotent. Without
``--apply`` it only reports what it would change.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from advisory.api.viewsets.farmer_profile import FarmerProfileViewSet
from advisory.models import FarmerProfile


class Command(BaseCommand):
    help = "Remove phone numbers from account profiles whose account never verified that number."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")

    def handle(self, *args, **options):
        User = get_user_model()
        claimed = FarmerProfile.objects.filter(session_id__startswith="user:").exclude(phone_number="")
        to_detach = []
        for profile in claimed.iterator():
            user_id = profile.session_id.split(":", 1)[1]
            user = User.objects.filter(pk=user_id).first() if user_id.isdigit() else None
            owned = FarmerProfileViewSet._phone_candidates(user) if user else set()
            if profile.phone_number not in owned:
                to_detach.append(profile.pk)

        self.stdout.write(f"{len(to_detach)} of {claimed.count()} account profiles hold an unverified phone number.")
        if not options["apply"]:
            self.stdout.write("Dry run: nothing changed. Re-run with --apply to detach them.")
            return
        with transaction.atomic():
            updated = FarmerProfile.objects.filter(pk__in=to_detach).update(phone_number="")
        self.stdout.write(self.style.SUCCESS(f"Detached the phone number from {updated} profile(s)."))
