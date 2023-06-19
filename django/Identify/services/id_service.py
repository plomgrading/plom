# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.db import transaction

from Papers.models import IDPage


class IDService:
    """Functions for Identify HTML page."""

    @transaction.atomic
    def get_all_id_papers(self):
        return IDPage.objects.all().order_by("pk")

    @transaction.atomic
    def get_identified_papers(self):
        return IDPage.objects.exclude(image=None).order_by("pk")

    @transaction.atomic
    def get_all_unidentified_papers(self):
        return IDPage.objects.exclude(image__isnull=False)
