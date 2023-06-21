# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.db import transaction

from Papers.models import IDPage, Image


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

    @transaction.atomic
    def get_id_image_object(self, img_pk):
        try:
            img_obj = Image.objects.get(pk=img_pk)
            return img_obj
        except Image.DoesNotExist:
            return None
